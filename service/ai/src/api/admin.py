from fastapi import APIRouter, HTTPException

from src.config import settings
from src.models.request import RebuildRequest
from src.models.response import StatsResponse
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/rebuild")
async def rebuild_index(request: RebuildRequest):
    """重建向量索引"""
    from src.app import get_index_service

    if not request.confirm:
        raise HTTPException(status_code=400, detail="Please confirm rebuild by setting confirm=true")

    svc = get_index_service()
    result = svc.rebuild_index()
    return {"success": True, "message": result["message"]}


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """服务统计信息"""
    from src.app import get_chat_service, get_index_service

    chat_svc = get_chat_service()
    index_svc = get_index_service()
    index_stats = index_svc.get_index_stats()

    return StatsResponse(
        success=True,
        stats={
            "active_sessions": len(chat_svc.get_active_sessions()),
            "model": settings.MODEL_NAME,
            "embedding_model": settings.EMBEDDING_MODEL,
            "doc_paths": len(settings.validate_docs_paths()),
            "index": index_stats,
        },
    )


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """清除会话"""
    from src.app import get_chat_service

    get_chat_service().clear_session(session_id)
    return {"success": True, "message": f"Session {session_id} cleared"}
