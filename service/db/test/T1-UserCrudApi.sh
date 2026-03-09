#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8082}"
seed="$(date +%s)_$$_$RANDOM"
username="u_${seed}"
email="${username}@test.local"
display_name="User ${seed}"
updated_email="u_${seed}_updated@test.local"

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

  local body
  body="$(cat "$tmp")"
  rm -f "$tmp"

  if [[ "$code" != "$expected_code" ]]; then
    echo "request failed: $method $path" >&2
    echo "expected HTTP $expected_code, got $code" >&2
    echo "response: $body" >&2
    exit 1
  fi

  RESPONSE_BODY="$body"
}

extract_user_id() {
  local resp="$1"
  local user_id
  user_id=$(printf '%s' "$resp" | grep -oE '"id":[0-9]+' | head -1 | cut -d: -f2 || true)
  if [[ -z "$user_id" ]]; then
    echo "failed to extract user id from response: $resp" >&2
    exit 1
  fi
  printf '%s' "$user_id"
}

request_json "POST" "/api/v1/db/users/create" "200" "{\"username\":\"${username}\",\"email\":\"${email}\",\"display_name\":\"${display_name}\",\"password_salt\":\"salt_1\",\"password_hash\":\"hash_1\"}"
create_resp="$RESPONSE_BODY"
assert_contains "$create_resp" '"success":true'
assert_contains "$create_resp" "\"username\":\"${username}\""
user_id="$(extract_user_id "$create_resp")"

request_json "GET" "/api/v1/db/users/get-by-username/${username}" "200"
get_by_username_resp="$RESPONSE_BODY"
assert_contains "$get_by_username_resp" '"success":true'
assert_contains "$get_by_username_resp" "\"id\":${user_id}"
assert_contains "$get_by_username_resp" "\"email\":\"${email}\""

request_json "GET" "/api/v1/db/users/get/${user_id}" "200"
get_by_id_resp="$RESPONSE_BODY"
assert_contains "$get_by_id_resp" '"success":true'
assert_contains "$get_by_id_resp" "\"username\":\"${username}\""

request_json "PATCH" "/api/v1/db/users/update/${user_id}" "200" "{\"email\":\"${updated_email}\",\"display_name\":\"Updated ${seed}\",\"bio\":\"bio text\",\"website\":\"https://example.com\",\"github\":\"gblob-test\"}"
update_user_resp="$RESPONSE_BODY"
assert_contains "$update_user_resp" '"success":true'
assert_contains "$update_user_resp" "\"email\":\"${updated_email}\""
assert_contains "$update_user_resp" "\"bio\":\"bio text\""

request_json "PUT" "/api/v1/db/users/update-password/${user_id}" "200" '{"password_salt":"salt_2","password_hash":"hash_2"}'
update_password_resp="$RESPONSE_BODY"
assert_contains "$update_password_resp" '"success":true'
assert_contains "$update_password_resp" "\"password_salt\":\"salt_2\""
assert_contains "$update_password_resp" "\"password_hash\":\"hash_2\""

request_json "PUT" "/api/v1/db/users/update-notifications/${user_id}" "200" '{"email_notifications":false,"new_post_notifications":true,"comment_reply_notifications":false,"release_notifications":true}'
update_notifications_resp="$RESPONSE_BODY"
assert_contains "$update_notifications_resp" '"success":true'
assert_contains "$update_notifications_resp" "\"email_notifications\":false"
assert_contains "$update_notifications_resp" "\"new_post_notifications\":true"
assert_contains "$update_notifications_resp" "\"comment_reply_notifications\":false"
assert_contains "$update_notifications_resp" "\"release_notifications\":true"

request_json "DELETE" "/api/v1/db/users/delete/${user_id}" "200"
delete_resp="$RESPONSE_BODY"
assert_contains "$delete_resp" '"success":true'

request_json "GET" "/api/v1/db/users/get/${user_id}" "404"
deleted_body="$RESPONSE_BODY"
assert_contains "$deleted_body" '"success":false'
assert_contains "$deleted_body" '"user not found"'

echo "db user CRUD API test passed"
