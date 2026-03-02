from fastapi import APIRouter, Body, Depends, Header, HTTPException

from src.api.security import extract_bearer_token, require_admin
from src.models.request import AuthLoginRequest, AuthLogoutRequest, AuthRefreshRequest
from src.utils.exceptions import AuthenticationError

router = APIRouter(prefix="/auth")


@router.post("/login")
async def login(payload: AuthLoginRequest):
    from src.app import get_auth_service

    try:
        data = get_auth_service().login(payload.username, payload.password)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=e.message) from None
    return {"success": True, "data": data}


@router.post("/refresh")
async def refresh_token(payload: AuthRefreshRequest):
    from src.app import get_auth_service

    try:
        data = get_auth_service().refresh(payload.refresh_token)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=e.message) from None
    return {"success": True, "data": data}


@router.get("/me")
async def me(current_admin: dict = Depends(require_admin)):
    return {"success": True, "data": current_admin}


@router.post("/logout")
async def logout(
    payload: AuthLogoutRequest = Body(default_factory=AuthLogoutRequest),
    authorization: str | None = Header(default=None),
):
    from src.app import get_auth_service

    access_token = None
    if authorization:
        try:
            access_token = extract_bearer_token(authorization)
        except HTTPException:
            access_token = None

    get_auth_service().logout(access_token=access_token, refresh_token=payload.refresh_token)
    return {"success": True, "message": "Logged out"}
