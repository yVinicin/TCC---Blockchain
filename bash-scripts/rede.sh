#!/bin/bash

set -e

RAFT_DIR=~/TCC/Raft/raft_network/test-network/
SMARTBFT_DIR=~/TCC/SmartBFT/smartbft_network/test-network/

case "$1" in

raft)
    # Entra na pasta do Raft
    cd "$RAFT_DIR"

    # Desliga a rede (caso tenha outra rede rodando)
    ./network.sh down

    # Sobe a rede Raft
    ./network.sh up createChannel

    # Faz o deploy do chaincode    
    ./network.sh deployCC \
      -ccn basic \
      -ccl go \
      -ccp ../asset-transfer-basic/chaincode-go

    ;;

smartbft)

    # Entra na pasta do SmartBFT
    cd "$SMARTBFT_DIR"

    # Desliga a rede (caso tenha outra rede rodando)
    ./network.sh down

    # Sobe a rede SmartBFT
    ./network.sh up createChannel -bft

    # Faz o deploy do chaincode   
    ./network.sh deployCC \
      -ccn basic \
      -ccl go \
      -ccp ../asset-transfer-basic/chaincode-go

    ;;

down)
    # Desliga as redes
    cd "$RAFT_DIR"
    ./network.sh down

    cd "$SMARTBFT_DIR"
    ./network.sh down

    ;;

*)

    echo "Uso:"
    echo "./rede.sh raft"
    echo "./rede.sh smartbft"
    echo "./rede.sh down"

    ;;

esac

