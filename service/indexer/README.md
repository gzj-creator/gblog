# Indexer Service

Independent indexing worker service.

## Responsibilities

- Poll pending index jobs from DB service
- Rebuild vector index by executing AI `build_index.py --force`
- Mark job success/failed back to DB
- Update global index version through DB `finish-success`

## Quick Start

```bash
cd service/indexer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/run_server.py --host 0.0.0.0 --port 8011
```

## Env Vars

- `INDEXER_DB_BASE_URL` default `http://127.0.0.1:8082`
- `INDEXER_POLL_INTERVAL_SECONDS` default `2.0`
- `INDEXER_AUTO_START` default `true`
- `INDEXER_AI_ROOT` default `../ai`
- `INDEXER_BUILD_SCRIPT` default `scripts/build_index.py`
- `INDEXER_BUILD_FORCE` default `true`
- `PYTHON_BIN` default `python3`

## API Docs

- [API](/Users/gongzhijie/Desktop/projects/git/blog/service/indexer/docs/api.md)
