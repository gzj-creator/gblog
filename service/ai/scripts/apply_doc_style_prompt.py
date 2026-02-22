#!/usr/bin/env python3
"""Apply unified style prompt to Galay repo docs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, List


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]

OPEN_FENCE_RE = re.compile(r"^```([A-Za-z0-9_+-]*)\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
CMAKE_RE = re.compile(
    r"^(cmake_minimum_required|project|add_executable|add_library|target_link_libraries|"
    r"target_include_directories|find_package|install)\s*\(",
    re.IGNORECASE,
)
CPP_HINT_RE = re.compile(
    r"(#include\b|std::|int\s+main\s*\(|co_await|co_return|namespace\s+\w+|class\s+\w+|struct\s+\w+)"
)
COMMAND_RE = re.compile(
    r"^\$?\s*(git|cmake|make|brew|apt|apt-get|dnf|yum|sudo|docker|kubectl|python|python3|pip|"
    r"npm|pnpm|yarn|g\+\+|gcc|clang\+\+|clang|./[^\s]+)(?:\s|$)",
    re.IGNORECASE,
)

INSTALL_SECTION = (
    "### macOS\n\n"
    "```bash\n"
    "brew install cmake ninja pkg-config\n"
    "# 根据下方“依赖”章节补充库（如 openssl、spdlog、simdjson、liburing 等）\n"
    "```\n\n"
    "### Linux (Ubuntu/Debian)\n\n"
    "```bash\n"
    "sudo apt update\n"
    "sudo apt install -y build-essential cmake ninja-build pkg-config\n"
    "# 根据下方“依赖”章节补充库（如 libssl-dev、libspdlog-dev、libsimdjson-dev、liburing-dev 等）\n"
    "```\n\n"
)


def _iter_targets() -> Iterable[Path]:
    yield from sorted(REPO_ROOT.glob("repos/galay-*/**/*.md"))


def _infer_language(block_lines: List[str], heading: str) -> str:
    text = "\n".join(block_lines).strip()
    heading_lc = heading.lower()

    if not text:
        return "text"

    if "构建选项" in heading or "编译选项" in heading:
        return "text"
    if "cmakelists" in heading_lc:
        return "cmake"

    non_empty = [line.strip() for line in block_lines if line.strip()]
    if non_empty and re.match(r"^(//|#)\s*CMakeLists", non_empty[0], flags=re.IGNORECASE):
        return "cmake"
    if any(CMAKE_RE.search(line) for line in non_empty):
        return "cmake"

    if CPP_HINT_RE.search(text):
        return "cpp"

    if all(line.startswith("-D") or line.startswith("ENABLE_") for line in non_empty):
        return "text"

    command_lines = [line for line in non_empty if COMMAND_RE.match(line) or line.startswith("#")]
    if non_empty and len(command_lines) / len(non_empty) >= 0.5:
        return "bash"

    if text.startswith("{") and ":" in text and text.endswith("}"):
        return "json"

    return "text"


def _normalize_fences(text: str) -> str:
    lines = text.split("\n")
    output: List[str] = []
    in_fence = False
    fence_lang = ""
    fence_lines: List[str] = []
    last_heading = ""

    for line in lines:
        stripped = line.strip()
        heading_match = HEADING_RE.match(stripped)
        if not in_fence and heading_match:
            last_heading = heading_match.group(2).strip()

        fence_match = OPEN_FENCE_RE.match(stripped)
        if fence_match:
            token = fence_match.group(1).strip().lower()
            if not in_fence:
                in_fence = True
                fence_lang = token
                fence_lines = []
                continue

            if token:
                fence_lines.append(line)
                continue

            inferred = _infer_language(fence_lines, last_heading)
            if not fence_lang:
                normalized_lang = inferred
            elif fence_lang == "text" and inferred != "text":
                normalized_lang = inferred
            else:
                normalized_lang = fence_lang
            output.append(f"```{normalized_lang}")
            output.extend(fence_lines)
            output.append("```")
            in_fence = False
            fence_lang = ""
            fence_lines = []
            continue

        if in_fence:
            fence_lines.append(line)
        else:
            output.append(line)

    if in_fence:
        inferred = _infer_language(fence_lines, last_heading)
        if not fence_lang:
            normalized_lang = inferred
        elif fence_lang == "text" and inferred != "text":
            normalized_lang = inferred
        else:
            normalized_lang = fence_lang
        output.append(f"```{normalized_lang}")
        output.extend(fence_lines)
        output.append("```")

    return "\n".join(output)


def _ensure_install_section(text: str, file_path: Path) -> str:
    if file_path.name != "README.md":
        return text
    # Only apply this template to top-level repo README:
    # repos/galay-*/README.md
    if file_path.parent.parent.name != "repos":
        return text
    if file_path.parent.name == "galay-ecosystem":
        return text

    updated = text.replace("\n## 构建\n", "\n## 安装与构建\n")
    if "## 安装与构建" not in updated:
        return updated

    has_macos = "### macOS" in updated
    has_linux = "### Linux (Ubuntu/Debian)" in updated
    if has_macos and has_linux:
        return updated

    pattern = re.compile(r"^## 安装与构建\s*$", re.MULTILINE)
    return pattern.sub("## 安装与构建\n\n" + INSTALL_SECTION.rstrip(), updated, count=1)


def _normalize_text(text: str, file_path: Path) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _ensure_install_section(normalized, file_path)
    normalized = _normalize_fences(normalized)
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip() + "\n"
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply unified style prompt to repos docs")
    parser.add_argument("--check", action="store_true", help="Check only, do not write files")
    args = parser.parse_args()

    changed = 0
    unchanged = 0
    for file_path in _iter_targets():
        original = file_path.read_text(encoding="utf-8", errors="ignore")
        updated = _normalize_text(original, file_path)
        if updated == original:
            unchanged += 1
            continue

        changed += 1
        if not args.check:
            file_path.write_text(updated, encoding="utf-8")
        print(f"[style] {'would update' if args.check else 'updated'}: {file_path.relative_to(REPO_ROOT)}")

    print(f"[style] summary changed={changed} unchanged={unchanged}")
    return 1 if args.check and changed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
