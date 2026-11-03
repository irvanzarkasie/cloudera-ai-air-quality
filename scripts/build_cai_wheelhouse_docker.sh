#!/usr/bin/env bash
# Build Linux wheelhouse from macOS/Windows using Docker (matches CAI amd64 in most deployments).
#
#   cd AirAware
#   bash scripts/build_cai_wheelhouse_docker.sh
#
# Apple Silicon: pulls linux/amd64 by default. Override: WHEELHOUSE_PLATFORM=linux/arm64
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLATFORM="${WHEELHOUSE_PLATFORM:-linux/amd64}"
IMAGE="${WHEELHOUSE_IMAGE:-python:3.11-slim}"

echo "Building wheelhouse in Docker (${PLATFORM}, ${IMAGE}) ..."
docker run --rm --platform "${PLATFORM}" \
  -v "${ROOT}:/work" -w /work \
  "${IMAGE}" \
  bash -c 'set -euo pipefail
    apt-get update -qq && apt-get install -y -qq --no-install-recommends ca-certificates >/dev/null
    python3.11 -m pip install -q --upgrade pip
    bash scripts/build_cai_wheelhouse.sh'

echo "Done. Pack with:"
echo "  tar czf wheelhouse-cai-py311-linux.tar.gz -C wheelhouse cai-py311-linux"
