from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.middleware import error_handler, request_logger, setup_cors, setup_rate_limit
from src.api.router import router as api_router
from src.config import settings
from src.core.vector_store import VectorStoreManager
from src.services.chat_service import ChatService
from src.services.index_state_watcher import DbIndexStateWatcher
from src.utils.exceptions import ServiceUnavailableError
from src.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

# ------------------------------------------------------------------
# 全局服务实例（lifespan 中初始化）
# ------------------------------------------------------------------
_vector_store: VectorStoreManager | None = None
_chat_service: ChatService | None = None
_index_state_watcher: DbIndexStateWatcher | None = None
_startup_error: str | None = None
_index_version: int | None = None


def _service_unavailable_message(default_message: str) -> str:
    return _startup_error or default_message


def _on_index_version_changed(version: int) -> None:
    """DB index_state 版本变化时，热加载本地持久化向量索引。"""
    global _startup_error, _index_version

    _index_version = version
    if _vector_store is None:
        return

    try:
        if not _vector_store.has_persisted_index():
            logger.warning("Index version changed to %s, but no persisted local vector index found", version)
            return
        _vector_store.load_existing()
        if _chat_service is not None:
            _chat_service.on_index_reloaded()
        _startup_error = None
        logger.info("Vector store hot reloaded for index version=%s", version)
    except Exception as exc:
        _startup_error = f"Vector store hot reload failed: {exc}"
        logger.exception(_startup_error)


def _try_recover_vector_store() -> bool:
    """尝试在运行时恢复向量索引可用性。"""
    global _startup_error

    if _vector_store is None:
        return False
    if _vector_store.is_ready:
        return True

    try:
        logger.info("Vector store not ready, attempting lazy recovery...")
        if not _vector_store.has_persisted_index():
            logger.warning("No persisted vector index for lazy recovery")
            return False
        _vector_store.load_existing()
        if _chat_service is not None:
            _chat_service.on_index_reloaded()
        _startup_error = None
        logger.info("Vector store lazy recovery succeeded")
        return True
    except Exception as exc:
        _startup_error = f"Vector store initialization failed: {exc}"
        logger.exception(_startup_error)
        return False


def get_vector_store() -> VectorStoreManager:
    if _vector_store is None:
        raise ServiceUnavailableError(
            _service_unavailable_message("Vector store is not initialized")
        )
    if not _vector_store.is_ready:
        if _try_recover_vector_store():
            return _vector_store
        raise ServiceUnavailableError(
            _service_unavailable_message("Vector index is not ready, please rebuild index")
        )
    return _vector_store


def get_chat_service() -> ChatService:
    if _chat_service is None:
        raise ServiceUnavailableError(
            _service_unavailable_message("Chat service is not initialized")
        )
    if _vector_store is None or not _vector_store.is_ready:
        if _try_recover_vector_store():
            return _chat_service
        raise ServiceUnavailableError(
            _service_unavailable_message("Vector index is not ready, chat API is unavailable")
        )
    return _chat_service


# ------------------------------------------------------------------
# 生命周期
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _vector_store, _chat_service, _index_state_watcher
    global _startup_error, _index_version

    logger.info("Initializing Galay AI Service...")
    _vector_store = None
    _chat_service = None
    _index_state_watcher = None
    _startup_error = None
    _index_version = None

    if not settings.OPENAI_API_KEY.strip():
        _startup_error = "OPENAI_API_KEY is empty, AI APIs are unavailable"
        logger.warning(_startup_error)
        yield
        logger.info("Shutting down Galay AI Service...")
        return

    try:
        _vector_store = VectorStoreManager()
        try:
            _vector_store.initialize()
        except Exception as exc:
            _startup_error = f"Vector store initialization failed: {exc}"
            logger.exception(_startup_error)

        _chat_service = ChatService(_vector_store)

        db_base_url = settings.DB_SERVICE_BASE_URL.strip()
        if settings.INDEX_STATE_AUTO_RELOAD and db_base_url:
            _index_state_watcher = DbIndexStateWatcher(
                base_url=db_base_url,
                poll_interval_seconds=settings.INDEX_STATE_POLL_INTERVAL_SECONDS,
                timeout_seconds=settings.INDEX_STATE_REQUEST_TIMEOUT_SECONDS,
                on_version_change=_on_index_version_changed,
            )
            _index_version = _index_state_watcher.refresh_once()
            _index_state_watcher.start()
            logger.info("Index-state watcher enabled, db_base_url=%s, initial_version=%s", db_base_url, _index_version)
        else:
            logger.info("Index-state watcher disabled")

        if _startup_error:
            logger.warning("Galay AI Service started in degraded mode: %s", _startup_error)
        else:
            logger.info("Galay AI Service initialized successfully")
    except Exception as exc:
        _startup_error = f"AI service startup failed: {exc}"
        _vector_store = None
        _chat_service = None
        if _index_state_watcher is not None:
            _index_state_watcher.stop()
        _index_state_watcher = None
        logger.exception(_startup_error)

    yield

    if _index_state_watcher is not None:
        _index_state_watcher.stop()
        _index_state_watcher = None
    logger.info("Shutting down Galay AI Service...")


# ------------------------------------------------------------------
# 应用工厂
# ------------------------------------------------------------------
def create_app() -> FastAPI:
    setup_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title="Galay AI Service",
        description="AI-powered Q&A service for Galay framework documentation",
        version="2.1.0",
        lifespan=lifespan,
    )

    app.middleware("http")(error_handler)
    app.middleware("http")(request_logger)
    setup_cors(app)
    setup_rate_limit(app)

    app.include_router(api_router)

    @app.get("/", tags=["Health"])
    async def root():
        return {
            "status": "ok" if _startup_error is None else "degraded",
            "service": "Galay AI Service",
            "version": "2.1.0",
            "startup_error": _startup_error,
        }

    @app.get("/health", tags=["Health"])
    async def health():
        return {
            "status": "ok" if _startup_error is None else "degraded",
            "startup_error": _startup_error,
            "services": {
                "vector_store_initialized": _vector_store is not None and _vector_store.is_ready,
                "chat_service_initialized": _chat_service is not None,
                "index_state_watch_enabled": _index_state_watcher is not None,
                "index_state_watch_running": _index_state_watcher.is_running if _index_state_watcher else False,
            },
            "index_version": _index_version,
        }

    return app


app = create_app()
