# Admin Service API

Base URL: `http://<admin-host>:8010`

All business endpoints are under prefix: `/api/v1/admin`.


## Auth

### POST `/api/v1/admin/auth/login`

```json
{
  "username": "admin",
  "password": "admin123456"
}
```

### POST `/api/v1/admin/auth/refresh`

```json
{
  "refresh_token": "..."
}
```

### GET `/api/v1/admin/auth/me`

`Authorization: Bearer <access_token>`

### POST `/api/v1/admin/auth/logout`

```json
{
  "refresh_token": "..."
}
```

## Managed Docs

### GET `/api/v1/admin/docs?project={project}&include_deleted={bool}`

List managed document metadata from DB service.

### GET `/api/v1/admin/docs/content?project={project}&relative_path={path}`

Read local managed document content plus DB metadata.

### POST `/api/v1/admin/docs/upload`

`multipart/form-data`

Fields:
- `file` required
- `project` optional
- `relative_path` optional
- `auto_reindex` optional (`true`/`false`)

Behavior:
- save file to managed docs path
- upsert metadata into DB
- create index job if `auto_reindex=true` (or global config enabled)

### PUT `/api/v1/admin/docs/content`

```json
{
  "project": "custom",
  "relative_path": "notes/intro.md",
  "content": "# Intro",
  "auto_reindex": true
}
```

### DELETE `/api/v1/admin/docs`

```json
{
  "project": "custom",
  "relative_path": "notes/intro.md",
  "auto_reindex": true
}
```

## Jobs / Stats

### GET `/api/v1/admin/jobs/{job_id}`

Fetch one index job status from DB.

### GET `/api/v1/admin/stats`

Returns document count + DB index state + admin config.

## Config

### GET `/api/v1/admin/config`

### PUT `/api/v1/admin/config`

```json
{
  "auto_reindex_on_doc_change": true,
  "allowed_extensions": [".md", ".txt"],
  "max_upload_size_kb": 2048,
  "default_doc_project": "custom",
  "managed_docs_path": "./managed_docs"
}
```
