#!/usr/bin/env bash
channel_name=$1
export PATH=${ROOTDIR}/../bin:${PWD}/../bin:$PATH

join_one_orderer() {
  local host=$1
  local admin_port=$2

  export ORDERER_ADMIN_TLS_SIGN_CERT=${PWD}/organizations/ordererOrganizations/example.com/orderers/${host}/tls/server.crt
  export ORDERER_ADMIN_TLS_PRIVATE_KEY=${PWD}/organizations/ordererOrganizations/example.com/orderers/${host}/tls/server.key

  osnadmin channel join --channelID ${channel_name} \
    --config-block ./channel-artifacts/${channel_name}.block \
    -o localhost:${admin_port} \
    --ca-file "${PWD}/organizations/ordererOrganizations/example.com/orderers/${host}/tls/ca.crt" \
    --client-cert "$ORDERER_ADMIN_TLS_SIGN_CERT" \
    --client-key "$ORDERER_ADMIN_TLS_PRIVATE_KEY" >> log.txt 2>&1
}

join_one_orderer "orderer.example.com"  7053
join_one_orderer "orderer2.example.com" 7055
join_one_orderer "orderer3.example.com" 7057
join_one_orderer "orderer4.example.com" 7059
