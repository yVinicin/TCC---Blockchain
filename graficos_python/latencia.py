import os
import re
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from bs4 import BeautifulSoup

# ----------------------------------------------------------------------
# CONFIGURAÇÃO
# ----------------------------------------------------------------------

REPORTS_DIR = "../caliper-relatorios"  # pasta contendo caliper-relatorios/{raft,smartbft}/round_N/report.html
OUTPUT_DIR = "graficos_latencia"
CONFIDENCE = 0.95

# Mapeia o nome do workload como aparece no report.html do Caliper
# para o nome padronizado usado nos gráficos.
WORKLOAD_NAME_MAP = {
    "createasset": "CreateAsset",
    "readasset": "ReadAsset",
    "transferasset": "TransferAsset",
}

# Regex para extrair "<workload>(...) - <tps>tps" da coluna "Name"
# Ex: "createAsset(Escrita) - 160tps" -> workload=createAsset, tps=160
ROW_NAME_RE = re.compile(r"^([a-zA-Z]+)\s*\(.*?\)\s*-\s*(\d+)\s*tps", re.IGNORECASE)

ALGO_COLORS = {
    "Raft": "#2E86AB",
    "SmartBFT": "#C73E1D",
}
ALGO_MARKERS = {
    "Raft": "o",
    "SmartBFT": "s",
}

WORKLOADS = ["CreateAsset", "ReadAsset", "TransferAsset"]
WORKLOAD_LABELS = {
    "CreateAsset": "CreateAsset (Escrita)",
    "ReadAsset": "ReadAsset (Leitura)",
    "TransferAsset": "TransferAsset (Leitura + Escrita)",
}


# ----------------------------------------------------------------------
# Extração dos report.html do Caliper
# ----------------------------------------------------------------------

def parse_algorithm_and_round(path: str):
    """Extrai algoritmo e round a partir do caminho do arquivo."""
    path_lower = path.lower()

    if "smartbft" in path_lower:
        algorithm = "SmartBFT"
    elif "raft" in path_lower:
        algorithm = "Raft"
    else:
        raise ValueError(f"Não foi possível identificar o algoritmo em: {path}")

    match = re.search(r"round[_\-]?(\d+)|r[_\-]?(\d+)\b|[_\-](\d+)\b", path_lower)
    if not match:
        raise ValueError(f"Não foi possível identificar o round em: {path}")
    round_num = int(next(g for g in match.groups() if g is not None))

    return algorithm, round_num


def parse_report_html(html_path: str) -> list[dict]:
    """
    Lê um report.html do Caliper e devolve uma lista de linhas
    (uma por workload x tps), extraindo throughput e latência.
    Ignora a linha de warmup ("Aquecimento" / "warmup").
    """
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    summary_table = soup.find("table")
    if summary_table is None:
        raise ValueError(f"Nenhuma tabela encontrada em {html_path}")

    rows = summary_table.find_all("tr")
    header_cells = [c.get_text(strip=True).lower() for c in rows[0].find_all(["th", "td"])]

    def col(cells, name_fragment):
        for i, h in enumerate(header_cells):
            if name_fragment in h:
                return cells[i]
        raise ValueError(f"Coluna contendo '{name_fragment}' não encontrada em {html_path}")

    algorithm, round_num = parse_algorithm_and_round(html_path)

    results = []
    for tr in rows[1:]:
        cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
        if not cells:
            continue
        name = cells[0]

        if "warmup" in name.lower() or "aquecimento" in name.lower():
            continue

        m = ROW_NAME_RE.match(name)
        if not m:
            continue

        raw_workload, tps_str = m.groups()
        workload = WORKLOAD_NAME_MAP.get(raw_workload.lower())
        if workload is None:
            continue

        throughput = float(col(cells, "throughput"))
        avg_latency = float(col(cells, "avg latency"))
        max_latency = float(col(cells, "max latency"))
        min_latency = float(col(cells, "min latency"))

        results.append({
            "algorithm": algorithm,
            "workload": workload,
            "tps": int(tps_str),
            "round": round_num,
            "throughput": throughput,
            "avg_latency": avg_latency,
            "max_latency": max_latency,
            "min_latency": min_latency,
        })

    return results


