# Indexer Service API

Base URL: `http://<indexer-host>:8011`

Indexer consumes jobs from `db-service` and executes vector rebuild by calling AI build script.

## GET `/health`

Returns worker status.

Example:

```json
{
  "status": "ok",
  "worker": {
    "running": true,
    "in_progress": false,
    "last_job_id": 1024,
    "last_status": "success",
    "last_error": "",
    "last_run_at": "2026-02-28T12:00:00+00:00",
    "handled_jobs": 10,
    "failed_jobs": 1,
    "index_version": 7
  }
}
```

## POST `/api/v1/indexer/run-once`

Immediately try one fetch-and-process cycle.

Response:

```json
{
  "success": true,
  "state": {
    "last_status": "success"
  }
}
```

## GET `/api/v1/indexer/state`

Returns same worker state snapshot without forcing execution.
