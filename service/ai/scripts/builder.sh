#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

AI_BASE_IMAGE="${AI_BASE_IMAGE:-python:3.11-slim}"
AI_IMAGE_TAG="${AI_IMAGE_TAG:-gblob-ai:local}"

docker buildx build \
  --build-arg AI_BASE_IMAGE="${AI_BASE_IMAGE}" \
  --load \
  -t "${AI_IMAGE_TAG}" \
  -f "${SERVICE_DIR}/docker/Dockerfile" \
  "${SERVICE_DIR}"
