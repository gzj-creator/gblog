#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${AI_ROOT}/venv"
ENV_FILE="${AI_ROOT}/.env"
ENV_EXAMPLE="${AI_ROOT}/.env.example"

BUILD_INDEX=false
RUN_SERVER=false
NO_SYSTEM_DEPS=false
DOCS_ROOT=""
OPENAI_KEY=""
HOST="0.0.0.0"
PORT="8000"

log() {
  printf '[install] %s\n' "$1"
}

warn() {
  printf '[install][warn] %s\n' "$1" >&2
}

die() {
  printf '[install][error] %s\n' "$1" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  bash scripts/install_linux.sh [options]

Options:
  --docs-root <path>     Set GALAY_DOCS_ROOT_PATH in .env
  --api-key <key>        Set OPENAI_API_KEY in .env
  --build-index          Build vector index after install
  --run                  Run service after install
  --host <ip>            Host for --run (default: 0.0.0.0)
  --port <port>          Port for --run (default: 8000)
  --no-system-deps       Skip apt/yum/dnf/pacman/zypper/apk install
  -h, --help             Show this help

Examples:
  bash scripts/install_linux.sh --docs-root /opt/repos --api-key sk-xxx
  bash scripts/install_linux.sh --docs-root /opt/repos --build-index --run
EOF
}

run_with_sudo() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
    return
  fi

  if command -v sudo >/dev/null 2>&1; then
    sudo "$@"
    return
  fi

  die "Need root privileges for system package installation (sudo not found)."
}

install_system_deps() {
  if [[ "${NO_SYSTEM_DEPS}" == "true" ]]; then
    log "Skipping system dependency installation (--no-system-deps)."
    return
  fi

  if command -v apt-get >/dev/null 2>&1; then
    log "Installing system dependencies via apt-get."
    run_with_sudo apt-get update
    run_with_sudo apt-get install -y python3 python3-venv python3-pip
    return
  fi

  if command -v dnf >/dev/null 2>&1; then
    log "Installing system dependencies via dnf."
    run_with_sudo dnf install -y python3 python3-pip
    return
  fi

  if command -v yum >/dev/null 2>&1; then
    log "Installing system dependencies via yum."
    run_with_sudo yum install -y python3 python3-pip
    return
  fi

  if command -v pacman >/dev/null 2>&1; then
    log "Installing system dependencies via pacman."
    run_with_sudo pacman -Sy --noconfirm python python-pip
    return
  fi

  if command -v zypper >/dev/null 2>&1; then
    log "Installing system dependencies via zypper."
    run_with_sudo zypper --non-interactive install python3 python3-pip
    return
  fi

  if command -v apk >/dev/null 2>&1; then
    log "Installing system dependencies via apk."
    run_with_sudo apk add --no-cache python3 py3-pip
    return
  fi

  warn "No known package manager detected. Install Python 3.10+ and pip manually."
}

ensure_python() {
  command -v python3 >/dev/null 2>&1 || die "python3 not found."

  if python3 -m venv --help >/dev/null 2>&1; then
    return
  fi

  if [[ "${NO_SYSTEM_DEPS}" == "true" ]]; then
    die "python3-venv is missing. Re-run without --no-system-deps or install it manually."
  fi

  warn "python3 -m venv is unavailable, trying to install venv package."

  if command -v apt-get >/dev/null 2>&1; then
    run_with_sudo apt-get install -y python3-venv
  elif command -v dnf >/dev/null 2>&1; then
    run_with_sudo dnf install -y python3-virtualenv
  elif command -v yum >/dev/null 2>&1; then
    run_with_sudo yum install -y python3-virtualenv
  elif command -v pacman >/dev/null 2>&1; then
    run_with_sudo pacman -Sy --noconfirm python-virtualenv
  elif command -v zypper >/dev/null 2>&1; then
    run_with_sudo zypper --non-interactive install python3-virtualenv
  elif command -v apk >/dev/null 2>&1; then
    run_with_sudo apk add --no-cache py3-virtualenv
  else
    die "python3-venv is missing and no supported package manager detected."
  fi

  python3 -m venv --help >/dev/null 2>&1 || die "python3-venv is still unavailable after installation."
}

