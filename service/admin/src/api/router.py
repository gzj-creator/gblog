from fastapi import APIRouter

from src.api import admin, auth

router = APIRouter(prefix="/api/v1/admin")

router.include_router(auth.router, tags=["AdminAuth"])
router.include_router(admin.router, tags=["Admin"])
