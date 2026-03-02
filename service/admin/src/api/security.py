from fastapi import Header, HTTPException


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    prefix = "bearer "
    if not authorization.lower().startswith(prefix):
        raise HTTPException(status_code=401, detail="Invalid Authorization scheme")
    token = authorization[len(prefix) :].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing access token")
    return token


def require_admin(authorization: str | None = Header(default=None)) -> dict:
    from src.app import get_auth_service
    from src.utils.exceptions import AuthenticationError

    token = extract_bearer_token(authorization)
    try:
        return get_auth_service().verify_access_token(token)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=e.message) from None
