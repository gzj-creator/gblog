from __future__ import annotations

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from src.config import settings
from src.db_client import DbClient
from src.worker import IndexerWorker

worker: IndexerWorker | None = None
worker_thread: threading.Thread | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker, worker_thread

    db = DbClient(base_url=settings.INDEXER_DB_BASE_URL)
    worker = IndexerWorker(
        db_client=db,
        ai_root=settings.ai_root_path(),
        build_script=settings.build_script_path(),
        python_bin=settings.PYTHON_BIN,
        force_rebuild=settings.INDEXER_BUILD_FORCE,
        max_error_length=settings.INDEXER_MAX_ERROR_MESSAGE_LENGTH,
    )

    try:
        worker.refresh_index_version()
    except Exception:
        pass

    if settings.INDEXER_AUTO_START:
        worker_thread = threading.Thread(
            target=worker.run_loop,
            kwargs={"poll_interval_seconds": settings.INDEXER_POLL_INTERVAL_SECONDS},
            daemon=True,
            name="indexer-worker",
        )
        worker_thread.start()

    yield

    if worker is not None:
        worker.stop()
    if worker_thread is not None:
        worker_thread.join(timeout=3)


def create_app() -> FastAPI:
    app = FastAPI(
        title="GBlob Indexer Service",
        description="Background indexing worker service",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.get("/")
    async def root():
        return {"status": "ok", "service": "indexer", "version": "1.0.0"}

    @app.get("/health")
    async def health():
        if worker is None:
            return {"status": "degraded", "reason": "worker_not_initialized"}
        return {"status": "ok", "worker": worker.get_state()}

    @app.post("/api/v1/indexer/run-once")
    async def run_once():
        if worker is None:
            raise HTTPException(status_code=503, detail="worker_not_initialized")
        worker.run_once()
        return {"success": True, "state": worker.get_state()}

    @app.get("/api/v1/indexer/state")
    async def state():
        if worker is None:
            raise HTTPException(status_code=503, detail="worker_not_initialized")
        return {"success": True, "state": worker.get_state()}

    return app


app = create_app()