create_venv_and_install_python_deps() {
  if [[ ! -d "${VENV_DIR}" ]]; then
    log "Creating virtual environment: ${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"
  else
    log "Using existing virtual environment: ${VENV_DIR}"
  fi

  log "Installing Python dependencies."
  "${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel
  "${VENV_DIR}/bin/pip" install -r "${AI_ROOT}/requirements.txt"
}

init_env_file() {
  if [[ ! -f "${ENV_FILE}" ]]; then
    [[ -f "${ENV_EXAMPLE}" ]] || die ".env.example not found: ${ENV_EXAMPLE}"
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
    log "Created .env from .env.example"
  else
    log "Using existing .env"
  fi
}

upsert_env() {
  local key="$1"
  local value="$2"
  local escaped_value

  escaped_value="$(printf '%s' "${value}" | sed -e 's/[\/&]/\\&/g')"

  if grep -qE "^${key}=" "${ENV_FILE}"; then
    sed -i.bak -E "s|^${key}=.*|${key}=${escaped_value}|" "${ENV_FILE}"
  else
    printf '\n%s=%s\n' "${key}" "${value}" >>"${ENV_FILE}"
  fi
}

configure_env_values() {
  if [[ -n "${DOCS_ROOT}" ]]; then
    upsert_env "GALAY_DOCS_ROOT_PATH" "${DOCS_ROOT}"
    log "Configured GALAY_DOCS_ROOT_PATH=${DOCS_ROOT}"
  fi

  if [[ -n "${OPENAI_KEY}" ]]; then
    upsert_env "OPENAI_API_KEY" "${OPENAI_KEY}"
    log "Configured OPENAI_API_KEY in .env"
  fi

  rm -f "${ENV_FILE}.bak"
}

build_index_if_requested() {
  if [[ "${BUILD_INDEX}" != "true" ]]; then
    return
  fi

  log "Building vector index."
  "${VENV_DIR}/bin/python" "${AI_ROOT}/scripts/build_index.py" --force
}

run_service_if_requested() {
  if [[ "${RUN_SERVER}" != "true" ]]; then
    return
  fi

  log "Starting service on ${HOST}:${PORT}"
  "${VENV_DIR}/bin/python" "${AI_ROOT}/scripts/run_server.py" --host "${HOST}" --port "${PORT}" --reload
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --docs-root)
        [[ $# -ge 2 ]] || die "--docs-root requires a path"
        DOCS_ROOT="$2"
        shift 2
        ;;
      --api-key)
        [[ $# -ge 2 ]] || die "--api-key requires a value"
        OPENAI_KEY="$2"
        shift 2
        ;;
      --build-index)
        BUILD_INDEX=true
        shift
        ;;
      --run)
        RUN_SERVER=true
        shift
        ;;
      --host)
        [[ $# -ge 2 ]] || die "--host requires a value"
        HOST="$2"
        shift 2
        ;;
      --port)
        [[ $# -ge 2 ]] || die "--port requires a value"
        PORT="$2"
        shift 2
        ;;
      --no-system-deps)
        NO_SYSTEM_DEPS=true
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown option: $1 (use --help)"
        ;;
    esac
  done
}

main() {
  [[ "$(uname -s)" == "Linux" ]] || die "This installer is for Linux only."
  parse_args "$@"

  cd "${AI_ROOT}"
  install_system_deps
  ensure_python
  create_venv_and_install_python_deps
  init_env_file
  configure_env_values
  build_index_if_requested

  log "Install completed."
  log "Next: source ${VENV_DIR}/bin/activate && python scripts/run_server.py --reload"

  run_service_if_requested
}

main "$@"
