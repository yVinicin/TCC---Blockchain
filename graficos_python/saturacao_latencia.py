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

# Aponte para a pasta raiz que contém os diretórios dos algoritmos e a subpasta "saturacao"
REPORTS_DIR = "../caliper-relatorios"  
OUTPUT_DIR = "graficos_latencia"
CONFIDENCE = 0.95

# Mapeia o nome do workload como aparece no report.html do Caliper
# para o nome padronizado usado nos gráficos.
WORKLOAD_NAME_MAP = {
    "createasset": "CreateAsset",
    "readasset": "ReadAsset",
    "transferasset": "TransferAsset",
}

# Regex adaptado para extrair "<workload> - <tps>tps" da coluna "Name"
# Ex: "transferAsset - 100tps" -> workload=transferAsset, tps=100
ROW_NAME_RE = re.compile(r"^([a-zA-Z]+)\s*-\s*(\d+)\s*tps", re.IGNORECASE)

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
    "TransferAsset": "TransferAsset (Saturação)",
}

# ----------------------------------------------------------------------
# Extração dos report.html do Caliper
# ----------------------------------------------------------------------

def parse_algorithm(path: str):
    """
    Extrai apenas o algoritmo a partir do caminho do arquivo.
    """
    path_lower = path.lower()

    if "smartbft" in path_lower:
        return "SmartBFT"
    elif "raft" in path_lower:
        return "Raft"
    else:
        return "Desconhecido"


def parse_report_html(html_path: str) -> list[dict]:
    """
    Lê um report.html do Caliper e devolve uma lista de linhas
    (uma por workload x tps), extraindo throughput e latência.
    Ignora a linha de warmup.
    """
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    # A primeira tabela da página é a tabela-resumo com todas as linhas.
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

    algorithm = parse_algorithm(html_path)
    results = []

    for tr in rows[1:]:
        cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
        if not cells:
            continue
        name = cells[0]

        # Ignora "Aquecimento-Ledger" ou qualquer variação com warmup
        if "warmup" in name.lower() or "aquecimento" in name.lower():
            continue

        m = ROW_NAME_RE.match(name)
        if not m:
            continue  

        raw_workload, tps_str = m.groups()
        workload = WORKLOAD_NAME_MAP.get(raw_workload.lower())
        if workload is None:
            continue

        # A extração permanece lendo todas as métricas do relatório
        throughput = float(col(cells, "throughput"))
        avg_latency = float(col(cells, "avg latency"))
        max_latency = float(col(cells, "max latency"))
        min_latency = float(col(cells, "min latency"))

        results.append({
            "algorithm": algorithm,
            "workload": workload,
            "tps": int(tps_str),
            "throughput": throughput,
            "avg_latency": avg_latency,
            "max_latency": max_latency,
            "min_latency": min_latency,
        })

    return results


def build_dataframe_from_caliper_reports(reports_dir: str) -> pd.DataFrame:
    """
    Varre reports_dir recursivamente em busca de report.html.
    """
    html_paths = glob.glob(os.path.join(reports_dir, "**", "report.html"), recursive=True)
    if not html_paths:
        html_paths = glob.glob(os.path.join(reports_dir, "**", "*.html"), recursive=True)

    if not html_paths:
        raise FileNotFoundError(
            f"Nenhum arquivo HTML encontrado em '{reports_dir}'. "
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
    """
    Calcula a média e o Intervalo de Confiança.
    """
    n = len(values)
    mean = np.mean(values)
    if n < 2:
        return mean, 0.0
    sem = stats.sem(values)
    margin = sem * stats.t.ppf((1 + confidence) / 2.0, n - 1)
    return mean, margin


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrupa por (algorithm, workload, tps) calculando a estatística sobre a LATÊNCIA MÉDIA.
    """
    records = []
    # Alterado de "throughput" para "avg_latency"
    grouped = df.groupby(["algorithm", "workload", "tps"])["avg_latency"] 
    
    for (algorithm, workload, tps), values in grouped:
        mean, margin = mean_and_ci(values.to_numpy())
        records.append({
            "algorithm": algorithm,
            "workload": workload,
            "tps": tps,
            "mean_latency": mean, # Alterado o nome da chave para refletir o dado
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
            algo_data["mean_latency"], # Puxando os dados de latência do resumo
            yerr=algo_data["ci95"],
            label=algorithm,
            color=ALGO_COLORS.get(algorithm, "black"),
            marker=ALGO_MARKERS.get(algorithm, "o"),
            markersize=7,
            linewidth=2,
            capsize=5,
            capthick=1.5,
            elinewidth=1.5,
        )

    # Textos adaptados para Latência
    ax.set_title(f"Latência vs TPS Alvo — {WORKLOAD_LABELS.get(workload, workload)}",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("TPS Alvo", fontsize=11)
    ax.set_ylabel("Latência Média (s)", fontsize=11) 
    ax.set_xticks(sorted(subset["tps"].unique()))
    ax.legend(title="Algoritmo", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    # Adicionado o nome do workload ao arquivo para evitar sobreposição caso existam múltiplos
    out_path = os.path.join(output_dir, f"saturacao_latencia.png") 
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


def main():
    df = build_dataframe_from_caliper_reports(REPORTS_DIR)

    # A verificação agora garante que a avg_latency foi extraída corretamente
    required_cols = {"algorithm", "workload", "tps", "avg_latency"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Colunas faltando nos dados extraídos: {missing}")

    summary = summarize(df)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for workload in WORKLOADS:
        if workload not in df["workload"].unique():
            print(f"[!] Workload '{workload}' não encontrado nos dados, pulando.")
            continue
        out_path = plot_workload(summary, workload, OUTPUT_DIR)
        print(f"[+] Gráfico de latência salvo em: {out_path}")


if __name__ == "__main__":
    main()

