from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict

from src.services.admin_config_service import AdminConfigService
from src.services.db_client import DbServiceClient

_PROJECT_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


class DocumentAdminService:
    def __init__(self, config_service: AdminConfigService, db_client: DbServiceClient) -> None:
        self._config_service = config_service
        self._db_client = db_client

    def list_documents(self, project: str | None = None, include_deleted: bool = False) -> list[dict[str, Any]]:
        return self._db_client.list_documents(project=project, include_deleted=include_deleted)

    def get_document_content(self, *, project: str | None, relative_path: str) -> dict[str, Any]:
        project_name = self._normalize_project(project)
        rel = self._normalize_relative_path(relative_path)
        file_path = self._managed_root() / project_name / rel
        if not file_path.exists() or not file_path.is_file():
            raise ValueError("Document not found")

        metadata = self._db_client.get_document(project=project_name, relative_path=rel)
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        metadata["content"] = content
        return metadata

    def upload_document(
        self,
        *,
        project: str | None,
        relative_path: str | None,
        filename: str,
        data: bytes,
        auto_reindex: bool | None,
    ) -> dict[str, Any]:
        project_name = self._normalize_project(project)
        rel = self._normalize_relative_path(relative_path or filename)
        self._validate_extension(rel)
        self._validate_upload_size(len(data))

        file_path = self._managed_root() / project_name / rel
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)

        sha256 = hashlib.sha256(data).hexdigest()
        doc = self._db_client.upsert_document(
            project=project_name,
            relative_path=rel,
            sha256=sha256,
            size_bytes=len(data),
            is_deleted=False,
        )

        reindex = self._maybe_enqueue_reindex(
            project=project_name,
            relative_path=rel,
            document_id=doc.get("id"),
            auto_reindex=auto_reindex,
            trigger_source="admin_upload",
        )
        return {"document": doc, "reindex": reindex}

    def upsert_document_content(
        self,
        *,
        project: str | None,
        relative_path: str,
        content: str,
        auto_reindex: bool | None,
    ) -> dict[str, Any]:
        project_name = self._normalize_project(project)
        rel = self._normalize_relative_path(relative_path)
        self._validate_extension(rel)

        encoded = content.encode("utf-8")
        file_path = self._managed_root() / project_name / rel
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        sha256 = hashlib.sha256(encoded).hexdigest()
        doc = self._db_client.upsert_document(
            project=project_name,
            relative_path=rel,
            sha256=sha256,
            size_bytes=len(encoded),
            is_deleted=False,
        )

        reindex = self._maybe_enqueue_reindex(
            project=project_name,
            relative_path=rel,
            document_id=doc.get("id"),
            auto_reindex=auto_reindex,
            trigger_source="admin_upsert",
        )
        return {"document": doc, "reindex": reindex}

    def delete_document(self, *, project: str | None, relative_path: str, auto_reindex: bool | None) -> dict[str, Any]:
        project_name = self._normalize_project(project)
        rel = self._normalize_relative_path(relative_path)

        file_path = self._managed_root() / project_name / rel
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            self._cleanup_empty_dirs(file_path.parent, stop_at=self._managed_root() / project_name)

        doc = self._db_client.delete_document(project=project_name, relative_path=rel)

        reindex = self._maybe_enqueue_reindex(
            project=project_name,
            relative_path=rel,
            document_id=doc.get("id"),
            auto_reindex=auto_reindex,
            trigger_source="admin_delete",
        )
        return {"deleted": {"project": project_name, "relative_path": rel}, "reindex": reindex}

    def _maybe_enqueue_reindex(
        self,
        *,
        project: str,
        relative_path: str,
        document_id: Any,
        auto_reindex: bool | None,
        trigger_source: str,
    ) -> Dict[str, Any]:
        enabled = self._config_service.should_auto_reindex() if auto_reindex is None else auto_reindex
        if not enabled:
            return {"triggered": False}

        numeric_doc_id = int(document_id) if isinstance(document_id, int) or str(document_id).isdigit() else None
        payload = {
            "project": project,
            "relative_path": relative_path,
            "trigger_source": trigger_source,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }

        job = self._db_client.create_index_job(
            project=project,
            relative_path=relative_path,
            document_id=numeric_doc_id,
            trigger_source=trigger_source,
            payload_json=json.dumps(payload, ensure_ascii=False),
        )
        return {"triggered": True, "job": job}

    def _managed_root(self) -> Path:
        path = self._config_service.managed_docs_path().expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _normalize_project(self, project: str | None) -> str:
        value = (project or self._config_service.default_project()).strip()
        if not _PROJECT_NAME_RE.match(value):
            raise ValueError("Invalid project name, use [a-zA-Z0-9_-] and start with alnum")
        return value

    @staticmethod
    def _normalize_relative_path(relative_path: str) -> str:
        candidate = relative_path.strip().replace("\\", "/")
        if not candidate:
            raise ValueError("relative_path is required")
        pure = PurePosixPath(candidate)
        if pure.is_absolute() or ".." in pure.parts:
            raise ValueError("relative_path cannot be absolute or contain '..'")
        normalized = str(pure)
        if normalized in {"", "."}:
            raise ValueError("Invalid relative_path")
        return normalized

    def _validate_extension(self, relative_path: str) -> None:
        suffix = Path(relative_path).suffix
        if not self._config_service.is_extension_allowed(suffix):
            raise ValueError(f"Unsupported file extension: {suffix}")

    def _validate_upload_size(self, size: int) -> None:
        max_size = self._config_service.max_upload_size_bytes()
        if size > max_size:
            raise ValueError(f"File too large, max {max_size // 1024}KB")

    @staticmethod
    def _cleanup_empty_dirs(path: Path, stop_at: Path) -> None:
        current = path
        while current != stop_at and current.exists() and current.is_dir():
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent
