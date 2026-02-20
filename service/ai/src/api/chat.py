import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.models.request import ChatRequest
from src.models.response import ChatResponse
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(payload: ChatRequest, request: Request):
    """聊天接口"""
    from src.app import get_chat_service

    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    svc = get_chat_service()
    if payload.use_memory:
        result = svc.chat(payload.message, payload.session_id)
    else:
        result = svc.query(payload.message)

    return ChatResponse(**result)


@router.post("/chat/stream")
@limiter.limit("30/minute")
async def chat_stream(payload: ChatRequest, request: Request):
    """流式聊天接口（SSE）"""
    from src.app import get_chat_service

    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    svc = get_chat_service()

    async def event_generator():
        async for data in svc.chat_stream(payload.message, payload.session_id):
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
