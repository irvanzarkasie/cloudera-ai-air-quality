#!/usr/bin/env bash
# Build an offline wheel cache for Cloudera AI (Linux x86_64, Python 3.11).
#
#   cd AirAware
#   bash scripts/build_cai_wheelhouse.sh
#   tar czf wheelhouse-cai-py311-linux.tar.gz wheelhouse/cai-py311-linux
#
# On macOS: downloads manylinux wheels (not macosx). pysqlite3-binary has no Mac wheel.
# Alternative: bash scripts/build_cai_wheelhouse_docker.sh
#
# Best match for your cluster: run this script inside a CAI Python 3.11 session once.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TAG="${WHEELHOUSE_TAG:-cai-py311-linux}"
OUT="${ROOT}/wheelhouse/${TAG}"
PY="${PYTHON:-python3.11}"

mkdir -p "$OUT"

PIP_EXTRA=()
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Host is $(uname -s): cross-downloading manylinux x86_64 / cp311 wheels for CAI ..."
  PIP_EXTRA=(
    --only-binary=:all:
    --platform manylinux2014_x86_64
    --platform manylinux_2_17_x86_64
    --platform manylinux_2_28_x86_64
    --python-version 3.11
  )
else
  echo "Downloading wheels on Linux with ${PY} ..."
fi

echo "Output: ${OUT}"
"${PY}" -m pip install -q --upgrade pip
"${PY}" -m pip download \
  "${PIP_EXTRA[@]}" \
  -r requirements-minimal.txt \
  -r requirements-crewai-addon.txt \
  -d "$OUT"

echo "Done. Wheel count: $(find "$OUT" -name '*.whl' | wc -l | tr -d ' ')"
echo "Pack for upload: tar czf wheelhouse-${TAG}.tar.gz -C wheelhouse ${TAG}"
