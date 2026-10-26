#!/bin/bash
set -e

RAFT_DIR=~/TCC/Raft/caliper-workspace/
SMARTBFT_DIR=~/TCC/SmartBFT/caliper-workspace/
CALIPER_REPORT=~/TCC/caliper-relatorios/
REDE_SCRIPT=~/TCC/bash-scripts/rede.sh
TOTAL_ROUNDS=10

# Operações executadas em cada rodada, com seus respectivos
# arquivos de benchconfig isolados.
OPERATIONS=(CreateAsset ReadAsset TransferAsset)
declare -A BENCHCONFIG=(
    [CreateAsset]="benchmarks/CreateAsset-benchmark.yaml"
    [ReadAsset]="benchmarks/ReadAsset-benchmark.yaml"
    [TransferAsset]="benchmarks/TransferAsset-benchmark.yaml"
)

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
        local ROUND_DIR="${REPORT_DIR}/round_${ROUND}"
        mkdir -p "$ROUND_DIR"

        echo ""
        echo "------------------------------------------------------------"
        echo " [$CONSENSUS] Rodada $ROUND/$TOTAL_ROUNDS"
        echo "------------------------------------------------------------"

        for OP in "${OPERATIONS[@]}"; do
            local OP_DIR="${ROUND_DIR}/${OP}"
            mkdir -p "$OP_DIR"

            # 1. Derruba a rede anterior (zera o ledger) - reset entre
            #    operações garante independência estatística
            echo "[$ROUND][$OP] Derrubando rede..."
            bash "$REDE_SCRIPT" down

            # 2. Sobe a rede do consenso correspondente e reinstala o chaincode
            echo "[$ROUND][$OP] Subindo rede $CONSENSUS..."
            bash "$REDE_SCRIPT" "$CONSENSUS"

            # Pausa para estabilização da rede (eleição de líder / view inicial)
            echo "[$ROUND][$OP] Aguardando estabilização da rede (15s)..."
            sleep 15

            local START_TIME
            START_TIME=$(TZ="America/Sao_Paulo" date +"%Y-%m-%dT%H:%M:%S%z")

            # 3. Executa o benchmark da operação
            echo "[$ROUND][$OP] Executando benchmark..."
            cd "$WORKDIR"

            npx caliper launch manager \
                --caliper-workspace ./ \
                --caliper-networkconfig "$NETWORK_CONFIG" \
                --caliper-benchconfig "${BENCHCONFIG[$OP]}" \
                --caliper-flow-only-test \
                2>&1 | tee "${OP_DIR}/caliper.log"

            local END_TIME
            END_TIME=$(TZ="America/Sao_Paulo" date +"%Y-%m-%dT%H:%M:%S%z")

            # 4. Move o relatório gerado para a pasta da própria operação
            if [[ -f "${WORKDIR}report.html" ]]; then
                mv "${WORKDIR}report.html" "${OP_DIR}/report.html"
                echo "[$ROUND][$OP] Relatório salvo em: ${OP_DIR}/report.html"
            else
                echo "[$ROUND][$OP] AVISO: report.html não encontrado!"
            fi

            # 5. Salva os timestamps da operação na sua própria pasta,
            #    para cruzar com Grafana/Prometheus depois
            cat > "${OP_DIR}/timestamps.txt" << EOF
round=$ROUND
operation=$OP
start=$START_TIME
end=$END_TIME
EOF

            echo "[$ROUND][$OP] Timestamps salvos em: ${OP_DIR}/timestamps.txt"
            echo "[$ROUND][$OP] Operação concluída."
        done

        echo "[$ROUND] Rodada concluída (3 operações)."
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

