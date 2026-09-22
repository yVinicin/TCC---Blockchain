```bash
#!/bin/bash

set -e

PROMETHEUS_VERSION="2.53.0"
ARCH="linux-amd64"
PROMETHEUS_DIR="prometheus-${PROMETHEUS_VERSION}.${ARCH}"
DOWNLOAD_URL="https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/${PROMETHEUS_DIR}.tar.gz"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo " Instalação do Prometheus ${PROMETHEUS_VERSION}"
echo "=========================================="

if [ -f "${PROMETHEUS_DIR}/prometheus" ]; then
    echo "Prometheus ${PROMETHEUS_VERSION} já está instalado."
    exit 0
fi

echo "Baixando Prometheus ${PROMETHEUS_VERSION}..."

curl -L -o "${PROMETHEUS_DIR}.tar.gz" "$DOWNLOAD_URL"

echo "Extraindo arquivo..."

tar -xzf "${PROMETHEUS_DIR}.tar.gz"

rm "${PROMETHEUS_DIR}.tar.gz"

echo "=========================================="
echo " Prometheus instalado com sucesso!"
echo "=========================================="
echo "Diretório: ${SCRIPT_DIR}/${PROMETHEUS_DIR}"
```
