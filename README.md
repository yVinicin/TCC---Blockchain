# ⛓️ TCC — Análise comparativa de desempenho dos mecanismos de consenso Raft e SmartBFT no Hyperledger Fabric 3.0

> Trabalho de Conclusão de Curso: análise comparativa de desempenho entre os mecanismos de consenso **Raft** e **SmartBFT** no Hyperledger Fabric 3.0, sob diferentes cargas de trabalho e taxas de transação.

![Badge Blockchain](https://img.shields.io/badge/Blockchain-Hyperledger%20Fabric%203.x-2F3134?logo=hyperledger&logoColor=white)
![Badge Benchmark](https://img.shields.io/badge/Benchmark-Hyperledger%20Caliper-orange)
![Badge Monitoring](https://img.shields.io/badge/Monitoring-Prometheus%20%2B%20Grafana-E6522C?logo=grafana&logoColor=white)
![Badge Academic](https://img.shields.io/badge/Type-TCC%20%2F%20Undergraduate%20Thesis-blue)

## 📖 Sobre o Projeto

Este repositório reúne toda a infraestrutura, scripts e dados utilizados no meu **Trabalho de Conclusão de Curso (TCC)**, cujo objetivo é comparar experimentalmente o desempenho dos mecanismos de consenso **Raft** e **SmartBFT** no **Hyperledger Fabric 3.0**.

A comparação avalia como cada algoritmo de consenso se comporta sob diferentes cargas de trabalho e taxas de transação, com foco em métricas de latência, throughput e consumo de recursos (CPU/RAM), correlacionadas com dados de monitoramento em tempo real.

## 🧪 Metodologia

* **Chaincode único:** `basic`, escrito em Go, usado em ambas as topologias para garantir comparabilidade.
* **Topologia equalizada:** 4 orderers / 2 organizações, montada a partir do `fabric-samples` test-network, com um perfil `ChannelUsingRaft` de 4 consenters EtcdRaft espelhando a topologia do SmartBFT. As duas topologias (`Raft/raft_network` e `SmartBFT/smartbft_network`) estão versionadas neste repositório já com todas as customizações aplicadas.
* **Cargas de trabalho:** `CreateAsset`, `ReadAsset` e `TransferAsset`, testadas em três taxas-alvo de TPS: **50, 160 e 270** (270 TPS identificado como o teto de throughput do ambiente).
* **Rounds:** 10 rounds completos por algoritmo de consenso, cada um com ~300 segundos de duração, precedidos por uma rodada de *warmup* para eliminar viés de cold-start.
* **Independência estatística:** a rede é resetada (teardown/startup completo) entre cada round.
* **Ferramenta de benchmark:** [Hyperledger Caliper](https://hyperledger-caliper.github.io/caliper/) 0.6, usando o binding `fabric:fabric-gateway` (SDK 1.5.0), com Node.js 18/20.

## 📊 Monitoramento

O consumo de recursos durante cada round é coletado com:

* **cAdvisor** — métricas de containers (CPU/RAM);
* **Prometheus** — scraping das métricas de orderers (porta 9443) e peers (portas 9444/9445);
* **Grafana** — dashboards para visualização e correlação temporal dos dados de cada round.

Os timestamps de cada round são registrados para permitir a correlação precisa entre os resultados do Caliper e as métricas de infraestrutura coletadas no Grafana.

## 📂 Estrutura do Projeto

```bash
TCC---Blockchain/
├── Raft/
│   ├── caliper-workspace/         # Configuração e workloads do Caliper para a rede Raft
│   └── raft_network/              # Rede Fabric (test-network) customizada com perfil Raft de 4 consenters
├── SmartBFT/
│   ├── caliper-workspace/         # Configuração e workloads do Caliper para a rede SmartBFT
│   └── smartbft_network/          # Rede Fabric (test-network) customizada com consenso SmartBFT
├── bash-scripts/                  # Scripts de orquestração (rede, benchmark, coleta de timestamps)
├── caliper-relatorios/            # Relatórios e resultados brutos gerados pelo Hyperledger Caliper (dados da pesquisa)
├── fabric-monitoring/             # Configuração do stack de monitoramento (cAdvisor, Prometheus, Grafana)
├── graficos_python/               # Scripts em Python para análise estatística e geração de gráficos
├── install-fabric.sh              # Script de instalação do Hyperledger Fabric
└── README.md                      # Esta documentação
```

> **Nota:** `node_modules/`, binários do Fabric (`bin/`, `config/`, `builders/`), material criptográfico gerado em runtime e o binário completo do Prometheus **não são versionados** (ver `.gitignore`). As instruções abaixo cobrem como gerar/baixar tudo isso do zero.

## ⚙️ Pré-requisitos

| Ferramenta | Versão usada | Observação |
|---|---|---|
| **Hyperledger Fabric** | v3.1.4 | binários e imagens Docker |
| **Docker Engine** | 28.0.0 | versões ≥29.x apresentaram incompatibilidade (broken pipe no install de chaincode) |
| **Node.js** | 18 ou 20 | exigido pelo SDK `fabric-gateway` 1.5.0 e pelo Caliper |
| **Hyperledger Caliper** | 0.6 | instalado via `npm` dentro de cada `caliper-workspace` |
| **Python** | 3.x + `venv` | para os scripts de análise estatística e geração de gráficos |
| **Prometheus** | 2.53.0 | baixado manualmente (binário, não versionado no repo) |
| **cAdvisor** | v0.57.0 | roda via Docker |
| **Grafana** | — | roda via Docker, dashboard importado pelo ID `14282` |
| **SO testado** | Linux Mint 22 (base Ubuntu 24.04 Noble) | deve funcionar em qualquer distro Ubuntu-based |

## 🚀 Como Executar

### 1. Clone o repositório

```bash
git clone https://github.com/yVinicin/TCC---Blockchain.git
cd TCC---Blockchain
```

### 2. Instale o Hyperledger Fabric (binários + imagens Docker)

```bash
curl -sSLO https://raw.githubusercontent.com/hyperledger/fabric/main/scripts/install-fabric.sh
chmod +x install-fabric.sh
./install-fabric.sh docker binary
```

Isso gera as pastas `bin/`, `config/` e `builders/` usadas por `raft_network/` e `smartbft_network/` (copie-as para dentro de cada uma, ou ajuste o `PATH`/variáveis conforme o script `install-fabric.sh` indicar).

### 3. Instale as dependências Node.js do Caliper (em cada topologia)

```bash
cd Raft/caliper-workspace && npm install && cd ../..
cd SmartBFT/caliper-workspace && npm install && cd ../..
```

### 4. Crie o ambiente virtual Python e instale as dependências de análise

```bash
cd graficos_python
python3 -m venv venv
source venv/bin/activate
pip install pandas numpy matplotlib scipy beautifulsoup4
cd ..
```

### 5. Suba a rede com o consenso desejado

```bash
./bash-scripts/rede.sh raft
# ou
./bash-scripts/rede.sh smartbft
# para derrubar:
./bash-scripts/rede.sh down
```

### 6. Suba o stack de monitoramento (Prometheus + cAdvisor + Grafana)

```bash
./fabric-monitoring/install-prometheus.sh   # baixa o binário do Prometheus (ignorado no git)
./bash-scripts/start-monitoring.sh
```

Acesse o Grafana (porta padrão `3000`) e importe o dashboard ID `14282`, ajustando o datasource para a UID configurada localmente.

### 7. Execute o benchmark completo

```bash
./bash-scripts/caliper-benchmark.sh raft
```
ou
```bash
./bash-scripts/caliper-benchmark.sh smartbft
```

Esse script cuida do teardown/startup da rede, espera de estabilização, execução do Caliper (10 rounds por TPS alvo) e arquivamento dos relatórios em `caliper-relatorios/`.

### 8. Gere os gráficos e a análise estatística

```bash
source graficos_python/venv/bin/activate
python3 graficos_python/latencia.py
python3 graficos_python/throughput.py
python3 graficos_python/recursos.py
python3 graficos_python/eficiencia.py
python3 graficos_python/metricas_estatisticas.py
```

## 📈 Status Atual

Os 10 rounds completos de benchmark já foram concluídos tanto para **Raft** quanto para **SmartBFT**. A etapa atual é a geração dos gráficos e a extração das métricas estatísticas finais para compor o relatório do TCC.
