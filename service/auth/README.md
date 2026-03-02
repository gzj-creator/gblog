# Auth Service

Authentication service for user identity, token lifecycle, and profile operations.

## Quick Start

```bash
bash scripts/S3-Build.sh
bash scripts/S1-RunServer.sh
```

## Health Check

```bash
curl http://127.0.0.1:8081/health
```

## Upstream DB Service

`auth-server` reads internal db service target from:

- `DB_SERVICE_HOST` (default `127.0.0.1`)
- `DB_SERVICE_PORT` (default `8082`)

## API

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `PUT /api/v1/auth/profile`
- `PUT /api/v1/auth/password`
- `PUT /api/v1/auth/notifications`
- `DELETE /api/v1/auth/account`

Password fields from frontend should be base64 strings:

- `password_b64` (register/login)
- `old_password_b64` / `new_password_b64` (password update)

Backend decodes base64, then stores `password_salt + password_hash` in db.

## Auth API Test

```bash
bash test/T1-AuthApi.sh
```
