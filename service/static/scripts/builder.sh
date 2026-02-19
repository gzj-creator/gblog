#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

STATIC_BASE_IMAGE="${STATIC_BASE_IMAGE:-ubuntu-24.04:galay-web-1.0}"
GALAY_KERNEL_BACKEND="${GALAY_KERNEL_BACKEND:-epoll}"
OUTPUT_DIR="${OUTPUT_DIR:-${SERVICE_DIR}/bin}"

docker buildx build \
  --build-arg STATIC_BASE_IMAGE="${STATIC_BASE_IMAGE}" \
  --build-arg GALAY_KERNEL_BACKEND="${GALAY_KERNEL_BACKEND}" \
  --target artifact \
  --output type=local,dest="${OUTPUT_DIR}" \
  -f "${SERVICE_DIR}/docker/Dockerfile" \
  "${SERVICE_DIR}"
