# DB Service API

Base URL: `http://<db-host>:8082`

All responses follow:

```json
{"success": true, "data": {}}
```

or

```json
{"success": false, "error": {"message": "..."}}
```

## Health

### GET `/health`

Returns service status.

## User APIs

### POST `/api/v1/db/users/create`

Create user.

Request JSON:

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "display_name": "Alice",
  "bio": "",
  "website": "",
  "github": "",
  "password_salt": "salt",
  "password_hash": "hash"
}
```

### GET `/api/v1/db/users/get-by-username/{username}`

### GET `/api/v1/db/users/get/{id}`

### PATCH `/api/v1/db/users/update/{id}`

Request JSON (partial):

```json
{
  "email": "new@example.com",
  "display_name": "New Name",
  "bio": "...",
  "website": "https://...",
  "github": "alice"
}
```

### PUT `/api/v1/db/users/update-password/{id}`

```json
{
  "password_salt": "salt2",
  "password_hash": "hash2"
}
```

### PUT `/api/v1/db/users/update-notifications/{id}`

```json
{
  "email_notifications": true,
  "new_post_notifications": true,
  "comment_reply_notifications": false,
  "release_notifications": true
}
```

### DELETE `/api/v1/db/users/delete/{id}`

## Document Metadata APIs

### POST `/api/v1/db/documents/upsert`

Create or update a managed document metadata record.

```json
{
  "project": "custom",
  "relative_path": "notes/intro.md",
  "sha256": "abc123",
  "size_bytes": 1024,
  "doc_version": 2,
  "is_deleted": false
}
```

Notes:
- `doc_version` optional. If omitted, server auto-increments version.
- `is_deleted` optional. Default `false`.

### POST `/api/v1/db/documents/get`

```json
{
  "project": "custom",
  "relative_path": "notes/intro.md"
}
```

Compatibility: `GET /api/v1/db/documents/get?project=...&relative_path=...` is still available.

### POST `/api/v1/db/documents/list`

```json
{
  "project": "custom",
  "include_deleted": false
}
```

- `project` optional
- `include_deleted` optional, default `false`

Compatibility: `GET /api/v1/db/documents/list` with query params is still available.

### POST `/api/v1/db/documents/delete`

Soft-delete document metadata (`is_deleted=true`, version increment).

```json
{
  "project": "custom",
  "relative_path": "notes/intro.md"
}
```

Compatibility: `DELETE /api/v1/db/documents/delete?project=...&relative_path=...` is still available.

## Index Job APIs

### POST `/api/v1/db/index-jobs/create`

Create an indexing task.

```json
{
  "job_type": "reindex",
  "project": "custom",
  "relative_path": "notes/intro.md",
  "document_id": 1,
  "trigger_source": "admin",
  "payload_json": "{}"
}
```

### POST `/api/v1/db/index-jobs/fetch-next`

Atomically fetch one pending task and mark it `running`.

Return:
- `data = null` if no pending jobs.
- otherwise one job record.

### GET `/api/v1/db/index-jobs/get/{id}`

### POST `/api/v1/db/index-jobs/finish-success`

Mark job success and increment global index version.

```json
{
  "job_id": 1001
}
```

Response includes both updated `job` and `index_state`.

### POST `/api/v1/db/index-jobs/finish-failed`

Mark job failed.

```json
{
  "job_id": 1001,
  "error_message": "embedding timeout"
}
```

## Index State API

### GET `/api/v1/db/index/state`

Returns current global index version and last successful job id.

Example:

```json
{
  "success": true,
  "data": {
    "current_version": 12,
    "last_success_job_id": 1001,
    "updated_at": "2026-02-28 12:00:00"
  }
}
```
