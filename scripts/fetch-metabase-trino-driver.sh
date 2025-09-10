#!/usr/bin/env bash
set -euo pipefail

DRIVER_URL="https://github.com/starburstdata/metabase-driver/releases/download/6.1.0/starburst-6.1.0.metabase-driver.jar"
DRIVER_SHA256="dafe626d6edd6de66086cb91b98628b2289b9e538562769ff826d98b2dee3ac5"

DEST_DIR="./metabase-plugins"
DEST_FILE="${DEST_DIR}/starburst-6.1.0.metabase-driver.jar"

mkdir -p "${DEST_DIR}"
echo "Downloading Starburst Metabase driver v6.1.0..."
curl -L --fail --show-error "${DRIVER_URL}" -o "${DEST_FILE}"

echo "Verifying checksum..."
echo "${DRIVER_SHA256}  ${DEST_FILE}" | shasum -a 256 -c -

echo "Driver fetched and verified: ${DEST_FILE}"
