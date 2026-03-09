#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8082}"
seed="$(date +%s)_$$_$RANDOM"
username="pw_reg_${seed}"
email="${username}@test.local"

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
    code="$(curl -sS -o "$tmp" -w "%{http_code}" -X "$method" "${BASE_URL}${path}" -H 'Content-Type: application/json' -d "$payload" || true)"
  else
    code="$(curl -sS -o "$tmp" -w "%{http_code}" -X "$method" "${BASE_URL}${path}" || true)"
  fi

  RESPONSE_BODY="$(cat "$tmp")"
  rm -f "$tmp"

  if [[ "$code" != "$expected_code" ]]; then
    echo "request failed: $method $path expected=$expected_code got=$code" >&2
    echo "response: $RESPONSE_BODY" >&2
    exit 1
  fi
}

extract_user_id() {
  local resp="$1"
  local user_id
  user_id="$(printf '%s' "$resp" | grep -oE '"id":[0-9]+' | head -1 | cut -d: -f2 || true)"
  if [[ -z "$user_id" ]]; then
    echo "failed to extract user id from response: $resp" >&2
    exit 1
  fi
  printf '%s' "$user_id"
}

request_json "POST" "/api/v1/db/users/create" "200" "{\"username\":\"${username}\",\"email\":\"${email}\",\"display_name\":\"${username}\",\"password_salt\":\"salt_1\",\"password_hash\":\"hash_1\"}"
assert_contains "$RESPONSE_BODY" '"success":true'
user_id="$(extract_user_id "$RESPONSE_BODY")"

request_json "PUT" "/api/v1/db/users/update-password/${user_id}" "200" '{"password_salt":"salt_2","password_hash":"hash_2"}'
assert_contains "$RESPONSE_BODY" '"success":true'
assert_contains "$RESPONSE_BODY" '"password_salt":"salt_2"'
assert_contains "$RESPONSE_BODY" '"password_hash":"hash_2"'

echo "db update-password regression test passed"
