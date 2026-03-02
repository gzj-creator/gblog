from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.router import router as api_router
from src.config import settings
from src.services.admin_config_service import AdminConfigService
from src.services.auth_service import AuthService
from src.services.db_client import DbServiceClient
from src.services.document_admin_service import DocumentAdminService

_auth_service: AuthService | None = None
_config_service: AdminConfigService | None = None
_db_client: DbServiceClient | None = None
_doc_service: DocumentAdminService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _auth_service, _config_service, _db_client, _doc_service

    _auth_service = AuthService()
    _config_service = AdminConfigService()
    _db_client = DbServiceClient(base_url=settings.DB_SERVICE_BASE_URL)
    _doc_service = DocumentAdminService(config_service=_config_service, db_client=_db_client)

    yield


def get_auth_service() -> AuthService:
    if _auth_service is None:
        raise RuntimeError("auth service not initialized")
    return _auth_service


def get_admin_config_service() -> AdminConfigService:
    if _config_service is None:
        raise RuntimeError("config service not initialized")
    return _config_service


def get_db_client() -> DbServiceClient:
    if _db_client is None:
        raise RuntimeError("db client not initialized")
    return _db_client


def get_document_admin_service() -> DocumentAdminService:
    if _doc_service is None:
        raise RuntimeError("document admin service not initialized")
    return _doc_service


def create_app() -> FastAPI:
    app = FastAPI(
        title="GBlob Admin Service",
        description="Admin service for managed docs and indexing tasks",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(api_router)

    @app.get("/")
    async def root():
        return {"status": "ok", "service": "admin", "version": "1.0.0"}

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "admin"}

    return app


app = create_app()
