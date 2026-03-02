from fastapi import APIRouter

from src.api import chat, search

router = APIRouter(prefix="/api")

router.include_router(chat.router, tags=["Chat"])
router.include_router(search.router, tags=["Search"])
