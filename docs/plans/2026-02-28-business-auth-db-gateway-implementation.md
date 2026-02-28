# Business/Auth/DB/Gateway Split Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split monolithic backend into independent `business -> auth -> db` services, migrate public APIs to `/api/v1/*`, and rename `static/backend` to `gateway/business` in one coordinated delivery.

**Architecture:** `gateway` is the only public edge proxy and static host. `business` serves content APIs and forwards auth APIs to `auth`. `auth` owns password/token logic and calls `db` over HTTP. `db` encapsulates persistence through a MySQL adapter (`galay-mysql`) with replaceable provider interface.

**Tech Stack:** C++23, galay-http, galay-kernel, galay-mysql, galay-utils (Base64/Salt), MySQL 8.0, Docker Compose.

---

### Task 1: Establish Failing API-v1 Contract Tests (TDD red first)

**Files:**
- Create: `tests/e2e/api_v1_contract.sh`
- Create: `tests/e2e/lib/http_assert.sh`
- Modify: `README.md`

**Step 1: Write the failing test**

```bash
#!/usr/bin/env bash
# tests/e2e/api_v1_contract.sh
set -euo pipefail
source "$(dirname "$0")/lib/http_assert.sh"

assert_http_code "http://127.0.0.1:80/api/v1/health" "200"
assert_http_code "http://127.0.0.1:80/api/v1/auth/login" "405"
```

**Step 2: Run test to verify it fails**

Run: `bash tests/e2e/api_v1_contract.sh`
Expected: FAIL because `/api/v1/*` is not wired yet.

**Step 3: Add minimal test helpers only (not implementation)**

```bash
# tests/e2e/lib/http_assert.sh
assert_http_code() {
  local url="$1"; local expected="$2"
  local got
  got=$(curl -s -o /tmp/resp.$$ -w "%{http_code}" "$url" || true)
  [[ "$got" == "$expected" ]] || {
    echo "expected $expected got $got for $url" >&2
    cat /tmp/resp.$$ >&2 || true
    exit 1
  }
}
```

**Step 4: Re-run test and keep red**

Run: `bash tests/e2e/api_v1_contract.sh`
Expected: Still FAIL (no production code touched yet).

**Step 5: Commit**

```bash
git add tests/e2e/api_v1_contract.sh tests/e2e/lib/http_assert.sh README.md
git commit -m "test(e2e): add failing /api/v1 contract checks"
```

### Task 2: Create DB Service Skeleton and Health Endpoint

**Files:**
- Create: `service/db/CMakeLists.txt`
- Create: `service/db/DbServer.cc`
- Create: `service/db/scripts/S1-RunServer.sh`
- Create: `service/db/scripts/S3-Build.sh`
- Create: `service/db/README.md`
- Create: `service/db/docs/schema.sql`

**Step 1: Write the failing test**

```bash
# tests/e2e/db_service_health.sh
#!/usr/bin/env bash
set -euo pipefail
curl -fsS http://127.0.0.1:8082/health >/dev/null
```

**Step 2: Run test to verify it fails**

Run: `bash tests/e2e/db_service_health.sh`
Expected: FAIL with connection refused.

**Step 3: Write minimal implementation**

```cpp
// service/db/DbServer.cc (minimal)
router.addHandler<HttpMethod::GET>("/health", healthHandler);
```

**Step 4: Run test to verify it passes**

Run:
- `bash service/db/scripts/S3-Build.sh`
- `bash service/db/scripts/S1-RunServer.sh`
- `bash tests/e2e/db_service_health.sh`
Expected: PASS.

**Step 5: Commit**

```bash
git add service/db tests/e2e/db_service_health.sh
git commit -m "feat(db): scaffold db service with health endpoint"
```

### Task 3: Implement MySQL Adapter and User Persistence Endpoints in DB Service

**Files:**
- Create: `service/db/src/DbProvider.h`
- Create: `service/db/src/MySqlDbProvider.h`
- Create: `service/db/src/MySqlDbProvider.cc`
- Modify: `service/db/DbServer.cc`
- Modify: `service/db/docs/schema.sql`
- Create: `service/db/test/T1-UserCrudApi.sh`
- Modify: `service/db/CMakeLists.txt`

