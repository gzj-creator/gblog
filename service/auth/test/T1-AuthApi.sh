#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8081}"
DB_BASE_URL="${DB_BASE_URL:-http://127.0.0.1:8082}"
seed="$(date +%s)_$$_$RANDOM"
username="auth_u_${seed}"
email="${username}@test.local"
password_plain="Pass_${seed}_A"
new_password_plain="Pass_${seed}_B"
password_b64="$(printf '%s' "$password_plain" | base64 | tr -d '\n')"
new_password_b64="$(printf '%s' "$new_password_plain" | base64 | tr -d '\n')"

assert_contains() {
  local haystack="$1"
  local needle="$2"
  if [[ "$haystack" != *"$needle"* ]]; then
    echo "assertion failed: expected to contain: $needle" >&2
    echo "response: $haystack" >&2
    exit 1
  fi
}

extract_json_string() {
  local body="$1"
  local key="$2"
  printf '%s' "$body" | sed -n "s/.*\"${key}\":\"\\([^\"]*\\)\".*/\\1/p" | head -1
}

request_json() {
  local method="$1"
  local path="$2"
  local expected_code="$3"
  local payload="${4:-}"
  local bearer="${5:-}"
  local tmp
  tmp="$(mktemp)"

  local curl_args=(-sS -o "$tmp" -w "%{http_code}" -X "$method" "${BASE_URL}${path}")
  if [[ -n "$payload" ]]; then
    curl_args+=(-H 'Content-Type: application/json' -d "$payload")
  fi
  if [[ -n "$bearer" ]]; then
    curl_args+=(-H "Authorization: Bearer ${bearer}")
  fi

  local code
  code="$(curl "${curl_args[@]}" || true)"
  RESPONSE_BODY="$(cat "$tmp")"
  rm -f "$tmp"

  if [[ "$code" != "$expected_code" ]]; then
    echo "request failed: $method $path expected=$expected_code got=$code" >&2
    echo "response: $RESPONSE_BODY" >&2
    exit 1
  fi
}

request_json "POST" "/api/v1/auth/register" "200" \
  "{\"username\":\"${username}\",\"email\":\"${email}\",\"display_name\":\"${username}\",\"password_b64\":\"${password_b64}\"}"
register_resp="$RESPONSE_BODY"
assert_contains "$register_resp" '"success":true'
assert_contains "$register_resp" "\"username\":\"${username}\""
access_token="$(extract_json_string "$register_resp" "access_token")"
refresh_token="$(extract_json_string "$register_resp" "refresh_token")"
if [[ -z "$access_token" || -z "$refresh_token" ]]; then
  echo "missing tokens in register response: $register_resp" >&2
  exit 1
fi

request_json "GET" "/api/v1/auth/me" "200" "" "$access_token"
assert_contains "$RESPONSE_BODY" "\"username\":\"${username}\""

request_json "PUT" "/api/v1/auth/profile" "200" \
  "{\"display_name\":\"${username}-updated\",\"bio\":\"bio-${seed}\",\"website\":\"https://example.com\",\"github\":\"gblob-user\"}" \
  "$access_token"
assert_contains "$RESPONSE_BODY" '"success":true'
assert_contains "$RESPONSE_BODY" "\"display_name\":\"${username}-updated\""

request_json "PUT" "/api/v1/auth/notifications" "200" \
  '{"email_notifications":false,"new_post_notifications":true,"comment_reply_notifications":false,"release_notifications":true}' \
  "$access_token"
assert_contains "$RESPONSE_BODY" '"success":true'
assert_contains "$RESPONSE_BODY" '"email_notifications":false'

request_json "PUT" "/api/v1/auth/password" "200" \
  "{\"old_password_b64\":\"${password_b64}\",\"new_password_b64\":\"${new_password_b64}\"}" \
  "$access_token"
assert_contains "$RESPONSE_BODY" '"success":true'

request_json "POST" "/api/v1/auth/refresh" "200" "{\"refresh_token\":\"${refresh_token}\"}"
assert_contains "$RESPONSE_BODY" '"success":true'
refreshed_access_token="$(extract_json_string "$RESPONSE_BODY" "access_token")"
if [[ -z "$refreshed_access_token" ]]; then
  echo "missing refreshed access token: $RESPONSE_BODY" >&2
  exit 1
fi

request_json "POST" "/api/v1/auth/logout" "200" "" "$refreshed_access_token"
assert_contains "$RESPONSE_BODY" '"success":true'

request_json "GET" "/api/v1/auth/me" "401" "" "$refreshed_access_token"
assert_contains "$RESPONSE_BODY" '"success":false'

request_json "POST" "/api/v1/auth/login" "401" \
  "{\"username\":\"${username}\",\"password_b64\":\"${password_b64}\"}"
assert_contains "$RESPONSE_BODY" '"success":false'

request_json "POST" "/api/v1/auth/login" "200" \
  "{\"username\":\"${username}\",\"password_b64\":\"${new_password_b64}\"}"
assert_contains "$RESPONSE_BODY" '"success":true'
access_token2="$(extract_json_string "$RESPONSE_BODY" "access_token")"
if [[ -z "$access_token2" ]]; then
  echo "missing access token in second login: $RESPONSE_BODY" >&2
  exit 1
fi

db_get_resp="$(curl -sS "${DB_BASE_URL}/api/v1/db/users/get-by-username/${username}" || true)"
assert_contains "$db_get_resp" '"success":true'
assert_contains "$db_get_resp" '"password_salt":"'
assert_contains "$db_get_resp" '"password_hash":"'

request_json "DELETE" "/api/v1/auth/account" "200" "" "$access_token2"
assert_contains "$RESPONSE_BODY" '"success":true'

request_json "POST" "/api/v1/auth/login" "401" \
  "{\"username\":\"${username}\",\"password_b64\":\"${new_password_b64}\"}"
assert_contains "$RESPONSE_BODY" '"success":false'

echo "auth api test passed"