def build_dataframe_from_caliper_reports(reports_dir: str) -> pd.DataFrame:
    """
    Varre reports_dir recursivamente em busca de report.html e
    extrai todas as linhas de todos os rounds (em memória, sem salvar CSV).
    """
    html_paths = glob.glob(os.path.join(reports_dir, "**", "report.html"), recursive=True)
    if not html_paths:
        html_paths = glob.glob(os.path.join(reports_dir, "**", "*.html"), recursive=True)

    if not html_paths:
        raise FileNotFoundError(
            f"Nenhum report.html encontrado em '{reports_dir}'. "
            "Ajuste REPORTS_DIR no topo do script."
        )

    all_rows = []
    for path in sorted(html_paths):
        try:
            all_rows.extend(parse_report_html(path))
        except Exception as e:
            print(f"[!] Erro ao processar {path}: {e}")

    df = pd.DataFrame(all_rows)
    print(f"[+] {len(html_paths)} relatórios processados, {len(df)} linhas extraídas.")
    return df


# ----------------------------------------------------------------------
# ESTATÍSTICA
# ----------------------------------------------------------------------

def mean_and_ci(values: np.ndarray, confidence: float = CONFIDENCE):
    """Retorna (média, margem_de_erro) usando distribuição t de Student."""
    n = len(values)
    mean = np.mean(values)
    if n < 2:
        return mean, 0.0
    sem = stats.sem(values)
    margin = sem * stats.t.ppf((1 + confidence) / 2.0, n - 1)
    return mean, margin


def summarize(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """
    Agrupa por (algorithm, workload, tps) e calcula média + IC95%
    da métrica de latência escolhida, a partir dos 10 rounds de cada combinação.
    """
    records = []
    grouped = df.groupby(["algorithm", "workload", "tps"])[metric]
    for (algorithm, workload, tps), values in grouped:
        mean, margin = mean_and_ci(values.to_numpy())
        records.append({
            "algorithm": algorithm,
            "workload": workload,
            "tps": tps,
            "mean_value": mean,
            "ci95": margin,
            "n_rounds": len(values),
        })
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# PLOTAGEM
# ----------------------------------------------------------------------

def plot_workload(summary: pd.DataFrame, workload: str, output_dir: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 5.5))

    subset = summary[summary["workload"] == workload].sort_values("tps")

    for algorithm in ["Raft", "SmartBFT"]:
        algo_data = subset[subset["algorithm"] == algorithm].sort_values("tps")
        if algo_data.empty:
            continue
        ax.errorbar(
            algo_data["tps"],
            algo_data["mean_value"],
            yerr=algo_data["ci95"],
            label=algorithm,
            color=ALGO_COLORS[algorithm],
            marker=ALGO_MARKERS[algorithm],
            markersize=7,
            linewidth=2,
            capsize=5,
            capthick=1.5,
            elinewidth=1.5,
        )

    ax.set_title(f"Latência Média vs TPS Alvo — {WORKLOAD_LABELS.get(workload, workload)}",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("TPS Alvo", fontsize=11)
    ax.set_ylabel("Latência Média (s)", fontsize=11)
    ax.set_xticks(sorted(subset["tps"].unique()))
    ax.legend(title="Algoritmo", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"latencia_{workload}.png")
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


def main():
    df = build_dataframe_from_caliper_reports(REPORTS_DIR)

    required_cols = {"algorithm", "workload", "tps", "round", "avg_latency"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Colunas faltando nos dados extraídos: {missing}")

    summary = summarize(df, metric="avg_latency")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for workload in WORKLOADS:
        if workload not in df["workload"].unique():
            print(f"[!] Workload '{workload}' não encontrado nos dados, pulando.")
            continue
        out_path = plot_workload(summary, workload, OUTPUT_DIR)
        print(f"[+] Gráfico salvo em: {out_path}")


if __name__ == "__main__":
    main()

