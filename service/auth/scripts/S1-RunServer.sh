#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
BIN="$BUILD_DIR/bin/auth-server"
HOST="${AUTH_SERVICE_HOST:-0.0.0.0}"
PORT="${AUTH_SERVICE_PORT:-8081}"

if [[ ! -x "$BIN" ]]; then
    echo "auth-server not found, building first..."
    bash "$SCRIPT_DIR/S3-Build.sh"
fi

exec "$BIN" -h "$HOST" -p "$PORT"
