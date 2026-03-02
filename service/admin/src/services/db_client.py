from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


class DbClientError(RuntimeError):
    pass


@dataclass
class DbServiceClient:
    base_url: str
    timeout_seconds: float = 20.0

    def _request(self, method: str, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}{path}"
        response = requests.request(method=method, url=url, json=json_body, timeout=self.timeout_seconds)
        try:
            payload = response.json()
        except ValueError as exc:
            raise DbClientError(f"invalid db response: {response.status_code} {response.text[:200]}") from exc

        if response.status_code >= 400:
            message = payload.get("error", {}).get("message", f"http {response.status_code}")
            raise DbClientError(message)

        if not payload.get("success", False):
            raise DbClientError(payload.get("error", {}).get("message", "db request failed"))

        return payload

    def upsert_document(
        self,
        *,
        project: str,
        relative_path: str,
        sha256: str,
        size_bytes: int,
        is_deleted: bool | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "project": project,
            "relative_path": relative_path,
            "sha256": sha256,
            "size_bytes": size_bytes,
        }
        if is_deleted is not None:
            body["is_deleted"] = is_deleted
        payload = self._request("POST", "/api/v1/db/documents/upsert", body)
        return payload.get("data", {})

    def get_document(self, *, project: str, relative_path: str) -> dict[str, Any]:
        payload = self._request(
            "POST",
            "/api/v1/db/documents/get",
            {"project": project, "relative_path": relative_path},
        )
        return payload.get("data", {})

    def list_documents(self, *, project: str | None, include_deleted: bool = False) -> list[dict[str, Any]]:
        body: dict[str, Any] = {"include_deleted": include_deleted}
        if project:
            body["project"] = project
        payload = self._request("POST", "/api/v1/db/documents/list", body)
        data = payload.get("data", [])
        if isinstance(data, list):
            return data
        return []

    def delete_document(self, *, project: str, relative_path: str) -> dict[str, Any]:
        payload = self._request(
            "POST",
            "/api/v1/db/documents/delete",
            {"project": project, "relative_path": relative_path},
        )
        return payload.get("data", {})

    def create_index_job(
        self,
        *,
        project: str,
        relative_path: str,
        document_id: int | None,
        trigger_source: str,
        payload_json: str,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "job_type": "reindex",
            "project": project,
            "relative_path": relative_path,
            "trigger_source": trigger_source,
            "payload_json": payload_json,
        }
        if document_id is not None:
            body["document_id"] = document_id
        payload = self._request("POST", "/api/v1/db/index-jobs/create", body)
        return payload.get("data", {})

    def get_index_job(self, job_id: int) -> dict[str, Any]:
        payload = self._request("GET", f"/api/v1/db/index-jobs/get/{job_id}")
        return payload.get("data", {})

    def get_index_state(self) -> dict[str, Any]:
        payload = self._request("GET", "/api/v1/db/index/state")
        return payload.get("data", {})
