#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${PROJECT_ROOT}/docker-compose.yml}"
ACTION="${1:-up}"

usage() {
  cat <<USAGE
Usage: $(basename "$0") [up|build|down|restart|ps|logs]

Environment variables (optional):
  SERVICE_MOUNT_ROOT    Base host mount dir (default: /root/service)
  GALAY_BASE_IMAGE      Base image for C++ services (default: ubuntu:galay-v1)
  GALAY_KERNEL_BACKEND  Galay backend macro (default: epoll)

Per-service overrides (examples):
  GATEWAY_CONFIG_DIR, GATEWAY_LOGS_DIR, GATEWAY_FRONTEND_DIR
  BUSINESS_CONFIG_DIR, BUSINESS_LOGS_DIR
  AUTH_CONFIG_DIR, AUTH_LOGS_DIR
  DB_CONFIG_DIR, DB_LOGS_DIR
  ADMIN_CONFIG_DIR, ADMIN_LOGS_DIR, ADMIN_MANAGED_DOCS_DIR
  AI_CONFIG_DIR, AI_LOGS_DIR, AI_DATA_DIR, AI_ENV_FILE
  INDEXER_CONFIG_DIR, INDEXER_LOGS_DIR
USAGE
}

set_default() {
  local var_name="$1"
  local default_value="$2"
  if [[ -z "${!var_name:-}" ]]; then
    printf -v "$var_name" '%s' "$default_value"
  fi
  export "$var_name"
}

ensure_dir() {
  local dir="$1"
  mkdir -p "$dir"
}

copy_if_missing() {
  local src="$1"
  local dst="$2"
  if [[ ! -f "$dst" ]]; then
    cp "$src" "$dst"
  fi
}

resolve_compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
    return
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose)
    return
  fi
  echo "[ERROR] docker compose/docker-compose not found" >&2
  exit 1
}

prepare_mounts() {
  set_default SERVICE_MOUNT_ROOT "/root/service"
  set_default GALAY_BASE_IMAGE "ubuntu:galay-v1"
  set_default GALAY_KERNEL_BACKEND "epoll"

  set_default DB_CONFIG_DIR "${SERVICE_MOUNT_ROOT}/db/config"
  set_default DB_LOGS_DIR "${SERVICE_MOUNT_ROOT}/db/logs"

  set_default AUTH_CONFIG_DIR "${SERVICE_MOUNT_ROOT}/auth/config"
  set_default AUTH_LOGS_DIR "${SERVICE_MOUNT_ROOT}/auth/logs"

  set_default BUSINESS_CONFIG_DIR "${SERVICE_MOUNT_ROOT}/business/config"
  set_default BUSINESS_LOGS_DIR "${SERVICE_MOUNT_ROOT}/business/logs"

  set_default GATEWAY_CONFIG_DIR "${SERVICE_MOUNT_ROOT}/gateway/config"
  set_default GATEWAY_LOGS_DIR "${SERVICE_MOUNT_ROOT}/gateway/logs"
  set_default GATEWAY_FRONTEND_DIR "${SERVICE_MOUNT_ROOT}/gateway/frontend"

  set_default ADMIN_CONFIG_DIR "${SERVICE_MOUNT_ROOT}/admin/config"
  set_default ADMIN_LOGS_DIR "${SERVICE_MOUNT_ROOT}/admin/logs"
  set_default ADMIN_MANAGED_DOCS_DIR "${SERVICE_MOUNT_ROOT}/admin/managed_docs"

  set_default AI_CONFIG_DIR "${SERVICE_MOUNT_ROOT}/ai/config"
  set_default AI_LOGS_DIR "${SERVICE_MOUNT_ROOT}/ai/logs"
  set_default AI_DATA_DIR "${SERVICE_MOUNT_ROOT}/ai/data"
  set_default AI_ENV_FILE "${AI_CONFIG_DIR}/.env"

  set_default INDEXER_CONFIG_DIR "${SERVICE_MOUNT_ROOT}/indexer/config"
  set_default INDEXER_LOGS_DIR "${SERVICE_MOUNT_ROOT}/indexer/logs"

  ensure_dir "$DB_CONFIG_DIR"
  ensure_dir "$DB_LOGS_DIR"
  ensure_dir "$AUTH_CONFIG_DIR"
  ensure_dir "$AUTH_LOGS_DIR"
  ensure_dir "$BUSINESS_CONFIG_DIR"
  ensure_dir "$BUSINESS_LOGS_DIR"
  ensure_dir "$GATEWAY_CONFIG_DIR"
  ensure_dir "$GATEWAY_LOGS_DIR"
  ensure_dir "$GATEWAY_FRONTEND_DIR"
  ensure_dir "$ADMIN_CONFIG_DIR"
  ensure_dir "$ADMIN_LOGS_DIR"
  ensure_dir "$ADMIN_MANAGED_DOCS_DIR"
  ensure_dir "$AI_CONFIG_DIR"
  ensure_dir "$AI_LOGS_DIR"
  ensure_dir "$AI_DATA_DIR"
  ensure_dir "$INDEXER_CONFIG_DIR"
  ensure_dir "$INDEXER_LOGS_DIR"

  copy_if_missing "${PROJECT_ROOT}/service/gateway/config/static-server.conf" "${GATEWAY_CONFIG_DIR}/static-server.conf"
  copy_if_missing "${PROJECT_ROOT}/service/ai/.env.example" "$AI_ENV_FILE"

  if [[ ! -f "${GATEWAY_FRONTEND_DIR}/index.html" ]]; then
    cp -R "${PROJECT_ROOT}/frontend/." "$GATEWAY_FRONTEND_DIR/"
  fi

  if [[ ! -f "${ADMIN_CONFIG_DIR}/admin_config.json" ]]; then
    cat > "${ADMIN_CONFIG_DIR}/admin_config.json" <<JSON
{
  "managed_docs_path": "/app/managed_docs"
}
JSON
  fi

  echo "[INFO] mount root: ${SERVICE_MOUNT_ROOT}"
  echo "[INFO] compose file: ${COMPOSE_FILE}"
}

run_compose() {
  case "$ACTION" in
    -h|--help|help)
      usage
      return 0
      ;;
  esac

  resolve_compose_cmd
  prepare_mounts

  case "$ACTION" in
    up)
      "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" build
      "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" up -d
      ;;
    build)
      "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" build
      ;;
    down)
      "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" down
      ;;
    restart)
      "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" build
      "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" up -d --force-recreate
      ;;
    ps)
      "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" ps
      ;;
    logs)
      shift || true
      "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" logs -f "$@"
      ;;
    *)
      usage
      echo "[ERROR] unknown action: $ACTION" >&2
      exit 1
      ;;
  esac
}

run_compose "$@"
