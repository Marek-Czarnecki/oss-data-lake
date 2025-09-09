#!/usr/bin/env bash
set -euo pipefail

# ===== REQUIRED: fill these =====
: "${DRIVER_URL:?Set DRIVER_URL to the exact .jar download URL}"
: "${DRIVER_SHA256:?Set DRIVER_SHA256 to the published sha256 for that .jar}"

DEST_DIR="./metabase-plugins"
DEST_FILE="${DEST_DIR}/metabase-trino-driver.jar"

mkdir -p "${DEST_DIR}"
echo "Downloading driver from: ${DRIVER_URL}"
curl -L --fail --show-error "${DRIVER_URL}" -o "${DEST_FILE}"

echo "Verifying SHA256..."
echo "${DRIVER_SHA256}  ${DEST_FILE}" | shasum -a 256 -c -

echo "Driver OK: ${DEST_FILE}"
