#!/usr/bin/env bash
# Install workshop deps from a local wheelhouse only (no PyPI).
# Requires: wheelhouse/cai-py311-linux/*.whl (see scripts/build_cai_wheelhouse.sh)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TAG="${WHEELHOUSE_TAG:-cai-py311-linux}"
WH="${AIRAWARE_WHEELHOUSE:-${ROOT}/wheelhouse/${TAG}}"

if [[ ! -d "$WH" ]] || ! compgen -G "${WH}/*.whl" > /dev/null; then
  echo "Offline wheelhouse not found: ${WH}" >&2
  echo "Unpack the facilitator tarball, e.g.:" >&2
  echo "  tar xzf wheelhouse-${TAG}.tar.gz -C wheelhouse" >&2
  exit 1
fi

PY="${PYTHON:-python3.11}"
echo "Installing from ${WH} (no index) ..."
"${PY}" -m pip install --no-index --find-links="${WH}" \
  -r requirements-minimal.txt \
  -r requirements-crewai-addon.txt

echo "Offline install done."
