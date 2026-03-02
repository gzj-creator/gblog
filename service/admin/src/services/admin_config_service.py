import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List

from src.config import settings


class AdminConfigService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._config_file = Path(settings.ADMIN_RUNTIME_CONFIG_PATH).expanduser()
        self._config: Dict[str, Any] = self._build_default_config()
        self._load_from_file()

    def get_config(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._config)

    def update_config(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            for key, value in patch.items():
                if value is None or key not in self._config:
                    continue
                self._config[key] = self._normalize_value(key, value)
            self._persist_locked()
            return dict(self._config)

    def is_extension_allowed(self, suffix: str) -> bool:
        normalized = self._normalize_extension(suffix)
        with self._lock:
            allowed = self._config.get("allowed_extensions", [])
        return normalized in allowed

    def max_upload_size_bytes(self) -> int:
        with self._lock:
            kb = int(self._config.get("max_upload_size_kb", settings.ADMIN_MAX_UPLOAD_SIZE_KB))
        return max(1, kb) * 1024

    def should_auto_reindex(self) -> bool:
        with self._lock:
            return bool(self._config.get("auto_reindex_on_doc_change", True))

    def default_project(self) -> str:
        with self._lock:
            value = str(self._config.get("default_doc_project", "custom")).strip()
        return value or "custom"

    def managed_docs_path(self) -> Path:
        with self._lock:
            raw = str(self._config.get("managed_docs_path", settings.ADMIN_MANAGED_DOCS_PATH))
        return Path(raw).expanduser()

    def _build_default_config(self) -> Dict[str, Any]:
        return {
            "managed_docs_path": str(Path(settings.ADMIN_MANAGED_DOCS_PATH).expanduser()),
            "auto_reindex_on_doc_change": bool(settings.ADMIN_AUTO_REINDEX_ON_DOC_CHANGE),
            "allowed_extensions": self._parse_extensions(settings.ADMIN_ALLOWED_DOC_EXTENSIONS),
            "max_upload_size_kb": int(settings.ADMIN_MAX_UPLOAD_SIZE_KB),
            "default_doc_project": settings.ADMIN_DEFAULT_DOC_PROJECT.strip() or "custom",
        }

    def _load_from_file(self) -> None:
        if not self._config_file.exists():
            return
        try:
            content = json.loads(self._config_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(content, dict):
            return
        for key in list(self._config.keys()):
            if key in content and content[key] is not None:
                self._config[key] = self._normalize_value(key, content[key])

    def _persist_locked(self) -> None:
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        self._config_file.write_text(json.dumps(self._config, ensure_ascii=False, indent=2), encoding="utf-8")

    def _normalize_value(self, key: str, value: Any) -> Any:
        if key == "auto_reindex_on_doc_change":
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"1", "true", "yes", "on"}:
                    return True
                if lowered in {"0", "false", "no", "off"}:
                    return False
            return bool(value)

        if key == "max_upload_size_kb":
            return max(1, int(value))

        if key == "allowed_extensions":
            if isinstance(value, str):
                return self._parse_extensions(value)
            if isinstance(value, list):
                parsed: List[str] = []
                for item in value:
                    normalized = self._normalize_extension(str(item))
                    if normalized and normalized not in parsed:
                        parsed.append(normalized)
                return parsed or [".md"]
            return self._config[key]

        if key == "managed_docs_path":
            raw = str(value).strip()
            return str(Path(raw or settings.ADMIN_MANAGED_DOCS_PATH).expanduser())

        if key == "default_doc_project":
            project = str(value).strip()
            return project or "custom"

        return value

    @staticmethod
    def _normalize_extension(ext: str) -> str:
        normalized = ext.strip().lower()
        if not normalized:
            return ""
        if not normalized.startswith("."):
            normalized = "." + normalized
        return normalized

    def _parse_extensions(self, raw: str) -> List[str]:
        parsed: List[str] = []
        for item in raw.split(","):
            normalized = self._normalize_extension(item)
            if normalized and normalized not in parsed:
                parsed.append(normalized)
        return parsed or [".md"]
