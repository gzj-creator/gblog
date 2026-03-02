#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8082}"
seed="$(date +%s)"
project="custom"
relative_path="docs/doc-${seed}.md"

assert_contains() {
  local haystack="$1"
  local needle="$2"
  if [[ "$haystack" != *"$needle"* ]]; then
    echo "assertion failed: expected response to contain: $needle" >&2
    echo "response: $haystack" >&2
    exit 1
  fi
}

request_json() {
  local method="$1"
  local path="$2"
  local expected_code="$3"
  local payload="${4:-}"
  local tmp
  tmp="$(mktemp)"

  local code
  if [[ -n "$payload" ]]; then
    code="$(/usr/bin/curl -sS -o "$tmp" -w "%{http_code}" -X "$method" "${BASE_URL}${path}" -H 'Content-Type: application/json' -d "$payload" || true)"
  else
    code="$(/usr/bin/curl -sS -o "$tmp" -w "%{http_code}" -X "$method" "${BASE_URL}${path}" || true)"
  fi

  RESPONSE_BODY="$(cat "$tmp")"
  rm -f "$tmp"

  if [[ "$code" != "$expected_code" ]]; then
    echo "request failed: $method $path expected=$expected_code got=$code" >&2
    echo "response: $RESPONSE_BODY" >&2
    exit 1
  fi
}

request_json "POST" "/api/v1/db/documents/upsert" "200" "{\"project\":\"${project}\",\"relative_path\":\"${relative_path}\",\"sha256\":\"sha-${seed}\",\"size_bytes\":123}"
assert_contains "$RESPONSE_BODY" '"success":true'
assert_contains "$RESPONSE_BODY" "\"project\":\"${project}\""

request_json "POST" "/api/v1/db/documents/get" "200" "{\"project\":\"${project}\",\"relative_path\":\"${relative_path}\"}"
assert_contains "$RESPONSE_BODY" '"success":true'
assert_contains "$RESPONSE_BODY" "\"relative_path\":\"${relative_path}\""

request_json "POST" "/api/v1/db/index-jobs/create" "200" "{\"job_type\":\"reindex\",\"project\":\"${project}\",\"relative_path\":\"${relative_path}\",\"trigger_source\":\"test\",\"payload_json\":\"{}\"}"
assert_contains "$RESPONSE_BODY" '"success":true'
job_id="$(printf '%s' "$RESPONSE_BODY" | /usr/bin/sed -n 's/.*"id":\([0-9][0-9]*\).*/\1/p' | /usr/bin/head -1)"
if [[ -z "$job_id" ]]; then
  echo "failed to parse job id from response: $RESPONSE_BODY" >&2
  exit 1
fi

request_json "POST" "/api/v1/db/index-jobs/fetch-next" "200"
assert_contains "$RESPONSE_BODY" '"success":true'
assert_contains "$RESPONSE_BODY" '"status":"running"'

request_json "POST" "/api/v1/db/index-jobs/finish-success" "200" "{\"job_id\":${job_id}}"
assert_contains "$RESPONSE_BODY" '"success":true'
assert_contains "$RESPONSE_BODY" '"status":"success"'
assert_contains "$RESPONSE_BODY" '"index_state":{'

request_json "GET" "/api/v1/db/index/state" "200"
assert_contains "$RESPONSE_BODY" '"success":true'
assert_contains "$RESPONSE_BODY" '"current_version":'

request_json "POST" "/api/v1/db/documents/delete" "200" "{\"project\":\"${project}\",\"relative_path\":\"${relative_path}\"}"
assert_contains "$RESPONSE_BODY" '"success":true'
assert_contains "$RESPONSE_BODY" '"is_deleted":true'

echo "db document/index job api test passed"