**Step 1: Write the failing test**

```bash
# service/db/test/T1-UserCrudApi.sh
# should fail before endpoints exist
curl -fsS -X POST http://127.0.0.1:8082/api/v1/db/users/create \
  -H 'Content-Type: application/json' \
  -d '{"username":"u1","email":"u1@test.com","display_name":"u1","password_salt":"s","password_hash":"h"}'
```

**Step 2: Run test to verify it fails**

Run: `bash service/db/test/T1-UserCrudApi.sh`
Expected: FAIL with 404/connection error.

**Step 3: Write minimal implementation**

```cpp
// add routes
POST   /api/v1/db/users/create
GET    /api/v1/db/users/get-by-username/:username
GET    /api/v1/db/users/get/:id
PATCH  /api/v1/db/users/update/:id
PUT    /api/v1/db/users/update-password/:id
PUT    /api/v1/db/users/update-notifications/:id
DELETE /api/v1/db/users/delete/:id
```

Use `galay-mysql` with prepared statements; define provider interface to isolate DB backend differences.

**Step 4: Run test to verify it passes**

Run:
- `bash service/db/scripts/S3-Build.sh`
- `MYSQL_* env + schema init`
- `bash service/db/test/T1-UserCrudApi.sh`
Expected: PASS CRUD flow.

**Step 5: Commit**

```bash
git add service/db/src service/db/DbServer.cc service/db/docs/schema.sql service/db/test/T1-UserCrudApi.sh service/db/CMakeLists.txt
git commit -m "feat(db): add mysql adapter and user persistence apis"
```

### Task 4: Create Auth Service Skeleton and Upstream DB Client

**Files:**
- Create: `service/auth/CMakeLists.txt`
- Create: `service/auth/AuthServer.cc`
- Create: `service/auth/src/DbHttpClient.h`
- Create: `service/auth/src/DbHttpClient.cc`
- Create: `service/auth/scripts/S1-RunServer.sh`
- Create: `service/auth/scripts/S3-Build.sh`
- Create: `service/auth/README.md`

**Step 1: Write the failing test**

```bash
# tests/e2e/auth_service_health.sh
curl -fsS http://127.0.0.1:8081/health >/dev/null
```

**Step 2: Run test to verify it fails**

Run: `bash tests/e2e/auth_service_health.sh`
Expected: FAIL.

**Step 3: Write minimal implementation**

```cpp
router.addHandler<HttpMethod::GET>("/health", healthHandler);
```

**Step 4: Run test to verify it passes**

Run:
- `bash service/auth/scripts/S3-Build.sh`
- `bash service/auth/scripts/S1-RunServer.sh`
- `bash tests/e2e/auth_service_health.sh`
Expected: PASS.

**Step 5: Commit**

```bash
git add service/auth tests/e2e/auth_service_health.sh
git commit -m "feat(auth): scaffold auth service and db upstream client"
```

### Task 5: Implement Auth APIs (/api/v1/auth/*), Password Salt+Hash, In-Memory Token Lifecycle

**Files:**
- Modify: `service/auth/AuthServer.cc`
- Create: `service/auth/src/PasswordCodec.h`
- Create: `service/auth/src/PasswordCodec.cc`
- Create: `service/auth/src/TokenStore.h`
- Create: `service/auth/src/TokenStore.cc`
- Create: `service/auth/test/T1-AuthApi.sh`
- Modify: `service/auth/CMakeLists.txt`

**Step 1: Write the failing test**

```bash
# service/auth/test/T1-AuthApi.sh
# expects /api/v1/auth/login to exist and return success json
curl -fsS -X POST http://127.0.0.1:8081/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo","password_b64":"ZGVtbzEyMw=="}'
```

**Step 2: Run test to verify it fails**

Run: `bash service/auth/test/T1-AuthApi.sh`
Expected: FAIL (404 or validation fail before logic exists).

**Step 3: Write minimal implementation**

