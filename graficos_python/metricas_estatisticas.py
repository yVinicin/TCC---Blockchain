import os
import re
import glob
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

# ----------------------------------------------------------------------
# CONFIGURAÇÃO
# ----------------------------------------------------------------------

REPORTS_DIR = "../caliper-relatorios"
OUTPUT_FILE = "estatisticas.txt"

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
NODE_LABELS = {
    "peer0.org1.example.com": "peer0.org1",
    "peer0.org2.example.com": "peer0.org2",
    "orderer.example.com":    "orderer",
    "orderer2.example.com":   "orderer2",
    "orderer3.example.com":   "orderer3",
    "orderer4.example.com":   "orderer4",
}

# ----------------------------------------------------------------------
# PARSERS COMUNS
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


def parse_memory_mb(value) -> float:
    if pd.isna(value) or str(value).strip() in ("", "0 B", "0B"):
        return np.nan
    s = str(value).strip()
    try:
        if "GiB" in s:
            return float(s.replace("GiB", "").strip()) * 1024 ** 3 / 1e6
        if "MiB" in s:
            return float(s.replace("MiB", "").strip()) * 1024 ** 2 / 1e6
        if "KiB" in s:
            return float(s.replace("KiB", "").strip()) * 1024 / 1e6
        if "B" in s:
            return float(s.replace("B", "").strip()) / 1e6
    except ValueError:
        pass
    return np.nan


def find_node_column(columns, node_key):
    for col in columns:
        if col.lower().startswith("dev-"):
            continue
        if node_key.lower() in col.lower():
            return col
    return None


# ----------------------------------------------------------------------
# EXTRAÇÃO — THROUGHPUT E LATÊNCIA (report.html)
# ----------------------------------------------------------------------

def parse_report_html(html_path: str) -> list[dict]:
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    table = soup.find("table")
    if table is None:
        return []

    rows = table.find_all("tr")
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
            "algorithm": algorithm,
            "workload":  workload,
            "tps":       int(tps_str),
            "round":     round_num,
            "throughput":  float(col(cells, "throughput")),
            "avg_latency": float(col(cells, "avg latency")),
        })
    return results


def load_caliper_data(reports_dir: str) -> pd.DataFrame:
    paths = glob.glob(os.path.join(reports_dir, "**", "round_*", "report.html"), recursive=True)
    rows = []
    for p in sorted(paths):
        try:
            rows.extend(parse_report_html(p))
        except Exception as e:
            print(f"[!] {p}: {e}")
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# EXTRAÇÃO — CPU E RAM (CSV do Prometheus)
# ----------------------------------------------------------------------

def load_resource_csv(path: str, metric: str) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(path, quotechar='"')
    except Exception as e:
        print(f"[!] Erro ao ler {path}: {e}")
        return None

    df.columns = [c.strip().strip('"') for c in df.columns]
    result = {}
    for node_key in NODE_FILTERS:
        col = find_node_column(list(df.columns), node_key)
        if col is None:
            result[node_key] = np.nan
            continue
        if metric == "cpu":
            result[node_key] = df[col].apply(parse_percent).to_numpy()
        else:
            result[node_key] = df[col].apply(parse_memory_mb).to_numpy()
    return result  # dict: node_key -> array de valores ao longo do tempo


def load_resource_rounds(reports_dir: str, algorithm: str, metric: str):
    """
    Retorna dict: node_key -> lista de arrays (um array por round).
    """
    filename = "CPU.csv" if metric == "cpu" else "Memory.csv"
    pattern  = os.path.join(reports_dir, algorithm.lower(), "round_*", filename)
    paths    = sorted(glob.glob(pattern))

    if not paths:
        raise FileNotFoundError(f"Nenhum {filename} em '{pattern}'.")

    per_node = {n: [] for n in NODE_FILTERS}
    for path in paths:
        data = load_resource_csv(path, metric)
        if data is None:
            continue
        for node_key in NODE_FILTERS:
            vals = data.get(node_key, np.nan)
            if np.isscalar(vals):
                per_node[node_key].append(np.array([np.nan]))
            else:
                per_node[node_key].append(vals)

    print(f"[+] {algorithm}: {len(paths)} rounds carregados para {metric.upper()}.")
    return per_node


# ----------------------------------------------------------------------
# CÁLCULO ESTATÍSTICO
# ----------------------------------------------------------------------

def stats(values: np.ndarray) -> dict:
    """Retorna média, desvio padrão e variância ignorando NaN."""
    v = values[~np.isnan(values)]
    if len(v) == 0:
        return {"mean": np.nan, "std": np.nan, "var": np.nan}
    return {
        "mean": np.mean(v),
        "std":  np.std(v, ddof=1),   # ddof=1 → desvio padrão amostral
        "var":  np.var(v, ddof=1),
    }


def caliper_stats(df: pd.DataFrame, algorithm: str) -> dict:
    """
    Para throughput e latência: agrupa por (workload, tps) e calcula
    estatísticas a partir dos valores dos 10 rounds.
    """
    result = {}
    sub = df[df["algorithm"] == algorithm]
    for metric in ("throughput", "avg_latency"):
        result[metric] = {}
        for (workload, tps), group in sub.groupby(["workload", "tps"]):
            key = f"{workload} @ {tps} TPS"
            result[metric][key] = stats(group[metric].to_numpy())
    return result


