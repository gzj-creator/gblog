from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.middleware import error_handler, request_logger, setup_cors, setup_rate_limit
from src.api.router import router as api_router
from src.config import settings
from src.core.vector_store import VectorStoreManager
from src.services.chat_service import ChatService
from src.services.index_service import IndexService
from src.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

# ------------------------------------------------------------------
# 全局服务实例（lifespan 中初始化）
# ------------------------------------------------------------------
_vector_store: VectorStoreManager | None = None
_chat_service: ChatService | None = None
_index_service: IndexService | None = None


def get_vector_store() -> VectorStoreManager:
    assert _vector_store is not None, "Vector store not initialized"
    return _vector_store


def get_chat_service() -> ChatService:
    assert _chat_service is not None, "Chat service not initialized"
    return _chat_service


def get_index_service() -> IndexService:
    assert _index_service is not None, "Index service not initialized"
    return _index_service


# ------------------------------------------------------------------
# 生命周期
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _vector_store, _chat_service, _index_service

    logger.info("Initializing Galay AI Service...")

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required")

    _vector_store = VectorStoreManager()
    _vector_store.initialize()

    _chat_service = ChatService(_vector_store)
    _index_service = IndexService(_vector_store)

    logger.info("Galay AI Service initialized successfully")
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
        return {"status": "ok", "service": "Galay AI Service", "version": "2.0.0"}

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
