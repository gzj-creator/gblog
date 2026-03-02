# Admin Service

Independent admin service for document management.

## Responsibilities

- Admin authentication
- Managed document upload/update/delete (local disk)
- Persist document metadata to DB service
- Create index jobs in DB service (asynchronous indexing)
- Read index/job state for admin UI

## Quick Start

```bash
cd service/admin
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/run_server.py --host 0.0.0.0 --port 8010
```

## API Docs

- [API](/Users/gongzhijie/Desktop/projects/git/blog/service/admin/docs/api.md)

## Key Env Vars

- `DB_SERVICE_BASE_URL` default `http://127.0.0.1:8082`
- `ADMIN_MANAGED_DOCS_PATH` default `./managed_docs`
- `ADMIN_RUNTIME_CONFIG_PATH` default `./runtime/admin_config.json`
- `ADMIN_AUTO_REINDEX_ON_DOC_CHANGE` default `true`
- `ADMIN_ALLOWED_DOC_EXTENSIONS` default `.md,.txt,.rst`
- `ADMIN_MAX_UPLOAD_SIZE_KB` default `1024`
