from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import settings
from src.db_client import DbClient, DbClientError


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkerState:
    running: bool = False
    in_progress: bool = False
    last_job_id: int | None = None
    last_status: str = "idle"
    last_error: str = ""
    last_run_at: str = ""
    handled_jobs: int = 0
    failed_jobs: int = 0
    index_version: int | None = None


@dataclass
class IndexerWorker:
    db_client: DbClient
    ai_root: Path
    build_script: Path
    python_bin: str
    force_rebuild: bool
    max_error_length: int
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _state: WorkerState = field(default_factory=WorkerState)
    _stop_event: threading.Event = field(default_factory=threading.Event)

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._state.running,
                "in_progress": self._state.in_progress,
                "last_job_id": self._state.last_job_id,
                "last_status": self._state.last_status,
                "last_error": self._state.last_error,
                "last_run_at": self._state.last_run_at,
                "handled_jobs": self._state.handled_jobs,
                "failed_jobs": self._state.failed_jobs,
                "index_version": self._state.index_version,
            }

    def stop(self) -> None:
        self._stop_event.set()

    def run_loop(self, poll_interval_seconds: float) -> None:
        with self._lock:
            self._state.running = True
            self._state.last_status = "loop_started"

        while not self._stop_event.is_set():
            self.run_once()
            self._stop_event.wait(max(0.1, poll_interval_seconds))

        with self._lock:
            self._state.running = False
            self._state.in_progress = False
            self._state.last_status = "loop_stopped"
            self._state.last_run_at = _now_iso()

    def run_once(self) -> None:
        with self._lock:
            if self._state.in_progress:
                return
            self._state.in_progress = True

        try:
            job = self.db_client.fetch_next_job()
            if not job:
                with self._lock:
                    self._state.last_status = "no_pending_job"
                    self._state.last_run_at = _now_iso()
                return

            job_id = int(job.get("id", 0))
            with self._lock:
                self._state.last_job_id = job_id
                self._state.last_status = "processing"
                self._state.last_error = ""
                self._state.last_run_at = _now_iso()

            self._rebuild_vector_index()

            result = self.db_client.finish_job_success(job_id)
            index_state = result.get("index_state", {}) if isinstance(result, dict) else {}

            with self._lock:
                self._state.handled_jobs += 1
                self._state.last_status = "success"
                self._state.last_error = ""
                self._state.last_run_at = _now_iso()
                if isinstance(index_state, dict):
                    version = index_state.get("current_version")
                    if isinstance(version, int):
                        self._state.index_version = version

        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            trimmed = message[: self.max_error_length]

            with self._lock:
                self._state.failed_jobs += 1
                self._state.last_status = "failed"
                self._state.last_error = trimmed
                self._state.last_run_at = _now_iso()
                job_id = self._state.last_job_id

            if job_id:
                try:
                    self.db_client.finish_job_failed(job_id, trimmed)
                except Exception:  # noqa: BLE001
                    pass

        finally:
            with self._lock:
                self._state.in_progress = False

    def refresh_index_version(self) -> None:
        state = self.db_client.get_index_state()
        with self._lock:
            version = state.get("current_version") if isinstance(state, dict) else None
            if isinstance(version, int):
                self._state.index_version = version

    def _rebuild_vector_index(self) -> None:
        if not self.build_script.exists():
            raise RuntimeError(f"build script not found: {self.build_script}")

        cmd = [self.python_bin, str(self.build_script)]
        if self.force_rebuild:
            cmd.append("--force")

        completed = subprocess.run(
            cmd,
            cwd=str(self.ai_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            detail = stderr if stderr else stdout
            if not detail:
                detail = f"build index failed with code {completed.returncode}"
            raise RuntimeError(detail)
