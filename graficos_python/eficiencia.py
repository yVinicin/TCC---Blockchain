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

REPORTS_DIR = "../caliper-relatorios"
OUTPUT_DIR  = "eficiencia"
CONFIDENCE  = 0.95

WORKLOAD_NAME_MAP = {
    "createasset":  "CreateAsset",
    "readasset":    "ReadAsset",
    "transferasset":"TransferAsset",
}
ROW_NAME_RE = re.compile(r"^([a-zA-Z]+)\s*\(.*?\)\s*-\s*(\d+)\s*tps", re.IGNORECASE)

NODE_FILTERS = [
    "peer0.org1.example.com",
    "peer0.org2.example.com",
    "orderer.example.com",
    "orderer2.example.com",
    "orderer3.example.com",
    "orderer4.example.com",
]

WORKLOADS = ["CreateAsset", "ReadAsset", "TransferAsset"]
WORKLOAD_LABELS = {
    "CreateAsset":  "CreateAsset (Escrita)",
    "ReadAsset":    "ReadAsset (Leitura)",
    "TransferAsset":"TransferAsset (Leitura + Escrita)",
}

ALGO_COLORS  = {"Raft": "#2E86AB", "SmartBFT": "#C73E1D"}
ALGO_MARKERS = {"Raft": "o",       "SmartBFT": "s"}

# ----------------------------------------------------------------------
# PARSERS
# ----------------------------------------------------------------------

def parse_algorithm_and_round(path: str):
    path_lower = path.lower()
    if "smartbft" in path_lower:
        algorithm = "SmartBFT"
    elif "raft" in path_lower:
        algorithm = "Raft"
    else:
        raise ValueError(f"Algoritmo não identificado em: {path}")
    match = re.search(r"round[_\-]?(\d+)", path_lower)
    if not match:
        raise ValueError(f"Round não identificado em: {path}")
    return algorithm, int(match.group(1))


def parse_percent(value) -> float:
    if pd.isna(value) or str(value).strip() == "":
        return np.nan
    try:
        return float(str(value).replace("%", "").strip())
    except ValueError:
        return np.nan


def find_node_column(columns: list[str], node_key: str) -> str | None:
    for col in columns:
        if col.lower().startswith("dev-"):
            continue
        if node_key.lower() in col.lower():
            return col
    return None


# ----------------------------------------------------------------------
# EXTRAÇÃO — THROUGHPUT (report.html)
# ----------------------------------------------------------------------

def parse_report_html(html_path: str) -> list[dict]:
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    table = soup.find("table")
    if table is None:
        return []

    rows    = table.find_all("tr")
    headers = [c.get_text(strip=True).lower() for c in rows[0].find_all(["th", "td"])]

    def col(cells, fragment):
        for i, h in enumerate(headers):
            if fragment in h:
                return cells[i]
        raise ValueError(f"Coluna '{fragment}' não encontrada em {html_path}")

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
        raw_wl, tps_str = m.groups()
        workload = WORKLOAD_NAME_MAP.get(raw_wl.lower())
        if not workload:
            continue
        results.append({
            "algorithm":  algorithm,
            "workload":   workload,
            "tps":        int(tps_str),
            "round":      round_num,
            "throughput": float(col(cells, "throughput")),
        })
    return results


def load_throughput(reports_dir: str) -> pd.DataFrame:
    # round_N/<Operacao>/report.html
    paths = glob.glob(
        os.path.join(reports_dir, "**", "round_*", "*", "report.html"), recursive=True
    )
    rows = []
    for p in sorted(paths):
        try:
            rows.extend(parse_report_html(p))
        except Exception as e:
            print(f"[!] {p}: {e}")
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# EXTRAÇÃO — CPU MÉDIA DO ROUND (CPU.csv)
# ----------------------------------------------------------------------

def cpu_mean_for_round(csv_path: str) -> float:
    """
    Lê o CPU.csv de um round e retorna a CPU média da rede no round inteiro
    (média temporal de todos os 6 nós).
    """
    try:
        df = pd.read_csv(csv_path, quotechar='"')
    except Exception as e:
        print(f"[!] Erro ao ler {csv_path}: {e}")
        return np.nan

    df.columns = [c.strip().strip('"') for c in df.columns]

    node_means = []
    for node_key in NODE_FILTERS:
        col = find_node_column(list(df.columns), node_key)
        if col is None:
            continue
        values = df[col].apply(parse_percent).to_numpy()
        node_mean = np.nanmean(values)
        if not np.isnan(node_mean):
            node_means.append(node_mean)

    return np.mean(node_means) if node_means else np.nan


