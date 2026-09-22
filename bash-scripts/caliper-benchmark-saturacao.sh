#!/bin/bash
set -e

RAFT_DIR=~/TCC/Raft/caliper-workspace/
SMARTBFT_DIR=~/TCC/SmartBFT/caliper-workspace/
CALIPER_REPORT=~/TCC/caliper-relatorios/
REDE_SCRIPT=~/TCC/bash-scripts/rede.sh
TOTAL_ROUNDS=1

run_benchmark() {
    local CONSENSUS=$1
    local WORKDIR=$2
    local NETWORK_CONFIG=$3

    local REPORT_DIR="${CALIPER_REPORT}${CONSENSUS}"
    mkdir -p "$REPORT_DIR"

    echo "============================================================"
    echo " Benchmark completo - Consenso: $CONSENSUS"
    echo " Total de rodadas: $TOTAL_ROUNDS"
    echo "============================================================"

    for ROUND in $(seq 1 $TOTAL_ROUNDS); do
        local ROUND_DIR="${REPORT_DIR}/saturacao"
        mkdir -p "$ROUND_DIR"

        local START_TIME
        START_TIME=$(TZ="America/Sao_Paulo" date +"%Y-%m-%dT%H:%M:%S%z")

        echo ""
        echo "------------------------------------------------------------"
        echo " [$CONSENSUS] Rodada $ROUND/$TOTAL_ROUNDS — Início: $START_TIME"
        echo "------------------------------------------------------------"

        # 1. Derruba a rede anterior (zera o ledger)
        echo "[$ROUND] Derrubando rede..."
        bash "$REDE_SCRIPT" down

        # 2. Sobe a rede do consenso correspondente e reinstala o chaincode
        echo "[$ROUND] Subindo rede $CONSENSUS..."
        bash "$REDE_SCRIPT" "$CONSENSUS"

        # Pausa para estabilização da rede (eleição de líder / view inicial)
        echo "[$ROUND] Aguardando estabilização da rede (15s)..."
        sleep 15

        # 3. Executa o benchmark
        echo "[$ROUND] Executando benchmark..."
        cd "$WORKDIR"

        npx caliper launch manager \
            --caliper-workspace ./ \
            --caliper-networkconfig "$NETWORK_CONFIG" \
            --caliper-benchconfig benchmarks/myBenchmark_saturacao.yaml \
            --caliper-flow-only-test

        local END_TIME
        END_TIME=$(TZ="America/Sao_Paulo" date +"%Y-%m-%dT%H:%M:%S%z")

        # 4. Move o relatório gerado para a pasta da rodada
        if [[ -f "${WORKDIR}report.html" ]]; then
            mv "${WORKDIR}report.html" "${ROUND_DIR}/report.html"
            echo "[$ROUND] Relatório salvo em: ${ROUND_DIR}/report.html"
        else
            echo "[$ROUND] AVISO: report.html não encontrado!"
        fi

        # 5. Salva os timestamps da rodada para cruzar com Grafana/Prometheus depois
        cat > "${ROUND_DIR}/timestamps.txt" << EOF
round=$ROUND
start=$START_TIME
end=$END_TIME
EOF

        echo "[$ROUND] Timestamps salvos em: ${ROUND_DIR}/timestamps.txt"
        echo "[$ROUND] Rodada concluída."
    done

    echo ""
    echo "============================================================"
    echo " Benchmark completo finalizado para: $CONSENSUS"
    echo " Relatórios disponíveis em: $REPORT_DIR"
    echo "============================================================"
}

case "$1" in
raft)
    run_benchmark "raft" "$RAFT_DIR" "networks/fabric-network-raft.yaml"
    ;;
smartbft)
    run_benchmark "smartbft" "$SMARTBFT_DIR" "networks/fabric-network-smartbft.yaml"
    ;;
*)
    echo "Uso:"
    echo "./caliper-benchmark.sh raft"
    echo "./caliper-benchmark.sh smartbft"
    ;;
esac

