#!/usr/bin/env bash
set -euo pipefail

# Optional: export LK_COMMIT=<commit_sha> to override the commit parsed from UPSTREAM.md
REPO_URL="https://raw.githubusercontent.com/lakekeeper-io/lakekeeper"

parse_commit() {
  # Look for a backticked hash in UPSTREAM.md after 'Commit:'
  if [[ -f "UPSTREAM.md" ]]; then
    grep -Eo 'Commit.*: `([0-9a-f]{7,40}|<COMMIT_SHA>)`' UPSTREAM.md | sed -E 's/.*`(.*)`/\1/'
  else
    echo ""
  fi
}

COMMIT="${LK_COMMIT:-$(parse_commit)}"
if [[ -z "${COMMIT}" || "${COMMIT}" == "<COMMIT_SHA>" ]]; then
  echo "ERROR: Lakekeeper commit is unknown. Set LK_COMMIT=<sha> or edit UPSTREAM.md (Commit line)."
  exit 1
fi

TMP_FILE="$(mktemp)"
echo "Fetching upstream compose at commit ${COMMIT} ..."
curl -fsSL "${REPO_URL}/${COMMIT}/examples/minimal/docker-compose.yaml" -o "${TMP_FILE}"

echo "Diff (upstream vs local docker-compose.yaml):"
if ! diff -u "${TMP_FILE}" docker-compose.yaml; then
  echo ""
  echo "▲ Differences detected. Review and decide whether to vendor updates."
  exit 2
fi

echo "✓ No differences."