def load_cpu_per_round(reports_dir: str) -> pd.DataFrame:
    """
    Retorna DataFrame com colunas: algorithm, workload, round, cpu_mean
    (uma linha por round de cada algoritmo x operação). A CPU média agora
    é calculada separadamente para cada operação, já que cada uma roda
    isolada e tem seu próprio CPU.csv.
    """
    rows = []
    for algorithm in ("Raft", "SmartBFT"):
        for workload in WORKLOADS:
            pattern = os.path.join(
                reports_dir, algorithm.lower(), "round_*", workload, "CPU.csv"
            )
            paths = sorted(glob.glob(pattern))
            if not paths:
                print(f"[!] Nenhum CPU.csv encontrado para {algorithm}/{workload}.")
                continue
            for path in paths:
                _, round_num = parse_algorithm_and_round(path)
                cpu_mean     = cpu_mean_for_round(path)
                rows.append({
                    "algorithm": algorithm,
                    "workload":  workload,
                    "round":     round_num,
                    "cpu_mean":  cpu_mean,
                })
            print(f"[+] {algorithm}/{workload}: {len(paths)} rounds de CPU carregados.")
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# CÁLCULO DE EFICIÊNCIA
# ----------------------------------------------------------------------

def compute_efficiency(throughput_df: pd.DataFrame, cpu_df: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza throughput com CPU média do round e calcula eficiência
    (tx/s por %) para cada combinação algorithm × workload × tps × round.
    """
    merged = throughput_df.merge(cpu_df, on=["algorithm", "workload", "round"], how="left")
    merged["efficiency"] = merged["throughput"] / merged["cpu_mean"]
    return merged


# ----------------------------------------------------------------------
# ESTATÍSTICA
# ----------------------------------------------------------------------

def mean_and_ci(values: np.ndarray) -> tuple[float, float]:
    n = len(values)
    mean = np.mean(values)
    if n < 2:
        return mean, 0.0
    sem    = stats.sem(values)
    margin = sem * stats.t.ppf((1 + CONFIDENCE) / 2.0, n - 1)
    return mean, margin


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for (algorithm, workload, tps), group in df.groupby(["algorithm", "workload", "tps"]):
        values       = group["efficiency"].dropna().to_numpy()
        mean, margin = mean_and_ci(values)
        records.append({
            "algorithm": algorithm,
            "workload":  workload,
            "tps":       tps,
            "mean_eff":  mean,
            "ci95":      margin,
        })
    summary = pd.DataFrame(records)
    # Nível de carga (0 = menor TPS, 1 = intermediário, 2 = maior) dentro de
    # cada algoritmo/workload. Permite alinhar redes com TPS alvo diferentes.
    summary["level"] = (
        summary.groupby(["algorithm", "workload"])["tps"]
        .rank(method="dense").astype(int) - 1
    )
    return summary


# ----------------------------------------------------------------------
# PLOTAGEM
# ----------------------------------------------------------------------

def plot_workload(summary: pd.DataFrame, workload: str, output_dir: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 5.5))

    subset = summary[summary["workload"] == workload].sort_values("tps")

    for algorithm in ["Raft", "SmartBFT"]:
        data = subset[subset["algorithm"] == algorithm].sort_values("tps")
        if data.empty:
            continue
        ax.errorbar(
            data["level"],
            data["mean_eff"],
            yerr=data["ci95"],
            label=algorithm,
            color=ALGO_COLORS[algorithm],
            marker=ALGO_MARKERS[algorithm],
            markersize=7,
            linewidth=2,
            capsize=5,
            capthick=1.5,
            elinewidth=1.5,
        )

    ax.set_title(
        f"Eficiência — {WORKLOAD_LABELS.get(workload, workload)}",
        fontsize=13, fontweight="bold"
    )
    ax.set_xlabel("Nível de carga (TPS alvo)", fontsize=11)
    ax.set_ylabel("Eficiência (tx/s por %CPU)", fontsize=11)

    # Rótulo de cada nível: um único TPS se as redes coincidem,
    # ou o TPS de cada rede quando diferem.
    levels = sorted(subset["level"].unique())
    labels = []
    for lv in levels:
        tps_by_algo = {
            r.algorithm: int(r.tps)
            for r in subset[subset["level"] == lv].itertuples()
        }
        if len(set(tps_by_algo.values())) == 1:
            labels.append(f"{next(iter(tps_by_algo.values()))}")
        else:
            labels.append("\n".join(
                f"{a}: {tps_by_algo[a]}" for a in ("Raft", "SmartBFT") if a in tps_by_algo
            ))
    ax.set_xticks(levels)
    ax.set_xticklabels(labels, fontsize=10)
    ax.margins(x=0.1)
    ax.legend(title="Algoritmo", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"eficiencia_{workload}.png")
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def main():
    print("[*] Carregando throughput dos report.html...")
    throughput_df = load_throughput(REPORTS_DIR)
    if throughput_df.empty:
        print("[!] Nenhum dado de throughput encontrado. Verifique REPORTS_DIR.")
        return

    print("[*] Carregando CPU média dos CPU.csv...")
    cpu_df = load_cpu_per_round(REPORTS_DIR)
    if cpu_df.empty:
        print("[!] Nenhum dado de CPU encontrado. Verifique REPORTS_DIR.")
        return

    eff_df  = compute_efficiency(throughput_df, cpu_df)
    summary = summarize(eff_df)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for workload in WORKLOADS:
        if workload not in eff_df["workload"].unique():
            print(f"[!] Workload '{workload}' não encontrado, pulando.")
            continue
        out_path = plot_workload(summary, workload, OUTPUT_DIR)
        print(f"[+] Gráfico salvo em: {out_path}")


if __name__ == "__main__":
    main()

