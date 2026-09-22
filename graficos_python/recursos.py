import os
import re
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------
# CONFIGURAÇÃO
# ----------------------------------------------------------------------

REPORTS_DIR = "../caliper-relatorios"
OUTPUT_DIR  = "graficos_recursos"

# Nós que queremos plotar (devem bater com fragmentos dos nomes das colunas)
NODE_FILTERS = [
    "peer0.org1.example.com",
    "peer0.org2.example.com",
    "orderer.example.com",
    "orderer2.example.com",
    "orderer3.example.com",
    "orderer4.example.com",
]

# Rótulos curtos para a legenda
NODE_LABELS = {
    "peer0.org1.example.com": "peer0.org1",
    "peer0.org2.example.com": "peer0.org2",
    "orderer.example.com":    "orderer",
    "orderer2.example.com":   "orderer2",
    "orderer3.example.com":   "orderer3",
    "orderer4.example.com":   "orderer4",
}

NODE_COLORS = {
    "peer0.org1.example.com": "#2E86AB",
    "peer0.org2.example.com": "#1B4F72",
    "orderer.example.com":    "#C73E1D",
    "orderer2.example.com":   "#E07B54",
    "orderer3.example.com":   "#27AE60",
    "orderer4.example.com":   "#1A7340",
}

# ----------------------------------------------------------------------
# PARSING DOS ARQUIVOS CSV
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

    match = re.search(r"round[_\-]?(\d+)", path_lower)
    if not match:
        raise ValueError(f"Não foi possível identificar o round em: {path}")

    return algorithm, int(match.group(1))


def parse_percent(value: str) -> float:
    """Converte '12.3%' ou '12.3' para float. Retorna NaN se inválido."""
    if pd.isna(value) or str(value).strip() == "":
        return np.nan
    try:
        return float(str(value).replace("%", "").strip())
    except ValueError:
        return np.nan


def parse_memory_mb(value: str) -> float:
    """Converte valores de memória do Prometheus para MB (megabytes decimais)."""
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


def find_node_column(columns: list[str], node_key: str) -> str | None:
    """
    Retorna o nome exato da coluna que corresponde ao node_key.
    Prioriza correspondência exata; ignora colunas de chaincode (dev-peer*).
    """
    for col in columns:
        if col.lower().startswith("dev-"):
            continue
        if node_key.lower() in col.lower():
            return col
    return None


def load_csv(path: str, metric: str) -> pd.DataFrame | None:
    """
    Lê um CPU.csv ou Memory.csv e retorna um DataFrame com colunas:
        time_min  (tempo relativo em minutos a partir de t=0)
        <node_key> para cada node em NODE_FILTERS
    """
    try:
        df = pd.read_csv(path, quotechar='"')
    except Exception as e:
        print(f"[!] Erro ao ler {path}: {e}")
        return None

    df.columns = [c.strip().strip('"') for c in df.columns]

    # Tempo relativo
    df["Time"] = pd.to_datetime(df["Time"])
    df["time_min"] = (df["Time"] - df["Time"].iloc[0]).dt.total_seconds() / 60

    result = pd.DataFrame({"time_min": df["time_min"]})

    for node_key in NODE_FILTERS:
        col = find_node_column(list(df.columns), node_key)
        if col is None:
            result[node_key] = np.nan
            continue
        if metric == "cpu":
            result[node_key] = df[col].apply(parse_percent)
        else:
            result[node_key] = df[col].apply(parse_memory_mb)

    return result


def load_all_rounds(reports_dir: str, algorithm: str, metric: str) -> list[pd.DataFrame]:
    """
    Carrega todos os rounds de um algoritmo para a métrica escolhida.
    Retorna lista de DataFrames (um por round), cada um com time_min + 6 colunas de node.
    """
    filename = "CPU.csv" if metric == "cpu" else "Memory.csv"
    pattern  = os.path.join(reports_dir, algorithm.lower(), "round_*", filename)
    paths    = sorted(glob.glob(pattern))

    if not paths:
        raise FileNotFoundError(
            f"Nenhum {filename} encontrado em '{pattern}'. "
            "Verifique REPORTS_DIR e a estrutura de pastas."
        )

    dfs = []
    for path in paths:
        df = load_csv(path, metric)
        if df is not None:
            dfs.append(df)

    print(f"[+] {algorithm}: {len(dfs)} rounds carregados para {metric.upper()}.")
    return dfs


# ----------------------------------------------------------------------
# ALINHAMENTO E MÉDIA DOS ROUNDS
# ----------------------------------------------------------------------

