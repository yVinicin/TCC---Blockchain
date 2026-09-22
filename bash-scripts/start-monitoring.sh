#!/bin/bash
# start-monitoring.sh — sobe o stack de monitoramento completo (Fabric 3.0)
set -e

PROMETHEUS_VOLUME="1a5830dd1af350d9464edf03b5bb316f9c5584122c5656c86563d91fe621dfd9"
PROMETHEUS_CONFIG="/home/vinicin/TCC/fabric-monitoring/prometheus/prometheus.yml"

# ─────────────────────────────────────────────
echo "==> Iniciando cAdvisor..."
docker rm -f cadvisor 2>/dev/null || true

docker run \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  --volume=/dev/disk/:/dev/disk:ro \
  --publish=8080:8080 \
  --detach=true \
  --name=cadvisor \
  --privileged \
  --device=/dev/kmsg \
  --restart=unless-stopped \
  ghcr.io/google/cadvisor:v0.57.0 \
  --housekeeping_interval=10s \
  --docker_only=true \
  --store_container_labels=true

# ─────────────────────────────────────────────
echo "==> Iniciando Prometheus..."
docker rm -f prometheus 2>/dev/null || true

docker run -d \
  --name prometheus \
  --restart unless-stopped \
  -p 9090:9090 \
  -v "$PROMETHEUS_CONFIG":/etc/prometheus/prometheus.yml:ro \
  -v "$PROMETHEUS_VOLUME":/prometheus \
  prom/prometheus:v2.53.0 \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --web.console.libraries=/usr/share/prometheus/console_libraries \
  --web.console.templates=/usr/share/prometheus/consoles \
  --web.enable-lifecycle

# ─────────────────────────────────────────────
echo "==> Conectando redes..."

# Rede monitoring (Grafana + cAdvisor)
docker network connect monitoring prometheus 2>/dev/null || true
docker network connect monitoring cadvisor  2>/dev/null || true

# Rede do Fabric ativo (Raft)
docker network connect fabric_test prometheus 2>/dev/null || true

# Descomente abaixo quando subir a rede SmartBFT:
# docker network connect <rede_smartbft> prometheus 2>/dev/null || true

# ─────────────────────────────────────────────
echo "==> Aguardando Prometheus iniciar..."
sleep 5
curl -s http://localhost:9090/-/healthy | grep -q "Healthy" && \
  echo "    Prometheus: OK" || echo "    Prometheus: ainda iniciando..."

# ─────────────────────────────────────────────
echo ""
echo "┌─────────────────────────────────────────┐"
echo "│         Stack de Monitoramento          │"
echo "├─────────────────────────────────────────┤"
echo "│  cAdvisor:   http://localhost:8080      │"
echo "│  Prometheus: http://localhost:9090      │"
echo "│  Grafana:    http://localhost:3000      │"
echo "└─────────────────────────────────────────┘"
echo ""
echo "Para recarregar o prometheus.yml sem reiniciar:"
echo "  curl -X POST http://localhost:9090/-/reload"
echo ""
echo "Para verificar os targets:"
echo "  curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool | grep -E 'job|health|lastError'"

