#!/usr/bin/env python3
"""Minimal upstream SSE server used by proxy demo.

Route:
  POST /api/chat/stream
"""

from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mock SSE upstream service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=19000)
    parser.add_argument("--chunk-delay", type=float, default=0.35)
    parser.add_argument("--linger-seconds", type=float, default=0.0)
    return parser


class MockSseHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    chunk_delay = 0.35
    linger_seconds = 0.0

    def log_message(self, fmt: str, *args) -> None:
        # Keep stdout concise and machine-readable.
        message = fmt % args
        print(f"[mock] {self.command} {self.path} - {message}", flush=True)

    def _read_body(self) -> bytes:
        content_length = int(self.headers.get("Content-Length", "0") or 0)
        if content_length <= 0:
            return b""
        return self.rfile.read(content_length)

    def _send_chunk(self, payload: str) -> None:
        data = payload.encode("utf-8")
        self.wfile.write(f"{len(data):X}\r\n".encode("ascii"))
        self.wfile.write(data)
        self.wfile.write(b"\r\n")
        self.wfile.flush()

    def do_POST(self) -> None:  # noqa: N802
        _ = self._read_body()

        if self.path != "/api/chat/stream":
            body = json.dumps({"detail": "not found", "path": self.path}).encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        chunks = [
            'data: {"content":"hello "}\n\n',
            'data: {"content":"stream"}\n\n',
            'data: {"done": true, "sources": []}\n\n',
        ]

        for index, chunk in enumerate(chunks):
            self._send_chunk(chunk)
            if index + 1 < len(chunks):
                time.sleep(self.chunk_delay)

        if self.linger_seconds > 0:
            time.sleep(self.linger_seconds)

        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()


def main() -> None:
    args = build_arg_parser().parse_args()
    MockSseHandler.chunk_delay = max(args.chunk_delay, 0.0)
    MockSseHandler.linger_seconds = max(args.linger_seconds, 0.0)

    server = HTTPServer((args.host, args.port), MockSseHandler)
    print(
        f"[mock] listening on http://{args.host}:{args.port} "
        f"(chunk_delay={MockSseHandler.chunk_delay}s linger={MockSseHandler.linger_seconds}s)",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
