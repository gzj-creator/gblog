#!/usr/bin/env python3
"""POST to SSE endpoint and print each received line with elapsed time."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SSE stream probe")
    parser.add_argument("--url", required=True, help="Target stream URL")
    parser.add_argument(
        "--body",
        default='{"message":"ping","session_id":"demo","use_memory":true}',
        help="JSON request body",
    )
    parser.add_argument("--timeout", type=float, default=8.0)
    return parser


def maybe_done_event(line: str) -> bool:
    if not line.startswith("data:"):
        return False
    payload = line.split(":", 1)[1].strip()
    if not payload:
        return False
    try:
        data = json.loads(payload)
    except Exception:
        return False
    return bool(data.get("done") is True or data.get("error"))


def main() -> int:
    args = build_arg_parser().parse_args()
    request = urllib.request.Request(
        args.url,
        data=args.body.encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            status = getattr(response, "status", 0)
            content_type = response.headers.get("Content-Type", "")
            print(f"status={status} content_type={content_type}")
            while True:
                raw_line = response.readline()
                if not raw_line:
                    break
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                elapsed = time.monotonic() - start
                print(f"{elapsed:7.3f}s {line}")
                if maybe_done_event(line):
                    break
            return 0
    except urllib.error.HTTPError as exc:
        print(f"http_error={exc.code} reason={exc.reason}", file=sys.stderr)
        try:
            body = exc.read().decode("utf-8", errors="replace")
            if body:
                print(body, file=sys.stderr)
        except Exception:
            pass
        return 2
    except Exception as exc:  # pragma: no cover - demo diagnostic path
        print(f"request_failed={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
