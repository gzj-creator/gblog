import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.utils.exceptions import AIServiceError
from src.utils.logger import get_logger

logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address)


async def error_handler(request: Request, call_next):
    """全局异常处理中间件"""
    try:
        return await call_next(request)
    except AIServiceError as e:
        logger.error(f"Service error: {e.message}")
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.message},
        )
    except Exception as e:
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Internal server error"},
        )


async def request_logger(request: Request, call_next):
    """请求日志中间件"""
    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed:.0f}ms)")
    return response


def setup_cors(app: FastAPI) -> None:
    """配置 CORS"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_rate_limit(app: FastAPI) -> None:
    """配置请求限流"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
