import json
import asyncio

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.concurrency import run_in_threadpool

from src.models.request import ChatRequest
from src.models.response import ChatResponse
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

CHAT_TIMEOUT_SECONDS = 120
STREAM_QUERY_TIMEOUT_SECONDS = 120
STREAM_HEARTBEAT_SECONDS = 10
STREAM_MEMORY_TIMEOUT_SECONDS = 180


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(payload: ChatRequest, request: Request):
    """聊天接口"""
    from src.app import get_chat_service

    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    svc = get_chat_service()
    try:
        if payload.use_memory:
            result = await asyncio.wait_for(
                run_in_threadpool(svc.chat, payload.message, payload.session_id),
                timeout=CHAT_TIMEOUT_SECONDS,
            )
        else:
            result = await asyncio.wait_for(
                run_in_threadpool(svc.query, payload.message),
                timeout=CHAT_TIMEOUT_SECONDS,
            )
    except TimeoutError:
        raise HTTPException(status_code=504, detail="LLM request timed out") from None

    return ChatResponse(**result)


@router.post("/chat/stream")
@limiter.limit("30/minute")
async def chat_stream(payload: ChatRequest, request: Request):
    """流式聊天接口（SSE）"""
    from src.app import get_chat_service

    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    svc = get_chat_service()
    def _event(data: dict) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def event_generator():
        try:
            # 首包尽快返回，降低代理/前端连接阶段超时概率。
            yield _event({"ping": True, "stage": "accepted"})

            if payload.use_memory:
                stream_iter = svc.chat_stream(payload.message, payload.session_id).__aiter__()
                start_at = asyncio.get_running_loop().time()
                while True:
                    if asyncio.get_running_loop().time() - start_at > STREAM_MEMORY_TIMEOUT_SECONDS:
                        yield _event({"error": "LLM stream timed out"})
                        yield _event({"done": True, "sources": []})
                        break

                    try:
                        data = await asyncio.wait_for(
                            stream_iter.__anext__(),
                            timeout=STREAM_HEARTBEAT_SECONDS,
                        )
                    except StopAsyncIteration:
                        break
                    except TimeoutError:
                        # 心跳包，避免长思考场景下前端/代理误判超时。
                        yield _event({"ping": True})
                        continue

                    yield _event(data)
                    if data.get("done") or data.get("error"):
                        break
                return

            result = await asyncio.wait_for(
                run_in_threadpool(svc.query, payload.message),
                timeout=STREAM_QUERY_TIMEOUT_SECONDS,
            )
            response_text = result.get("response", "")
            sources = result.get("sources", [])
            blocks = result.get("blocks", [])
            if response_text:
                if blocks:
                    yield _event({"replace": response_text, "blocks": blocks})
                else:
                    yield _event({"content": response_text})
            yield _event({"done": True, "sources": sources, "blocks": blocks})
        except TimeoutError:
            yield _event({"error": "LLM request timed out"})
            yield _event({"done": True, "sources": []})
        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield _event({"error": str(e)})
            yield _event({"done": True, "sources": []})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
