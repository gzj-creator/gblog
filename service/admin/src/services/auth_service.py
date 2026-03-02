import secrets
from dataclasses import dataclass
from time import time
from typing import Dict

from src.config import settings
from src.utils.exceptions import AuthenticationError


@dataclass
class _TokenRecord:
    username: str
    token_type: str
    expires_at: float


class AuthService:
    def __init__(self) -> None:
        self._enabled = settings.ADMIN_AUTH_ENABLED
        self._username = settings.ADMIN_USERNAME.strip() or "admin"
        self._password = settings.ADMIN_PASSWORD
        self._access_ttl = max(60, settings.ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        self._refresh_ttl = max(60, settings.ADMIN_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)
        self._tokens: Dict[str, _TokenRecord] = {}

    def login(self, username: str, password: str) -> dict:
        if self._enabled and (username != self._username or password != self._password):
            raise AuthenticationError("Invalid username or password")

        now = int(time())
        access_token = self._issue_token(self._username, "access", self._access_ttl)
        refresh_token = self._issue_token(self._username, "refresh", self._refresh_ttl)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self._access_ttl,
            "issued_at": now,
            "user": {"username": self._username, "role": "admin"},
        }

    def refresh(self, refresh_token: str) -> dict:
        record = self._get_valid_record(refresh_token, "refresh")
        now = int(time())
        access_token = self._issue_token(record.username, "access", self._access_ttl)
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self._access_ttl,
            "issued_at": now,
        }

    def verify_access_token(self, token: str) -> dict:
        if not self._enabled:
            return {"username": self._username, "role": "admin"}
        record = self._get_valid_record(token, "access")
        return {"username": record.username, "role": "admin"}

    def logout(self, access_token: str | None = None, refresh_token: str | None = None) -> None:
        if access_token:
            self._tokens.pop(access_token, None)
        if refresh_token:
            self._tokens.pop(refresh_token, None)

    def _issue_token(self, username: str, token_type: str, ttl: int) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = time() + max(1, ttl)
        self._tokens[token] = _TokenRecord(username=username, token_type=token_type, expires_at=expires_at)
        return token

    def _get_valid_record(self, token: str, expected_type: str) -> _TokenRecord:
        token = token.strip()
        if not token:
            raise AuthenticationError("Missing token")

        record = self._tokens.get(token)
        if record is None:
            raise AuthenticationError("Invalid token")
        if record.expires_at <= time():
            self._tokens.pop(token, None)
            raise AuthenticationError("Token expired")
        if record.token_type != expected_type:
            raise AuthenticationError("Invalid token type")
        return record
