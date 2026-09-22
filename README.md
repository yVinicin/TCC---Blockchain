# ⛓️ TCC — Análise Comparativa de Mecanismos de Consenso no Hyperledger Fabric 3.0

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
* **Topologia equalizada:** 4 orderers / 2 organizações, montada a partir do `fabric-samples` test-network, com um perfil `ChannelUsingRaft` de 4 consenters EtcdRaft espelhando a topologia do SmartBFT.
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
├── Raft/                          # Topologia de rede Fabric configurada com consenso Raft
├── SmartBFT/                      # Topologia de rede Fabric configurada com consenso SmartBFT
├── bash-scripts/                  # Scripts de orquestração (rede, benchmark, coleta de timestamps)
├── caliper-relatorios/            # Relatórios e resultados brutos gerados pelo Hyperledger Caliper
├── fabric-monitoring/             # Configuração do stack de monitoramento (cAdvisor, Prometheus, Grafana)
├── graficos_python/               # Scripts em Python para análise estatística e geração de gráficos
├── install-fabric.sh              # Script de instalação do Hyperledger Fabric
├── links prometheus e grafana     # Referências/links úteis do stack de monitoramento
└── README.md                      # Esta documentação
```

## ⚙️ Ambiente de Desenvolvimento

* Hyperledger Fabric `v3.1.4`
* Docker Engine `28.0.0`
* Linux Mint 22 (base Ubuntu 24.04 Noble)

## 🚀 Como Executar

1.  **Clone o repositório:**
```bash
    git clone https://github.com/yVinicin/TCC---Blockchain.git
    cd TCC---Blockchain
```

2.  **Suba a rede** com o consenso desejado (`raft`, `smartbft` ou `down` para derrubar):
```bash
    ./bash-scripts/rede.sh raft
    # ou
    ./bash-scripts/rede.sh smartbft
```

3.  **Execute o benchmark completo** (teardown/startup da rede, espera de estabilização, execução do Caliper e arquivamento dos relatórios):
```bash
    ./bash-scripts/caliper-benchmark.sh
```

4.  **Gere os gráficos e a análise estatística** a partir dos relatórios coletados:
```bash
    python3 graficos_python/<script>.py
```

## 📈 Status Atual

Os 10 rounds completos de benchmark já foram concluídos tanto para **Raft** quanto para **SmartBFT**. A etapa atual é a geração dos gráficos e a extração das métricas estatísticas finais para compor o relatório do TCC.
