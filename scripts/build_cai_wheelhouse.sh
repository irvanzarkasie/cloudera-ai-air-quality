#!/usr/bin/env bash
# Build an offline wheel cache for Cloudera AI (Linux, Python 3.11).
# Run on a Linux machine or CAI session once; share the tarball with attendees.
#
#   cd AirAware
#   bash scripts/build_cai_wheelhouse.sh
#   tar czf wheelhouse-cai-py311-linux.tar.gz wheelhouse/cai-py311-linux
#
# Attendees: unpack into AirAware/, then the notebook installs from ./wheelhouse/... (no PyPI).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TAG="${WHEELHOUSE_TAG:-cai-py311-linux}"
OUT="${ROOT}/wheelhouse/${TAG}"
PY="${PYTHON:-python3.11}"

mkdir -p "$OUT"
echo "Downloading wheels with ${PY} into ${OUT} ..."
"${PY}" -m pip install -q --upgrade pip
"${PY}" -m pip download \
  -r requirements-minimal.txt \
  -r requirements-crewai-addon.txt \
  -d "$OUT"

echo "Done. Wheel count: $(find "$OUT" -name '*.whl' | wc -l | tr -d ' ')"
echo "Pack for upload: tar czf wheelhouse-${TAG}.tar.gz -C wheelhouse ${TAG}"