def resource_stats(per_node: dict) -> dict:
    """
    Para cada nó, calcula:
      - mean_temporal / std_temporal / var_temporal:
            média de cada round (série temporal colapsada em 1 número)
            depois estatísticas entre os 10 rounds
      - mean_peak / std_peak / var_peak:
            máximo de cada round
            depois estatísticas entre os 10 rounds
    """
    result = {}
    for node_key, arrays in per_node.items():
        means_per_round = np.array([np.nanmean(a) for a in arrays])
        peaks_per_round = np.array([np.nanmax(a)  for a in arrays])
        result[node_key] = {
            "temporal": stats(means_per_round),
            "peak":     stats(peaks_per_round),
        }
    return result


# ----------------------------------------------------------------------
# FORMATAÇÃO DO RELATÓRIO TXT
# ----------------------------------------------------------------------

WORKLOADS_ORDER = [
    "CreateAsset @ 50 TPS",  "CreateAsset @ 160 TPS",  "CreateAsset @ 270 TPS",
    "ReadAsset @ 50 TPS",    "ReadAsset @ 160 TPS",    "ReadAsset @ 270 TPS",
    "TransferAsset @ 50 TPS","TransferAsset @ 160 TPS","TransferAsset @ 270 TPS",
]

def fmt(v, decimals=4):
    return f"{v:.{decimals}f}" if not np.isnan(v) else "N/A"

def write_report(lines: list[str], path: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[+] Relatório salvo em: {path}")


def section_caliper(algo_stats: dict, algorithm: str) -> list[str]:
    lines = []
    lines.append(f"Rede {algorithm}:")
    lines.append("")

    for metric_key, metric_label, unit in [
        ("throughput",  "Throughput",     "tx/s"),
        ("avg_latency", "Latência Média", "s"),
    ]:
        lines.append(f"  [ {metric_label} ({unit}) ]")
        data = algo_stats[metric_key]
        for scenario in WORKLOADS_ORDER:
            if scenario not in data:
                continue
            s = data[scenario]
            lines.append(f"  {scenario}:")
            lines.append(f"      Média:          {fmt(s['mean'])} {unit}")
            lines.append(f"      Desvio Padrão:  {fmt(s['std'])}")
            lines.append(f"      Variância:      {fmt(s['var'])}")
        lines.append("")

    return lines


def section_resource(node_stats: dict, algorithm: str, metric: str) -> list[str]:
    lines = []
    unit = "%" if metric == "cpu" else "MB"
    label = "CPU" if metric == "cpu" else "RAM"
    lines.append(f"  [ {label} ({unit}) ]")

    for node_key in NODE_FILTERS:
        if node_key not in node_stats:
            continue
        s    = node_stats[node_key]
        name = NODE_LABELS[node_key]

        lines.append(f"  {name}:")
        lines.append(f"    Consumo médio temporal:")
        lines.append(f"      Média:          {fmt(s['temporal']['mean'])} {unit}")
        lines.append(f"      Desvio Padrão:  {fmt(s['temporal']['std'])}")
        lines.append(f"      Variância:      {fmt(s['temporal']['var'])}")
        lines.append(f"    Pico máximo:")
        lines.append(f"      Média:          {fmt(s['peak']['mean'])} {unit}")
        lines.append(f"      Desvio Padrão:  {fmt(s['peak']['std'])}")
        lines.append(f"      Variância:      {fmt(s['peak']['var'])}")

    lines.append("")
    return lines


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def main():
    # --- Throughput e Latência ---
    print("[*] Carregando report.html...")
    caliper_df = load_caliper_data(REPORTS_DIR)

    # --- CPU e RAM ---
    resource_data = {}
    for algorithm in ("Raft", "SmartBFT"):
        resource_data[algorithm] = {}
        for metric in ("cpu", "ram"):
            try:
                resource_data[algorithm][metric] = load_resource_rounds(
                    REPORTS_DIR, algorithm, metric
                )
            except FileNotFoundError as e:
                print(f"[!] {e}")
                resource_data[algorithm][metric] = {}

    # --- Montar relatório ---
    output = []
    output.append("=" * 60)
    output.append("  ESTATÍSTICAS — Raft vs SmartBFT")
    output.append("  Métricas: Throughput, Latência, CPU, RAM")
    output.append("  Estatísticas: Média, Desvio Padrão, Variância")
    output.append("  (Desvio padrão amostral, ddof=1)")
    output.append("=" * 60)
    output.append("")

    for algorithm in ("Raft", "SmartBFT"):
        # Throughput e Latência
        if not caliper_df.empty:
            algo_stats = caliper_stats(caliper_df, algorithm)
            output.extend(section_caliper(algo_stats, algorithm))
        else:
            output.append(f"Rede {algorithm}:")
            output.append("  [!] Dados do Caliper não encontrados.")
            output.append("")

        # CPU e RAM
        for metric in ("cpu", "ram"):
            per_node = resource_data[algorithm].get(metric, {})
            if per_node:
                node_stats = resource_stats(per_node)
                output.extend(section_resource(node_stats, algorithm, metric))
            else:
                unit  = "%" if metric == "cpu" else "MB"
                label = "CPU" if metric == "cpu" else "RAM"
                output.append(f"  [ {label} ({unit}) ]")
                output.append(f"  [!] Dados não encontrados.")
                output.append("")

        output.append("-" * 60)
        output.append("")

    write_report(output, OUTPUT_FILE)


if __name__ == "__main__":
    main()

