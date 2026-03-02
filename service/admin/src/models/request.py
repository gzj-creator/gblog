from typing import List, Optional

from pydantic import BaseModel, Field


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class AuthRefreshRequest(BaseModel):
    refresh_token: str


class AuthLogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class AdminUpsertDocumentRequest(BaseModel):
    project: Optional[str] = None
    relative_path: str
    content: str
    auto_reindex: Optional[bool] = None


class AdminDeleteDocumentRequest(BaseModel):
    project: Optional[str] = None
    relative_path: str
    auto_reindex: Optional[bool] = None


class AdminConfigUpdateRequest(BaseModel):
    auto_reindex_on_doc_change: Optional[bool] = None
    allowed_extensions: Optional[List[str]] = None
    max_upload_size_kb: Optional[int] = Field(default=None, ge=1, le=10240)
    default_doc_project: Optional[str] = None
    managed_docs_path: Optional[str] = None