```cpp
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me
PUT  /api/v1/auth/profile
PUT  /api/v1/auth/password
PUT  /api/v1/auth/notifications
DELETE /api/v1/auth/account
```

- Decode `password_b64` by galay-utils Base64.
- Generate salt by galay-utils `Salt::generate`.
- Hash password by galay-utils `Salt::hashPassword`.
- Refresh token stored in-memory only.

**Step 4: Run test to verify it passes**

Run: `bash service/auth/test/T1-AuthApi.sh`
Expected: PASS and verify DB table has `password_salt/password_hash` non-empty.

**Step 5: Commit**

```bash
git add service/auth/AuthServer.cc service/auth/src service/auth/test/T1-AuthApi.sh service/auth/CMakeLists.txt
git commit -m "feat(auth): implement /api/v1/auth apis with salt-hash password flow"
```

### Task 6: Refactor Business Service to /api/v1 and Forward Auth Requests to Auth Service

**Files:**
- Rename: `service/backend` -> `service/business` (later task will finalize path references)
- Modify: `service/backend/BlogServer.cc`
- Create: `service/backend/src/AuthHttpClient.h`
- Create: `service/backend/src/AuthHttpClient.cc`
- Modify: `service/backend/CMakeLists.txt`
- Create: `service/backend/test/T2-BusinessV1Api.sh`

**Step 1: Write the failing test**

```bash
# service/backend/test/T2-BusinessV1Api.sh
curl -fsS http://127.0.0.1:8080/api/v1/health >/dev/null
curl -fsS -X POST http://127.0.0.1:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' -d '{"username":"u1","password_b64":"dTEyMw=="}' >/dev/null
```

**Step 2: Run test to verify it fails**

Run: `bash service/backend/test/T2-BusinessV1Api.sh`
Expected: FAIL for missing `/api/v1` and auth forwarding.

**Step 3: Write minimal implementation**

- Content APIs remap to `/api/v1/*`.
- `business` forwards `/api/v1/auth/*` to `AUTH_UPSTREAM`.
- Preserve JSON response envelope conventions.

**Step 4: Run test to verify it passes**

Run: `bash service/backend/test/T2-BusinessV1Api.sh`
Expected: PASS.

**Step 5: Commit**

```bash
git add service/backend/BlogServer.cc service/backend/src service/backend/CMakeLists.txt service/backend/test/T2-BusinessV1Api.sh
git commit -m "feat(business): add /api/v1 routes and auth upstream forwarding"
```

### Task 7: Rename Directories and Service Identities (backend->business, static->gateway)

**Files:**
- Move: `service/backend` -> `service/business`
- Move: `service/static` -> `service/gateway`
- Modify: `docker-compose.yml`
- Modify: `README.md`
- Modify: `service/business/README.md`
- Modify: `service/gateway/README.md`
- Modify: `service/gateway/config/static-server.conf`
- Modify: `service/gateway/.env.example`

**Step 1: Write the failing test**

```bash
# tests/e2e/compose_names.sh
grep -q "business:" docker-compose.yml
grep -q "gateway:" docker-compose.yml
```

**Step 2: Run test to verify it fails**

Run: `bash tests/e2e/compose_names.sh`
Expected: FAIL before rename.

**Step 3: Write minimal implementation**

```bash
git mv service/backend service/business
git mv service/static service/gateway
```

Then update compose service names, volume paths, container names, startup commands, and gateway proxy routes:
- `/api/v1 -> business:8080`
- `/ai -> ai:8000`

**Step 4: Run test to verify it passes**

Run: `bash tests/e2e/compose_names.sh`
Expected: PASS.

**Step 5: Commit**

```bash
git add service/business service/gateway docker-compose.yml README.md tests/e2e/compose_names.sh
git commit -m "refactor: rename backend/static to business/gateway and update compose"
```

### Task 8: Update Frontend API Bases to /api/v1 and /api/v1/auth

**Files:**
- Modify: `frontend/js/auth.js`
- Modify: `frontend/js/home.js`
- Modify: `frontend/js/blog.js`
- Modify: `frontend/js/article.js`
- Modify: `frontend/js/docs.js`
- Modify: `frontend/js/search.js`
- Modify: `frontend/js/projects.js`
- Modify: `frontend/js/profile.js`

