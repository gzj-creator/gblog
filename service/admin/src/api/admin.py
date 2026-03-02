from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from src.api.security import require_admin
from src.models.request import AdminConfigUpdateRequest, AdminDeleteDocumentRequest, AdminUpsertDocumentRequest
from src.models.response import StatsResponse
from src.services.db_client import DbClientError

router = APIRouter()


def _parse_optional_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise HTTPException(status_code=400, detail="auto_reindex must be true/false")


@router.get("/stats", response_model=StatsResponse)
async def get_stats(_: dict = Depends(require_admin)):
    from src.app import get_admin_config_service, get_document_admin_service, get_db_client

    config = get_admin_config_service().get_config()
    docs = get_document_admin_service().list_documents(project=None, include_deleted=False)
    index_state = get_db_client().get_index_state()

    return StatsResponse(
        success=True,
        stats={
            "document_count": len(docs),
            "index_state": index_state,
            "admin_config": config,
        },
    )


@router.get("/docs")
async def list_documents(
    project: str | None = Query(default=None),
    include_deleted: bool = Query(default=False),
    _: dict = Depends(require_admin),
):
    from src.app import get_document_admin_service

    try:
        documents = get_document_admin_service().list_documents(
            project=project,
            include_deleted=include_deleted,
        )
    except DbClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None

    return {"success": True, "documents": documents}


@router.get("/docs/content")
async def get_document_content(
    relative_path: str = Query(...),
    project: str | None = Query(default=None),
    _: dict = Depends(require_admin),
):
    from src.app import get_document_admin_service

    try:
        doc = get_document_admin_service().get_document_content(project=project, relative_path=relative_path)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except DbClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None

    return {"success": True, "document": doc}


@router.post("/docs/upload")
async def upload_document(
    file: UploadFile = File(...),
    project: str | None = Form(default=None),
    relative_path: str | None = Form(default=None),
    auto_reindex: str | None = Form(default=None),
    _: dict = Depends(require_admin),
):
    from src.app import get_document_admin_service

    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Missing uploaded filename")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        result = get_document_admin_service().upload_document(
            project=project,
            relative_path=relative_path,
            filename=filename,
            data=data,
            auto_reindex=_parse_optional_bool(auto_reindex),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except DbClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None

    return {"success": True, **result}


@router.put("/docs/content")
async def upsert_document_content(
    request: AdminUpsertDocumentRequest,
    _: dict = Depends(require_admin),
):
    from src.app import get_document_admin_service

    try:
        result = get_document_admin_service().upsert_document_content(
            project=request.project,
            relative_path=request.relative_path,
            content=request.content,
            auto_reindex=request.auto_reindex,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except DbClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None

    return {"success": True, **result}


@router.delete("/docs")
async def delete_document(
    request: AdminDeleteDocumentRequest,
    _: dict = Depends(require_admin),
):
    from src.app import get_document_admin_service

    try:
        result = get_document_admin_service().delete_document(
            project=request.project,
            relative_path=request.relative_path,
            auto_reindex=request.auto_reindex,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except DbClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None

    return {"success": True, **result}


@router.get("/jobs/{job_id}")
async def get_job(job_id: int, _: dict = Depends(require_admin)):
    from src.app import get_db_client

    try:
        job = get_db_client().get_index_job(job_id)
    except DbClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None

    return {"success": True, "job": job}


@router.get("/config")
async def get_admin_config(_: dict = Depends(require_admin)):
    from src.app import get_admin_config_service

    return {"success": True, "config": get_admin_config_service().get_config()}


@router.put("/config")
async def update_admin_config(request: AdminConfigUpdateRequest, _: dict = Depends(require_admin)):
    from src.app import get_admin_config_service

    patch = request.model_dump(exclude_none=True)
    try:
        config = get_admin_config_service().update_config(patch)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return {"success": True, "config": config}
