#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
BIN="$BUILD_DIR/bin/db-server"
TEST_SCRIPT="$PROJECT_DIR/test/T1-UserCrudApi.sh"

TEST_HOST="${DB_TEST_HOST:-127.0.0.1}"
TEST_PORT="${DB_TEST_PORT:-18082}"
BASE_URL="http://${TEST_HOST}:${TEST_PORT}"

if [[ ! -x "$BIN" ]]; then
    echo "db-server not found, building first..."
    bash "$SCRIPT_DIR/S3-Build.sh"
fi

if [[ ! -x "$TEST_SCRIPT" ]]; then
    echo "test script not executable: $TEST_SCRIPT" >&2
    exit 1
fi

"$BIN" -h "$TEST_HOST" -p "$TEST_PORT" &
SERVER_PID=$!
cleanup() {
    kill "$SERVER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in $(seq 1 50); do
    if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
        break
    fi
    sleep 0.2
done

if ! curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
    echo "db-server failed to start at $BASE_URL" >&2
    exit 1
fi

echo "Running CRUD API test at $BASE_URL"
BASE_URL="$BASE_URL" bash "$TEST_SCRIPT"
