# DB Service

MySQL-backed database abstraction service.

## Scope

- User profile and credential storage APIs
- Managed document metadata APIs
- Index job queue APIs
- Global index version state API

## Quick Start

```bash
bash scripts/S3-Build.sh
bash scripts/S2-InitSchema.sh
bash scripts/S1-RunServer.sh
```

## Health Check

```bash
curl http://127.0.0.1:8082/health
```

## Environment Variables

`db-server` reads MySQL config from:

- `DB_MYSQL_HOST` (default `127.0.0.1`)
- `DB_MYSQL_PORT` (default `3306`)
- `DB_MYSQL_USER` (default `root`)
- `DB_MYSQL_PASSWORD` (default `password`)
- `DB_MYSQL_DATABASE` (default `gblob`)
- `DB_MYSQL_CHARSET` (default `utf8mb4`)

Server bind can be changed via:

- `DB_SERVICE_HOST` (default `0.0.0.0`)
- `DB_SERVICE_PORT` (default `8082`)

## API Docs

- [API](/Users/gongzhijie/Desktop/projects/git/blog/service/db/docs/api.md)
- [Schema](/Users/gongzhijie/Desktop/projects/git/blog/service/db/docs/schema.sql)

## Tests

```bash
# User CRUD
bash scripts/S4-RunCrudTest.sh

# Document metadata + index job queue
bash scripts/S5-RunDocumentIndexTest.sh
```
