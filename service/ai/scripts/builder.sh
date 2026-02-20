#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_DIR="$(cd "${AI_DIR}/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${PROJECT_DIR}/docker-compose.yml}"
SERVICE_NAME="${SERVICE_NAME:-ai}"
CONTAINER_NAME="${CONTAINER_NAME:-gblob-ai}"

BUILD=true
NO_CACHE=false
FORCE_RECREATE=true
REBUILD_KB=true
RUN_EVAL=false
MIN_PASS_RATE="0.70"
GENERATE_DOCS=false
DOCS_ROOT_OVERRIDE=""

usage() {
  cat <<'EOF'
Usage: builder.sh [options]

One-click deploy for AI service.

Options:
  --no-build             Skip image build step
  --no-cache             Build image with --no-cache
  --no-force-recreate    Up container without --force-recreate
  --no-rebuild-kb        Skip rebuilding vector index after deploy
  --run-eval             Run KB evaluation after rebuild
  --min-pass-rate <v>    Pass threshold for evaluation (default: 0.70)
  --generate-docs        Ask rebuild_kb.py to generate galay docs before indexing
  --docs-root <path>     Override GALAY_DOCS_ROOT_PATH for compose up/build
  --help                 Show this help

Environment:
  COMPOSE_FILE           docker-compose file path (default: <project>/docker-compose.yml)
  SERVICE_NAME           compose service name (default: ai)
  CONTAINER_NAME         container name for docker exec (default: gblob-ai)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build)
      BUILD=false
      shift
      ;;
    --no-cache)
      NO_CACHE=true
      shift
      ;;
    --no-force-recreate)
      FORCE_RECREATE=false
      shift
      ;;
    --no-rebuild-kb)
      REBUILD_KB=false
      shift
      ;;
    --run-eval)
      RUN_EVAL=true
      shift
      ;;
    --min-pass-rate)
      MIN_PASS_RATE="${2:-}"
      shift 2
      ;;
    --generate-docs)
      GENERATE_DOCS=true
      shift
      ;;
    --docs-root)
      DOCS_ROOT_OVERRIDE="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "[ERROR] Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] docker command not found" >&2
  exit 1
fi

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "[ERROR] docker compose file not found: ${COMPOSE_FILE}" >&2
  exit 1
fi

run_compose() {
  if [[ -n "${DOCS_ROOT_OVERRIDE}" ]]; then
    GALAY_DOCS_ROOT_PATH="${DOCS_ROOT_OVERRIDE}" docker compose -f "${COMPOSE_FILE}" "$@"
  else
    docker compose -f "${COMPOSE_FILE}" "$@"
  fi
}

echo "============================================"
echo "AI One-Click Deploy"
echo "============================================"
echo "Project: ${PROJECT_DIR}"
echo "Compose: ${COMPOSE_FILE}"
echo "Service: ${SERVICE_NAME}"
echo "Container: ${CONTAINER_NAME}"
echo "Build: ${BUILD}"
echo "No cache: ${NO_CACHE}"
echo "Force recreate: ${FORCE_RECREATE}"
echo "Rebuild KB: ${REBUILD_KB}"
echo "Run eval: ${RUN_EVAL}"
echo "============================================"

if [[ "${BUILD}" == "true" ]]; then
  build_args=(build)
  if [[ "${NO_CACHE}" == "true" ]]; then
    build_args+=(--no-cache)
  fi
  build_args+=("${SERVICE_NAME}")
  echo "[INFO] Building image via compose..."
  run_compose "${build_args[@]}"
fi

up_args=(up -d)
if [[ "${FORCE_RECREATE}" == "true" ]]; then
  up_args+=(--force-recreate)
fi
up_args+=("${SERVICE_NAME}")
echo "[INFO] Starting service..."
run_compose "${up_args[@]}"

echo "[INFO] Waiting for service startup..."
sleep 2

if command -v curl >/dev/null 2>&1; then
  for _ in $(seq 1 20); do
    if curl -fsS --max-time 2 "http://127.0.0.1:8000/health" >/tmp/gblob-ai-health.json 2>/dev/null; then
      echo "[INFO] Health check passed: $(cat /tmp/gblob-ai-health.json)"
      break
    fi
    sleep 1
  done
else
  echo "[WARN] curl not found, skip host health check"
fi

if [[ "${REBUILD_KB}" == "true" ]]; then
  rebuild_cmd="cd /app && python scripts/rebuild_kb.py --force"
  if [[ "${GENERATE_DOCS}" == "true" ]]; then
    rebuild_cmd+=" --generate-docs"
  fi
  echo "[INFO] Rebuilding knowledge base..."
  docker exec "${CONTAINER_NAME}" sh -lc "${rebuild_cmd}"
fi

if [[ "${RUN_EVAL}" == "true" ]]; then
  echo "[INFO] Running KB evaluation..."
  docker exec "${CONTAINER_NAME}" sh -lc \
    "cd /app && python scripts/evaluate_kb.py --mode all --min-pass-rate ${MIN_PASS_RATE}"
fi

echo "[OK] AI deploy finished."
