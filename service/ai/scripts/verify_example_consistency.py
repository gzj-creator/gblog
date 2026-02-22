#!/usr/bin/env python3
"""Verify usage snippets stay aligned with documented demo/example patterns."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    message: str
    allow_path_contains: tuple[str, ...] = ()


TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".cpp",
    ".cc",
    ".cxx",
    ".h",
    ".hpp",
    ".hh",
    ".hxx",
    ".py",
}

SKIP_DIRS = {
    ".git",
    "build",
    "node_modules",
    ".venv",
    "venv",
    ".cache",
    "__pycache__",
    "vector_store",
    "logs",
}

RULES: List[Rule] = [
    Rule(
        name="http-default-ctor",
        pattern=re.compile(r"\bHttpServer\s+[A-Za-z_]\w*\s*;"),
        message="HttpServer must use HttpServerConfig constructor",
        allow_path_contains=(
            "service/ai/src/services/rag_service.py",
            "service/ai/src/services/chat_service.py",
        ),
    ),
    Rule(
        name="http-scheduler-ctor",
        pattern=re.compile(r"\bHttpServer\s+[A-Za-z_]\w*\s*\([^)]*scheduler[^)]*\)\s*;"),
        message="HttpServer must not be constructed with scheduler args",
        allow_path_contains=(
            "service/ai/src/services/rag_service.py",
            "service/ai/src/services/chat_service.py",
        ),
    ),
    Rule(
        name="http-route-method-on-server",
        pattern=re.compile(r"\bserver\.(?:get|post|put|del|delete|patch|head|options)\s*\("),
        message="HttpServer demo should use HttpRouter::addHandler, not server.get/post",
        allow_path_contains=(
            "service/ai/src/services/rag_service.py",
            "service/ai/src/services/chat_service.py",
        ),
    ),
    Rule(
        name="http-start-with-port",
        pattern=re.compile(r"\bserver\.start\s*\(\s*\d+\s*\)"),
        message="HttpServer start should use router, not numeric port",
        allow_path_contains=(
            "service/ai/src/services/rag_service.py",
            "service/ai/src/services/chat_service.py",
        ),
    ),
    Rule(
        name="rpc-braced-config",
        pattern=re.compile(r"\bRpcServer\s+[A-Za-z_]\w*\s*\(\s*\{"),
        message="RpcServer should be created via RpcServerConfig",
    ),
    Rule(
        name="iocontent-singleton",
        pattern=re.compile(r"\b(?:IoContext|IOContext)\s*::\s*GetInstance\s*\("),
        message="IoContext singleton API is forbidden",
        allow_path_contains=(
            "service/ai/src/services/rag_service.py",
            "service/ai/src/services/chat_service.py",
        ),
    ),
    Rule(
        name="runtime-singleton",
        pattern=re.compile(r"\bRuntime::getInstance\s*\("),
        message="Runtime singleton API is forbidden",
        allow_path_contains=(
            "service/ai/src/services/rag_service.py",
            "service/ai/src/services/chat_service.py",
        ),
    ),
]


def iter_files(root: Path, targets: Iterable[str]) -> Iterable[Path]:
    for relative in targets:
        target = root / relative
        if not target.exists():
            continue
        if target.is_file():
            yield target
            continue
        for file_path in target.rglob("*"):
            if not file_path.is_file():
                continue
            if any(part in SKIP_DIRS for part in file_path.parts):
                continue
            if file_path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            yield file_path


def is_allowed(file_path: Path, rule: Rule, root: Path) -> bool:
    rel = file_path.relative_to(root).as_posix()
    return any(token in rel for token in rule.allow_path_contains)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify usage snippets align with demo/example patterns")
    parser.add_argument(
        "--targets",
        nargs="+",
        default=["repos", "frontend", "service"],
        help="Relative paths to scan",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    findings: List[str] = []

    for file_path in iter_files(repo_root, args.targets):
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        rel = file_path.relative_to(repo_root).as_posix()
        for idx, line in enumerate(lines, start=1):
            for rule in RULES:
                if not rule.pattern.search(line):
                    continue
                if is_allowed(file_path, rule, repo_root):
                    continue
                findings.append(f"{rel}:{idx}: {rule.name}: {rule.message}\n  {line.strip()}")

    if findings:
        print("[FAIL] Example consistency check failed:\n")
        for item in findings:
            print(item)
        print(f"\nTotal findings: {len(findings)}")
        return 1

    print("[PASS] Example consistency check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
