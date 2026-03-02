from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


class DbClientError(RuntimeError):
    pass


@dataclass
class DbClient:
    base_url: str
    timeout_seconds: float = 20.0

    def _request(self, method: str, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}{path}"
        resp = requests.request(method=method, url=url, json=json_body, timeout=self.timeout_seconds)
        try:
            payload = resp.json()
        except ValueError as exc:
            raise DbClientError(f"db response is not json: {resp.status_code} {resp.text[:200]}") from exc

        if resp.status_code >= 400:
            message = payload.get("error", {}).get("message", f"http {resp.status_code}")
            raise DbClientError(f"db request failed: {method} {path}: {message}")

        if not payload.get("success", False):
            message = payload.get("error", {}).get("message", "unknown db error")
            raise DbClientError(f"db request failed: {method} {path}: {message}")

        return payload

    def fetch_next_job(self) -> dict[str, Any] | None:
        payload = self._request("POST", "/api/v1/db/index-jobs/fetch-next")
        return payload.get("data")

    def finish_job_success(self, job_id: int) -> dict[str, Any]:
        payload = self._request("POST", "/api/v1/db/index-jobs/finish-success", {"job_id": job_id})
        return payload.get("data", {})

    def finish_job_failed(self, job_id: int, error_message: str) -> dict[str, Any]:
        payload = self._request(
            "POST",
            "/api/v1/db/index-jobs/finish-failed",
            {"job_id": job_id, "error_message": error_message},
        )
        return payload.get("data", {})

    def get_index_state(self) -> dict[str, Any]:
        payload = self._request("GET", "/api/v1/db/index/state")
        return payload.get("data", {})
