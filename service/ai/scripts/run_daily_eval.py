#!/usr/bin/env python3
"""Run daily evaluation, archive report, and send alert webhook when needed."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict
from urllib import error, request


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _send_webhook(webhook: str, payload: Dict[str, Any]) -> tuple[bool, str]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            return True, f"http {resp.status}"
    except error.URLError as exc:
        return False, str(exc)


def _build_eval_cmd(ai_dir: Path, args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        str(ai_dir / "scripts" / "evaluate_kb.py"),
        "--mode",
        "all",
        "--base-url",
        args.base_url,
        "--cases",
        args.cases,
        "--min-pass-rate",
        str(args.min_pass_rate),
        "--top-k",
        str(args.top_k),
        "--timeout",
        str(args.timeout),
    ]
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="Run daily KB evaluation with alerting")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="AI service URL")
    parser.add_argument("--cases", default="eval/benchmark_cases.json", help="benchmark case path")
    parser.add_argument("--min-pass-rate", type=float, default=0.8, help="minimum acceptable pass rate")
    parser.add_argument("--top-k", type=int, default=5, help="top-k for search eval")
    parser.add_argument("--timeout", type=float, default=20.0, help="request timeout seconds")
    parser.add_argument(
        "--alert-webhook",
        default="",
        help="webhook url for alerts (fallback: EVAL_ALERT_WEBHOOK env)",
    )
    parser.add_argument(
        "--notify-on-pass",
        action="store_true",
        help="send webhook notification on success as well",
    )
    args = parser.parse_args()

    ai_dir = Path(__file__).resolve().parent.parent
    eval_report = ai_dir / "eval" / "last_eval_report.json"
    eval_history_dir = ai_dir / "eval" / "history"
    eval_history_dir.mkdir(parents=True, exist_ok=True)

    cmd = _build_eval_cmd(ai_dir, args)
    started_at = datetime.now(timezone.utc)
    proc = subprocess.run(
        cmd,
        cwd=str(ai_dir),
        capture_output=True,
        text=True,
    )
    ended_at = datetime.now(timezone.utc)

    report = _load_json(eval_report)
    summary = report.get("summary", {}) if isinstance(report, dict) else {}
    pass_rate = float(summary.get("pass_rate", 0.0) or 0.0)
    expected = float(summary.get("min_pass_rate", args.min_pass_rate) or args.min_pass_rate)
    passed = proc.returncode == 0 and pass_rate >= expected
    status = "PASS" if passed else "FAIL"

    history_record = {
        "status": status,
        "started_at_utc": started_at.isoformat(),
        "ended_at_utc": ended_at.isoformat(),
        "duration_seconds": round((ended_at - started_at).total_seconds(), 3),
        "command": cmd,
        "returncode": proc.returncode,
        "summary": summary,
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-4000:],
    }

    ts = started_at.strftime("%Y%m%d-%H%M%S")
    history_path = eval_history_dir / f"daily-eval-{ts}.json"
    history_path.write_text(json.dumps(history_record, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[{status}] pass_rate={pass_rate:.4f} expected>={expected:.4f}")
    print(f"[INFO] history report: {history_path}")

    webhook = args.alert_webhook.strip() or os.getenv("EVAL_ALERT_WEBHOOK", "").strip()
    should_notify = bool(webhook) and (not passed or args.notify_on_pass)
    if should_notify:
        text = (
            f"[Galay AI Daily Eval] {status} | pass_rate={pass_rate:.4f} | "
            f"expected>={expected:.4f} | report={history_path.name}"
        )
        payload = {
            "text": text,
            "status": status,
            "summary": summary,
            "history_report": str(history_path),
            "started_at_utc": history_record["started_at_utc"],
        }
        ok, detail = _send_webhook(webhook, payload)
        print(f"[INFO] webhook sent={ok} detail={detail}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