**Step 1: Write the failing test**

```bash
# tests/e2e/frontend_api_base.sh
rg -n "const API_BASE = '/api'|const AUTH_API = '/api/auth'" frontend/js && exit 1 || true
```

**Step 2: Run test to verify it fails**

Run: `bash tests/e2e/frontend_api_base.sh`
Expected: FAIL because old constants exist.

**Step 3: Write minimal implementation**

- Replace `'/api'` -> `'/api/v1'` for content endpoints.
- Replace `'/api/auth'` -> `'/api/v1/auth'` for auth endpoints.

**Step 4: Run test to verify it passes**

Run: `bash tests/e2e/frontend_api_base.sh`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/js/auth.js frontend/js/home.js frontend/js/blog.js frontend/js/article.js frontend/js/docs.js frontend/js/search.js frontend/js/projects.js frontend/js/profile.js tests/e2e/frontend_api_base.sh
git commit -m "refactor(frontend): migrate api base paths to /api/v1"
```

### Task 9: End-to-End Verification and Docs Sync

**Files:**
- Modify: `README.md`
- Modify: `service/business/README.md`
- Modify: `service/gateway/README.md`
- Modify: `service/auth/README.md`
- Modify: `service/db/README.md`
- Create: `docs/plans/2026-02-28-api-v1-migration-notes.md`

**Step 1: Write the failing verification checklist**

```bash
# tests/e2e/full_stack_smoke.sh
curl -fsS http://127.0.0.1/api/v1/health >/dev/null
curl -fsS -X POST http://127.0.0.1/api/v1/auth/register -H 'Content-Type: application/json' -d '{"username":"u","email":"u@test.com","password_b64":"dTEyMw=="}' >/dev/null
curl -fsS http://127.0.0.1/api/v1/posts >/dev/null
```

**Step 2: Run checklist before wiring all services**

Run: `bash tests/e2e/full_stack_smoke.sh`
Expected: FAIL.

**Step 3: Complete docs and compose startup instructions**

- Document all service ports and startup order.
- Document token non-persistence behavior.
- Document DB schema bootstrap command.

**Step 4: Run final verification to green**

Run:
- `docker compose up -d --build`
- `bash tests/e2e/full_stack_smoke.sh`
Expected: PASS.

**Step 5: Commit**

```bash
git add README.md service/business/README.md service/gateway/README.md service/auth/README.md service/db/README.md docs/plans/2026-02-28-api-v1-migration-notes.md tests/e2e/full_stack_smoke.sh
git commit -m "docs: finalize api v1 split architecture and migration notes"
```

### Task 10: Clean Validation Gate (required before branch completion)

**Files:**
- No source changes expected unless fixes are required

**Step 1: Run build checks**

Run:
- `bash service/db/scripts/S3-Build.sh`
- `bash service/auth/scripts/S3-Build.sh`
- `bash service/business/scripts/S3-Build.sh`
- `bash service/gateway/scripts/builder.sh`
Expected: PASS all builds.

**Step 2: Run service-level tests**

Run:
- `bash service/db/test/T1-UserCrudApi.sh`
- `bash service/auth/test/T1-AuthApi.sh`
- `bash service/business/test/T2-BusinessV1Api.sh`
Expected: PASS.

**Step 3: Run e2e tests**

Run:
- `bash tests/e2e/api_v1_contract.sh`
- `bash tests/e2e/full_stack_smoke.sh`
Expected: PASS.

**Step 4: If any failure, fix and re-run from failing layer upward**

Expected: All green with evidence logs.

**Step 5: Commit verification artifacts if needed**

```bash
git add <only-if-new-verification-docs>
git commit -m "chore: record final verification evidence"
```

---

## Notes for Execution

- Follow `@test-driven-development` strictly for each behavior change.
- Use `@verification-before-completion` before claiming completion.
- Keep commits small and reversible (one task per commit).
- Do not mix directory rename with protocol/business logic in the same commit.

