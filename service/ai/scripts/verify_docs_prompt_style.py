#!/usr/bin/env python3
"""Verify repos docs follow unified style prompt."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]

OPEN_FENCE_RE = re.compile(r"^```([A-Za-z0-9_+-]*)\s*$")


def _iter_repo_markdown() -> Iterable[Path]:
    yield from sorted(REPO_ROOT.glob("repos/galay-*/**/*.md"))


def _check_fence_openings(text: str) -> List[str]:
    issues: List[str] = []
    in_fence = False

    for idx, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        match = OPEN_FENCE_RE.match(line)
        if not match:
            continue

        token = match.group(1).strip()
        if not in_fence:
            if not token:
                issues.append(f"bare_fence_open_line:{idx}")
            in_fence = True
            continue

        if not token:
            in_fence = False

    if in_fence:
        issues.append("unclosed_fence")
    return issues


def _check_install_sections(path: Path, text: str) -> List[str]:
    if path.name != "README.md":
        return []
    # Only enforce install section for top-level repo README:
    # repos/galay-*/README.md
    if path.parent.parent.name != "repos":
        return []
    if path.parent.name == "galay-ecosystem":
        return []

    issues: List[str] = []
    if "## 安装与构建" not in text:
        issues.append("missing_install_build_section")
    if "### macOS" not in text:
        issues.append("missing_macos_section")
    if "### Linux (Ubuntu/Debian)" not in text:
        issues.append("missing_linux_section")
    if "### 通用构建" not in text:
        issues.append("missing_common_build_section")
    return issues


def main() -> int:
    problems: List[str] = []
    files = list(_iter_repo_markdown())
    if not files:
        print("[verify_docs_prompt_style] ERROR: no repo README files found")
        return 1

    for file_path in files:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        issues = []
        issues.extend(_check_install_sections(file_path, text))
        issues.extend(_check_fence_openings(text))
        if issues:
            problems.append(f"- {file_path.relative_to(REPO_ROOT)}: {'; '.join(issues)}")

    print(f"[verify_docs_prompt_style] files={len(files)} problem_files={len(problems)}")
    if problems:
        for row in problems:
            print(row)
        return 1

    print("[verify_docs_prompt_style] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
