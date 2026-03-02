from __future__ import annotations

import threading
from typing import Callable

import requests

from src.utils.logger import get_logger

logger = get_logger(__name__)


class DbIndexStateWatcher:
    """Poll DB index_state and trigger callback when index version changes."""

    def __init__(
        self,
        *,
        base_url: str,
        poll_interval_seconds: float,
        on_version_change: Callable[[int], None],
        timeout_seconds: float = 3.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._poll_interval_seconds = max(0.5, float(poll_interval_seconds))
        self._timeout_seconds = max(0.5, float(timeout_seconds))
        self._on_version_change = on_version_change

        self._current_version: int | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def current_version(self) -> int | None:
        return self._current_version

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="db-index-state-watcher", daemon=True)
        self._thread.start()
        logger.info("DB index-state watcher started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        logger.info("DB index-state watcher stopped")

    def refresh_once(self) -> int | None:
        latest = self._fetch_current_version()
        if latest is None:
            return None

        previous = self._current_version
        self._current_version = latest

        if previous is not None and latest != previous:
            logger.info("Detected index version change: %s -> %s", previous, latest)
            try:
                self._on_version_change(latest)
            except Exception:
                logger.exception("Failed to process index version change callback")

        return latest

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.refresh_once()
            self._stop_event.wait(self._poll_interval_seconds)

    def _fetch_current_version(self) -> int | None:
        try:
            response = requests.get(
                f"{self._base_url}/api/v1/db/index/state",
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as exc:
            logger.warning("Fetch db index_state failed: %s", exc)
            return None

        if response.status_code >= 400:
            logger.warning("Fetch db index_state failed, status=%s body=%s", response.status_code, response.text[:200])
            return None

        try:
            payload = response.json()
        except ValueError:
            logger.warning("Fetch db index_state failed, invalid json")
            return None

        if not payload.get("success", False):
            logger.warning("Fetch db index_state failed, success=false")
            return None

        data = payload.get("data") or {}
        version = data.get("current_version")
        if version is None:
            return None

        try:
            return int(version)
        except (TypeError, ValueError):
            logger.warning("Fetch db index_state failed, invalid current_version=%r", version)
            return None
