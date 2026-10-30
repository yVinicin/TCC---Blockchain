# ⛓️ TCC — Análise Comparativa de Desempenho dos Mecanismos de Consenso Raft e SmartBFT no Hyperledger Fabric 3.0

> Repositório do Trabalho de Conclusão de Curso em Ciência da Computação pela Universidade Estadual do Oeste do Paraná (UNIOESTE), desenvolvido para avaliar experimentalmente o desempenho dos mecanismos de consenso **Raft** e **SmartBFT** no Hyperledger Fabric 3.0.

![Blockchain](https://img.shields.io/badge/Blockchain-Hyperledger%20Fabric%203.0-2F3134?logo=hyperledger&logoColor=white)
![Benchmark](https://img.shields.io/badge/Benchmark-Hyperledger%20Caliper-orange)
![Monitoring](https://img.shields.io/badge/Monitoring-Prometheus%20%2B%20Grafana-E6522C?logo=grafana&logoColor=white)
![Academic](https://img.shields.io/badge/Trabalho-TCC-blue)

## 📖 Sobre o Projeto

Este repositório contém a infraestrutura experimental, os scripts de execução, as configurações de rede, os relatórios de benchmark e os recursos utilizados no desenvolvimento do Trabalho de Conclusão de Curso intitulado **Análise comparativa de desempenho dos mecanismos de consenso Raft e SmartBFT no Hyperledger Fabric 3.0**.

O objetivo do trabalho é investigar o impacto da utilização de diferentes mecanismos de consenso sobre o desempenho de uma blockchain permissionada, considerando três métricas principais:

- **Vazão (throughput):** quantidade de transações processadas por segundo (TPS).
- **Latência:** tempo decorrido entre a submissão de uma transação e sua confirmação.
- **Consumo de recursos computacionais:** utilização de CPU e memória RAM pelos nós da rede.

A pesquisa compara os protocolos em condições normais de operação, submetendo as redes a diferentes cargas de trabalho. O estudo busca identificar os pontos de saturação da infraestrutura e caracterizar o custo computacional associado a cada mecanismo de consenso.

## 🧪 Metodologia Experimental

### Configuração das redes

Foram configuradas duas redes Hyperledger Fabric com topologias equivalentes, diferenciadas pelo mecanismo de consenso utilizado:

- **Raft:** protocolo com tolerância a falhas de parada (CFT — *Crash Fault Tolerance*).
- **SmartBFT:** protocolo com tolerância a falhas bizantinas (BFT — *Byzantine Fault Tolerance*).

Ambas as redes utilizam quatro nós ordenadores (*orderers*) e dois nós pares (*peers*), mantendo a topologia constante para permitir uma comparação controlada entre os protocolos.

### Cargas de trabalho

Os experimentos utilizam três operações de *chaincode*:

| Operação | Descrição | Patamares de carga |
|---|---|---|
| `CreateAsset` | Escrita de ativos no livro-razão. | 100, 200 e 300 TPS alvo |
| `ReadAsset` | Leitura de ativos. | 100, 200, 300, 400, 500, 600 e 700 TPS alvo |
| `TransferAsset` | Operação de leitura seguida de escrita. | 100, 200 e 300 TPS alvo |

Os maiores patamares foram definidos para identificar a saturação da infraestrutura. Para as operações de escrita e transferência, foi utilizado o alvo de 300 TPS. Para a operação de leitura, a carga foi elevada até 700 TPS, devido à maior capacidade de processamento observada nesse cenário.

Antes dos testes de leitura e transferência, o livro-razão é inicializado com 1.000 ativos.

### Repetições e análise estatística

Foram realizadas **260 execuções experimentais**, distribuídas igualmente entre os dois protocolos:

- 130 execuções com Raft;
- 130 execuções com SmartBFT;
- 10 repetições para cada patamar de carga de cada operação.

Os relatórios gerados pelo Hyperledger Caliper são utilizados na análise comparativa. Os resultados são avaliados por meio de estatística descritiva, considerando média, desvio padrão, variância e intervalo de confiança de 95%.

### Ferramentas utilizadas

- **Hyperledger Fabric:** plataforma blockchain permissionada.
- **Hyperledger Caliper:** execução dos benchmarks e coleta das métricas de transação.
- **Docker:** execução dos componentes da infraestrutura em contêineres.
- **cAdvisor:** coleta de métricas de utilização de recursos dos contêineres.
- **Prometheus:** armazenamento e consulta de métricas em séries temporais.
- **Grafana:** visualização e análise dos dados de monitoramento.
- **Python:** processamento dos resultados, análise estatística e geração de gráficos.

## 📊 Monitoramento da Infraestrutura

O monitoramento complementa os resultados do benchmark, permitindo relacionar o comportamento das transações ao consumo de recursos computacionais.

| Ferramenta | Finalidade |
|---|---|
| cAdvisor | Coletar métricas de CPU e memória RAM dos contêineres. |
| Prometheus | Armazenar e disponibilizar as métricas coletadas. |
| Grafana | Visualizar o comportamento dos nós durante os experimentos. |
| Scripts Python | Processar os dados e gerar gráficos comparativos. |

As métricas de utilização de CPU e memória RAM são coletadas durante os testes para investigar as diferenças de custo computacional entre Raft e SmartBFT.

## 📈 Principais Resultados

Os experimentos demonstraram que os dois protocolos apresentam desempenho semelhante em cargas baixas e intermediárias, mas diferenças mais evidentes surgem próximo à saturação da infraestrutura.

Os principais resultados de vazão observados foram:

| Operação | Raft | SmartBFT |
|---|---:|---:|
| `CreateAsset` | 293,44 TPS | 270,17 TPS |
| `ReadAsset` | 683,21 TPS | 681,37 TPS |
| `TransferAsset` | 293,48 TPS | 273,28 TPS |

*Valores médios observados nos respectivos pontos de saturação.*

A análise também identificou diferenças no consumo de recursos: o SmartBFT apresentou maior custo de processamento de CPU nos nós ordenadores, enquanto o Raft apresentou maior consumo de memória RAM nos cenários avaliados. Sob alta carga, o SmartBFT também apresentou aumento mais acentuado da latência.

Esses resultados evidenciam um *trade-off* entre os mecanismos de consenso, considerando o desempenho observado e as propriedades de tolerância a falhas oferecidas por cada protocolo.

**Limitação importante:** os experimentos foram conduzidos em condições normais de operação. Não foram realizados testes com injeção de nós maliciosos ou interrupções deliberadas de nós; portanto, os resultados não constituem uma avaliação experimental direta da resiliência a falhas bizantinas.

## 📂 Estrutura do Projeto

```text
TCC---Blockchain/
├── Raft/
│   ├── caliper-workspace/     # Configurações e workloads do Caliper
│   └── raft_network/          # Rede Fabric configurada com Raft
├── SmartBFT/
│   ├── caliper-workspace/     # Configurações e workloads do Caliper
│   └── smartbft_network/      # Rede Fabric configurada com SmartBFT
├── bash-scripts/              # Scripts de gerenciamento e benchmark
├── caliper-relatorios/        # Relatórios e resultados dos experimentos
├── fabric-monitoring/         # Configurações do monitoramento
├── graficos_python/           # Scripts de análise e geração de gráficos
├── install-fabric.sh          # Script de instalação, se aplicável à versão
└── README.md                  # Documentação do projeto
```

> **Observação:** a estrutura acima representa a organização lógica do projeto. Os arquivos efetivamente presentes em cada diretório podem variar conforme a versão do repositório. Binários, dependências locais, material criptográfico gerado durante a execução e outros artefatos podem não estar versionados.

## ⚙️ Ambiente Experimental

Os experimentos descritos na monografia foram realizados no seguinte ambiente:

| Componente | Versão ou configuração |
|---|---|
| Sistema operacional | Linux Mint Cinnamon 22.3 |
| Processador | Intel Core i5-1335U |
| Memória RAM | 8 GB |
| Armazenamento | SSD NVMe de 512 GB |
| Docker | 28.0.0 |
| Hyperledger Fabric | 3.0.0 |
| Hyperledger Caliper | 0.6.0 |
| Prometheus | 2.53.0 |
| Grafana | 13.0.2 |
| cAdvisor | 0.57.0 |

Para reproduzir os experimentos, também é necessário instalar as dependências específicas dos scripts de benchmark, do *chaincode* e dos programas de análise. Consulte as configurações presentes nos diretórios correspondentes antes de instalar versões adicionais de ferramentas.

## 🚀 Como Executar

As instruções a seguir apresentam o fluxo geral para preparar o ambiente e executar os experimentos. Os comandos pressupõem que os scripts mencionados estejam presentes no repositório e que suas dependências tenham sido configuradas.

### 1. Clonar o repositório

```bash
git clone https://github.com/yVinicin/TCC---Blockchain.git
cd TCC---Blockchain
```

### 2. Preparar as redes Hyperledger Fabric

Prepare os binários, as imagens Docker e as configurações exigidas pela versão do Fabric utilizada no projeto.

```bash
cd Raft/raft_network
```

Siga as instruções de instalação compatíveis com o Fabric 3.0.0 e com os arquivos de configuração existentes nessa pasta. Repita o procedimento para `SmartBFT/smartbft_network`.

> **Importante:** o script oficial de instalação pode baixar a versão corrente do Fabric se não houver uma versão explicitamente fixada. Para reproduzir os experimentos da monografia, confirme que os binários e as imagens utilizados correspondem ao Fabric 3.0.0.

### 3. Instalar as dependências do Hyperledger Caliper

Se os diretórios de benchmark possuírem seus próprios arquivos `package.json`, instale as dependências em cada um deles:

```bash
cd Raft/caliper-workspace
npm install
cd ../..

cd SmartBFT/caliper-workspace
npm install
cd ../..
```

Utilize uma versão do Node.js compatível com as dependências declaradas nos arquivos de configuração do projeto.

### 4. Preparar o ambiente Python

Crie um ambiente virtual para instalar as bibliotecas utilizadas nos scripts de análise:

```bash
cd graficos_python
python3 -m venv venv
source venv/bin/activate
```

Instale as dependências necessárias de acordo com os imports presentes nos scripts. Caso sejam utilizadas as bibliotecas abaixo, a instalação pode ser feita com:

```bash
pip install pandas numpy matplotlib scipy beautifulsoup4
```

### 5. Iniciar a rede

Se o script de gerenciamento estiver disponível na versão atual do repositório, selecione o protocolo desejado:

```bash
./bash-scripts/rede.sh raft
```

Para iniciar a rede com SmartBFT:

```bash
./bash-scripts/rede.sh smartbft
```

Para encerrar a rede:

```bash
./bash-scripts/rede.sh down
```

Verifique o conteúdo do script `rede.sh` para confirmar quais etapas de criação do canal, configuração da rede e instalação do *chaincode* são automatizadas.

### 6. Iniciar o monitoramento

Prepare o Prometheus e inicie os serviços de monitoramento conforme as configurações disponíveis no diretório `fabric-monitoring/`.

Se o projeto possuir o script correspondente:

```bash
./fabric-monitoring/install-prometheus.sh
./bash-scripts/start-monitoring.sh
```

Quando os serviços estiverem disponíveis, acesse o Grafana pelo endereço e pela porta definidos na configuração local. Configure o datasource do Prometheus e os dashboards necessários.

### 7. Executar os benchmarks

Se o script de automação estiver presente:

```bash
./bash-scripts/caliper-benchmark.sh
```

Antes da execução, confirme os patamares de carga, o número de repetições, os parâmetros de inicialização e os diretórios de saída. Para reproduzir a metodologia da monografia, mantenha as mesmas condições experimentais para os dois protocolos.

### 8. Gerar os gráficos e analisar os resultados

Ative o ambiente virtual Python:

```bash
source graficos_python/venv/bin/activate
```

Execute os scripts de análise disponíveis:

```bash
python3 graficos_python/latencia.py
python3 graficos_python/throughput.py
python3 graficos_python/recursos.py
python3 graficos_python/eficiencia.py
python3 graficos_python/metricas_estatisticas.py
```

Os nomes dos arquivos acima devem ser conferidos na versão atual do repositório. Os scripts processam os resultados experimentais para apoiar a análise de vazão, latência, consumo de recursos e métricas estatísticas.

## 🎓 Trabalho Acadêmico

**Título:** Análise comparativa de desempenho dos mecanismos de consenso Raft e SmartBFT no Hyperledger Fabric 3.0.

**Autor:** Vinicius Mattos Marcos.

**Instituição:** Universidade Estadual do Oeste do Paraná (UNIOESTE) — Centro de Ciências Exatas e Tecnológicas, Curso de Ciência da Computação.

**Orientador:** Luiz Antonio Rodrigues.

**Ano:** 2026.

## 📚 Referência ao Repositório

O repositório contém os recursos utilizados na execução dos experimentos e na elaboração dos resultados apresentados na monografia.

- **Código-fonte e configurações:** https://github.com/yVinicin/TCC---Blockchain
- **Tema da pesquisa:** avaliação experimental de desempenho de protocolos de consenso em uma blockchain permissionada.
- **Métricas analisadas:** vazão, latência, consumo de CPU e memória RAM.

---

*Este projeto foi desenvolvido para fins acadêmicos, como parte de um Trabalho de Conclusão de Curso em Ciência da Computação.*
