#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
BIN="$BUILD_DIR/bin/db-server"
HOST="${DB_SERVICE_HOST:-0.0.0.0}"
PORT="${DB_SERVICE_PORT:-8082}"

if [[ ! -x "$BIN" ]]; then
    echo "db-server not found, building first..."
    bash "$SCRIPT_DIR/S3-Build.sh"
fi

exec "$BIN" -h "$HOST" -p "$PORT"
