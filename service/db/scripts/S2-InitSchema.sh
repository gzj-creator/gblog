#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SCHEMA_FILE="$PROJECT_DIR/docs/schema.sql"

MYSQL_HOST="${DB_MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${DB_MYSQL_PORT:-3306}"
MYSQL_USER="${DB_MYSQL_USER:-root}"
MYSQL_PASSWORD="${DB_MYSQL_PASSWORD:-password}"
MYSQL_DATABASE="${DB_MYSQL_DATABASE:-gblob}"

if command -v mysql >/dev/null 2>&1; then
    MYSQL_BIN="mysql"
elif [[ -x "/opt/homebrew/opt/mysql-client/bin/mysql" ]]; then
    MYSQL_BIN="/opt/homebrew/opt/mysql-client/bin/mysql"
else
    echo "mysql client not found. Install mysql-client or put mysql in PATH." >&2
    exit 1
fi

if [[ ! -f "$SCHEMA_FILE" ]]; then
    echo "schema file not found: $SCHEMA_FILE" >&2
    exit 1
fi

tmp_schema="$(mktemp)"
cleanup() {
    rm -f "$tmp_schema"
}
trap cleanup EXIT

# Allow applying the shared schema into any target database by env var.
awk '
    BEGIN { IGNORECASE = 1 }
    /^[[:space:]]*CREATE[[:space:]]+DATABASE[[:space:]]+IF[[:space:]]+NOT[[:space:]]+EXISTS[[:space:]]+/ { next }
    /^[[:space:]]*USE[[:space:]]+/ { next }
    { print }
' "$SCHEMA_FILE" > "$tmp_schema"

echo "Applying schema to database '$MYSQL_DATABASE': $SCHEMA_FILE"
"$MYSQL_BIN" -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -D "$MYSQL_DATABASE" < "$tmp_schema"
echo "Schema applied successfully."
