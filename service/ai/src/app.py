from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI

from src.api.middleware import error_handler, request_logger, setup_cors, setup_rate_limit
from src.api.router import router as api_router
from src.config import settings
from src.core.vector_store import VectorStoreManager
from src.services.chat_service import ChatService
from src.services.index_service import IndexService
from src.utils.exceptions import ServiceUnavailableError
from src.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

# ------------------------------------------------------------------
# 全局服务实例（lifespan 中初始化）
# ------------------------------------------------------------------
_vector_store: VectorStoreManager | None = None
_chat_service: ChatService | None = None
_index_service: IndexService | None = None
_startup_error: str | None = None
_vector_store_recovery_lock = Lock()


def _service_unavailable_message(default_message: str) -> str:
    return _startup_error or default_message


def _try_recover_vector_store() -> bool:
    """尝试在运行时恢复向量索引可用性。"""
    global _startup_error

    if _vector_store is None:
        return False
    if _vector_store.is_ready:
        return True

    with _vector_store_recovery_lock:
        if _vector_store.is_ready:
            return True
        try:
            logger.info("Vector store not ready, attempting lazy recovery...")
            # 请求路径只允许“加载已存在索引”，避免在线构建导致长阻塞和超时。
            if not _vector_store.has_persisted_index():
                logger.warning("No persisted vector index for lazy recovery")
                return False
            _vector_store.load_existing()
            _startup_error = None
            logger.info("Vector store lazy recovery succeeded")
            return True
        except Exception as e:
            _startup_error = f"Vector store initialization failed: {e}"
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


def get_index_service() -> IndexService:
    if _index_service is None:
        raise ServiceUnavailableError(
            _service_unavailable_message("Index service is not initialized")
        )
    return _index_service


# ------------------------------------------------------------------
# 生命周期
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _vector_store, _chat_service, _index_service, _startup_error

    logger.info("Initializing Galay AI Service...")
    _vector_store = None
    _chat_service = None
    _index_service = None
    _startup_error = None

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
        except Exception as e:
            _startup_error = f"Vector store initialization failed: {e}"
            logger.exception(_startup_error)

        _chat_service = ChatService(_vector_store)
        _index_service = IndexService(_vector_store)

        if _startup_error:
            logger.warning(f"Galay AI Service started in degraded mode: {_startup_error}")
        else:
            logger.info("Galay AI Service initialized successfully")
    except Exception as e:
        _startup_error = f"AI service startup failed: {e}"
        _vector_store = None
        _chat_service = None
        _index_service = None
        logger.exception(_startup_error)

    yield
    logger.info("Shutting down Galay AI Service...")


# ------------------------------------------------------------------
# 应用工厂
# ------------------------------------------------------------------
def create_app() -> FastAPI:
    setup_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title="Galay AI Service",
        description="AI-powered Q&A service for Galay framework documentation",
        version="2.0.0",
        lifespan=lifespan,
    )

    # 中间件（注册顺序：后注册的先执行）
    app.middleware("http")(error_handler)
    app.middleware("http")(request_logger)
    setup_cors(app)
    setup_rate_limit(app)

    # 路由
    app.include_router(api_router)

    @app.get("/", tags=["Health"])
    async def root():
        return {
            "status": "ok" if _startup_error is None else "degraded",
            "service": "Galay AI Service",
            "version": "2.0.0",
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
                "index_service_initialized": _index_service is not None,
            },
        }

    return app


app = create_app()
