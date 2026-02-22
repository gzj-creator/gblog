#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

UPSTREAM_PORT="${UPSTREAM_PORT:-19000}"
RAW_PORT="${RAW_PORT:-19080}"
HTTP_PORT="${HTTP_PORT:-19081}"
MOCK_CHUNK_DELAY="${MOCK_CHUNK_DELAY:-0.35}"
MOCK_LINGER_SECONDS="${MOCK_LINGER_SECONDS:-0}"
PROBE_TIMEOUT="${PROBE_TIMEOUT:-8}"

find_static_bin() {
  if [[ -n "${STATIC_BIN:-}" && -x "${STATIC_BIN}" ]]; then
    echo "${STATIC_BIN}"
    return 0
  fi

  local candidates=(
    "${REPO_ROOT}/build/static-debug/static-server"
    "${REPO_ROOT}/build/static/static-server"
    "${REPO_ROOT}/service/static/bin/static-server"
  )

  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -x "${candidate}" ]]; then
      echo "${candidate}"
      return 0
    fi
  done

  return 1
}

require_command() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "[demo] missing command: ${cmd}" >&2
    exit 1
  fi
}

wait_http_ready() {
  local url="$1"
  local max_retry=40
  local i
  for ((i = 1; i <= max_retry; i++)); do
    if curl -sS --max-time 0.5 -o /dev/null "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.1
  done
  return 1
}

run_probe() {
  local mode="$1"
  local port="$2"
  local output_file="$3"
  local url="http://127.0.0.1:${port}/ai/api/chat/stream"
  local mode_upper
  mode_upper="$(printf '%s' "${mode}" | tr '[:lower:]' '[:upper:]')"

  echo
  echo "=== ${mode_upper} probe @ ${url} ==="
  if ! python3 "${SCRIPT_DIR}/stream_probe.py" \
    --url "${url}" \
    --timeout "${PROBE_TIMEOUT}" \
    | tee "${output_file}"; then
    echo "[demo] ${mode} probe failed" >&2
    return 1
  fi
}

summarize_probe() {
  local label="$1"
  local file="$2"
  python3 - "$label" "$file" <<'PY'
import re
import sys

label = sys.argv[1]
path = sys.argv[2]

times = []
pattern = re.compile(r"^\s*([0-9]+\.[0-9]+)s\s+data:")

with open(path, "r", encoding="utf-8") as f:
    for line in f:
        m = pattern.match(line)
        if m:
            times.append(float(m.group(1)))

if not times:
    print(f"[demo] {label}: no SSE data lines")
    raise SystemExit(0)

span = times[-1] - times[0]
print(f"[demo] {label}: first={times[0]:.3f}s last={times[-1]:.3f}s span={span:.3f}s events={len(times)}")
PY
}

require_command python3
require_command curl

STATIC_BIN_PATH="$(find_static_bin || true)"
if [[ -z "${STATIC_BIN_PATH}" ]]; then
  cat >&2 <<EOF
[demo] static-server binary not found.
[demo] set STATIC_BIN or build one first, for example:
  cmake -S service/static -B build/static-debug -DCMAKE_BUILD_TYPE=Debug -DCMAKE_PREFIX_PATH=/usr/local
  cmake --build build/static-debug --parallel
EOF
  exit 1
fi

TMP_DIR="$(mktemp -d)"
FRONTEND_DIR="${TMP_DIR}/frontend"
mkdir -p "${FRONTEND_DIR}"
printf '<!doctype html><title>proxy demo</title>\n' > "${FRONTEND_DIR}/index.html"

RAW_CONF="${TMP_DIR}/static-raw.conf"
HTTP_CONF="${TMP_DIR}/static-http.conf"
RAW_LOG="${TMP_DIR}/static-raw.log"
HTTP_LOG="${TMP_DIR}/static-http.log"
MOCK_LOG="${TMP_DIR}/mock.log"
RAW_OUT="${TMP_DIR}/raw.out"
HTTP_OUT="${TMP_DIR}/http.out"

cat > "${RAW_CONF}" <<EOF
server.host=127.0.0.1
server.port=${RAW_PORT}
static.frontend_root=${FRONTEND_DIR}
log.dir=${TMP_DIR}
log.file=$(basename "${RAW_LOG}")
proxy.enabled=true
proxy.route=/ai,127.0.0.1,${UPSTREAM_PORT},raw
EOF

cat > "${HTTP_CONF}" <<EOF
server.host=127.0.0.1
server.port=${HTTP_PORT}
static.frontend_root=${FRONTEND_DIR}
log.dir=${TMP_DIR}
log.file=$(basename "${HTTP_LOG}")
proxy.enabled=true
proxy.route=/ai,127.0.0.1,${UPSTREAM_PORT},http
EOF

MOCK_PID=""
RAW_STATIC_PID=""
HTTP_STATIC_PID=""

cleanup() {
  if [[ -n "${HTTP_STATIC_PID}" ]]; then
    kill "${HTTP_STATIC_PID}" >/dev/null 2>&1 || true
    wait "${HTTP_STATIC_PID}" 2>/dev/null || true
  fi
  if [[ -n "${RAW_STATIC_PID}" ]]; then
    kill "${RAW_STATIC_PID}" >/dev/null 2>&1 || true
    wait "${RAW_STATIC_PID}" 2>/dev/null || true
  fi
  if [[ -n "${MOCK_PID}" ]]; then
    kill "${MOCK_PID}" >/dev/null 2>&1 || true
    wait "${MOCK_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

python3 "${SCRIPT_DIR}/mock_sse_upstream.py" \
  --host 127.0.0.1 \
  --port "${UPSTREAM_PORT}" \
  --chunk-delay "${MOCK_CHUNK_DELAY}" \
  --linger-seconds "${MOCK_LINGER_SECONDS}" \
  > "${MOCK_LOG}" 2>&1 &
MOCK_PID="$!"

if ! wait_http_ready "http://127.0.0.1:${UPSTREAM_PORT}/health"; then
  # /health is expected 404, but connection should become available.
  if ! wait_http_ready "http://127.0.0.1:${UPSTREAM_PORT}/"; then
    echo "[demo] upstream mock did not start" >&2
    exit 1
  fi
fi

STATIC_CONFIG_PATH="${RAW_CONF}" "${STATIC_BIN_PATH}" > /dev/null 2>&1 &
RAW_STATIC_PID="$!"
if ! wait_http_ready "http://127.0.0.1:${RAW_PORT}/"; then
  echo "[demo] raw static instance did not start" >&2
  exit 1
fi

run_probe "raw" "${RAW_PORT}" "${RAW_OUT}"

kill "${RAW_STATIC_PID}" >/dev/null 2>&1 || true
wait "${RAW_STATIC_PID}" 2>/dev/null || true
RAW_STATIC_PID=""

STATIC_CONFIG_PATH="${HTTP_CONF}" "${STATIC_BIN_PATH}" > /dev/null 2>&1 &
HTTP_STATIC_PID="$!"
if ! wait_http_ready "http://127.0.0.1:${HTTP_PORT}/"; then
  echo "[demo] http static instance did not start" >&2
  exit 1
fi

run_probe "http" "${HTTP_PORT}" "${HTTP_OUT}"

echo
echo "=== summary ==="
summarize_probe "raw" "${RAW_OUT}"
summarize_probe "http" "${HTTP_OUT}"
echo "[demo] artifacts: ${TMP_DIR}"
echo "[demo] logs: ${MOCK_LOG}, ${RAW_LOG}, ${HTTP_LOG}"