def average_rounds(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Alinha os rounds por tempo relativo (usando o menor número de linhas
    como referência) e calcula a média ponto a ponto de cada node.
    """
    min_len = min(len(df) for df in dfs)
    clipped = [df.iloc[:min_len].reset_index(drop=True) for df in dfs]

    time_min = clipped[0]["time_min"].values
    avg = pd.DataFrame({"time_min": time_min})

    for node_key in NODE_FILTERS:
        cols = [df[node_key].values for df in clipped if node_key in df.columns]
        if cols:
            stacked = np.array(cols, dtype=float)
            avg[node_key] = np.nanmean(stacked, axis=0)
        else:
            avg[node_key] = np.nan

    return avg


# ----------------------------------------------------------------------
# PLOTAGEM
# ----------------------------------------------------------------------

def plot_resources(avg_df: pd.DataFrame, algorithm: str, metric: str, output_dir: str) -> str:
    """
    Plota um gráfico com 6 linhas (uma por node) para o algoritmo e métrica dados.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    for node_key in NODE_FILTERS:
        if node_key not in avg_df.columns:
            continue
        values = avg_df[node_key].values
        if np.all(np.isnan(values)):
            continue
        ax.plot(
            avg_df["time_min"],
            values,
            label=NODE_LABELS[node_key],
            color=NODE_COLORS[node_key],
            linewidth=1.8,
        )

    if metric == "cpu":
        ylabel = "CPU (%)"
        title  = f"Consumo de CPU por Nó — {algorithm}"
        suffix = "cpu"
    else:
        ylabel = "RAM (MB)"
        title  = f"Consumo de RAM por Nó — {algorithm}"
        suffix = "ram"

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("Tempo relativo (min)", fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.legend(title="Nó", fontsize=9, loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{suffix}_{algorithm.lower()}.png")
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


def aggregate_network(avg_df: pd.DataFrame, metric: str) -> np.ndarray:
    """
    Reduz os 6 nós a um único valor por ponto de tempo:
      - CPU: média entre os nós (evita distorção do peer0.org1)
      - RAM: soma dos nós (consumo total da rede)
    """
    node_data = np.array(
        [avg_df[n].values for n in NODE_FILTERS if n in avg_df.columns],
        dtype=float,
    )
    if metric == "cpu":
        return np.nanmean(node_data, axis=0)
    else:
        return np.nansum(node_data, axis=0)


def plot_comparativo(
    avg_raft: pd.DataFrame,
    avg_smartbft: pd.DataFrame,
    metric: str,
    output_dir: str,
) -> str:
    """
    Plota um gráfico com 2 linhas (Raft vs SmartBFT) representando o
    consumo agregado da rede ao longo do tempo.
    """
    # Alinha os dois DataFrames pelo menor comprimento
    min_len = min(len(avg_raft), len(avg_smartbft))
    time_min = avg_raft["time_min"].values[:min_len]

    raft_vals     = aggregate_network(avg_raft.iloc[:min_len],     metric)
    smartbft_vals = aggregate_network(avg_smartbft.iloc[:min_len], metric)

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(time_min, raft_vals,     label="Raft",     color="#2E86AB", linewidth=2)
    ax.plot(time_min, smartbft_vals, label="SmartBFT", color="#C73E1D", linewidth=2)

    if metric == "cpu":
        ylabel  = "CPU médio da rede (%)"
        title   = "Consumo de CPU — Raft vs SmartBFT (média dos nós)"
        suffix  = "cpu_comparativo"
    else:
        ylabel  = "RAM total da rede (MB)"
        title   = "Consumo de RAM — Raft vs SmartBFT (soma dos nós)"
        suffix  = "ram_comparativo"

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("Tempo relativo (min)", fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.legend(title="Algoritmo", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{suffix}.png")
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    avg_cache = {}  # guarda avg_df por (algorithm, metric) para reusar no comparativo

    # Gráficos por nó (4 imagens)
    for metric in ("cpu", "ram"):
        for algorithm in ("Raft", "SmartBFT"):
            try:
                dfs = load_all_rounds(REPORTS_DIR, algorithm, metric)
            except FileNotFoundError as e:
                print(f"[!] {e}")
                continue

            avg_df = average_rounds(dfs)
            avg_cache[(algorithm, metric)] = avg_df

            out_path = plot_resources(avg_df, algorithm, metric, OUTPUT_DIR)
            print(f"[+] Gráfico salvo em: {out_path}")

    # Gráficos comparativos (2 imagens)
    for metric in ("cpu", "ram"):
        raft_df     = avg_cache.get(("Raft",     metric))
        smartbft_df = avg_cache.get(("SmartBFT", metric))
        if raft_df is None or smartbft_df is None:
            print(f"[!] Dados insuficientes para o comparativo de {metric.upper()}, pulando.")
            continue
        out_path = plot_comparativo(raft_df, smartbft_df, metric, OUTPUT_DIR)
        print(f"[+] Gráfico salvo em: {out_path}")


if __name__ == "__main__":
    main()

