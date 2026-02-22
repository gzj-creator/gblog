#!/usr/bin/env python3
"""No-network markdown normalization regression checks.

This script validates:
1) Synthetic cases that previously caused formatting regressions.
2) All markdown files in this repository with sanity checks.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


AI_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(AI_ROOT))

from src.core.document_cleaner import clean_document_content  # noqa: E402
from src.core.markdown_blocks import markdown_to_blocks  # noqa: E402
from src.core.markdown_normalizer import normalize_markdown_content  # noqa: E402


DECORATIVE_RE = re.compile(r"[✅☑✔✳✴★☆⭐🔥🌟✨💡🔧⚙🛠📈📌📍🚀🎯▶►■□▪▫◆◇•·]")
QUOTED_FENCE_RE = re.compile(r"[“”\"']```|```[“”\"']")
EMPTY_FENCE_RE = re.compile(r"(?ms)^```[A-Za-z0-9_-]*\n\s*```[ \t]*$")
FENCE_LINE_RE = re.compile(r"^```[A-Za-z0-9_-]*\s*$")
LANG_ORPHAN_RE = re.compile(r"^(cpp|c\+\+|bash|shell|sh|zsh|cmake|text|plaintext)\s*$", re.IGNORECASE)
ISOLATED_NUMBER_RE = re.compile(r"^\d+\.\s*$")


def _run(cmd: List[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd), text=True)


def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def run_synthetic_cases() -> None:
    cases: List[Tuple[str, str, Dict[str, str]]] = [
        (
            "raw_cmake",
            (
                "1. 环境要求：\n"
                "- C++20 编译器（GCC 11+/Clang 14+）\n"
                "- CMake 3.20+ 构建系统\n"
                "2. 安装步骤：git clone https://github.com/galay/galay.git 使用 CMake 构建：\n"
                "cmake -S . -B build\n"
                "cmake --build build -j\n"
                "3. 编译运行命令：g++ -std=c++20 main.cpp -o demo ./demo\n"
            ),
            {
                "must_contain_1": "## 环境要求",
                "must_contain_2": "## 安装步骤",
                "must_contain_3": "使用 CMake 构建：",
                "must_contain_4": "cmake --build build --parallel",
                "must_contain_5": "## 编译运行命令",
                "must_contain_6": "```bash\ng++ -std=c++20 main.cpp -o demo ./demo\n```",
                "must_not_contain_1": "```bash\nGCC 11+/Clang 14+）",
            },
        ),
        (
            "portable_parallel",
            (
                "```bash\n"
                "cmake --build build -j\"$(nproc)\"\n"
                "make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu)\n"
                "```\n"
            ),
            {
                "must_contain_1": "cmake --build build --parallel",
                "must_contain_2": "make -j",
                "must_not_contain_1": "$(nproc",
                "must_not_contain_2": "sysctl -n hw.ncpu",
                "must_not_contain_3": " -j\"$(nproc)\"",
            },
        ),
        (
            "quoted_fence",
            "\"```bash\npython3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt\n```\"",
            {
                "must_contain_1": "```bash\npython3 -m venv .venv",
                "must_not_contain_1": "\"```",
                "must_not_contain_2": "```\"",
            },
        ),
        (
            "repeated_ol",
            "1. 第一项\n1. 第二项\n1. 第三项\n",
            {
                "must_contain_1": "1. 第一项",
                "must_contain_2": "1. 第二项",
                "must_contain_3": "1. 第三项",
            },
        ),
    ]

    for name, raw, rules in cases:
        normalized = normalize_markdown_content(raw, target="answer", strip_decorative=True)
        blocks = markdown_to_blocks(normalized)
        for key, value in rules.items():
            if key.startswith("must_contain"):
                _assert(value in normalized, f"[{name}] missing required fragment: {value!r}")
            if key.startswith("must_not_contain"):
                _assert(value not in normalized, f"[{name}] forbidden fragment found: {value!r}")

        _assert(len(blocks) > 0, f"[{name}] blocks should not be empty")
        if name == "raw_cmake":
            types = {str(block.get("type", "")) for block in blocks}
            _assert("heading" in types, "[raw_cmake] missing heading block")
            _assert("list" in types, "[raw_cmake] missing list block")
            _assert("code" in types, "[raw_cmake] missing code block")


def _collect_markdown_files() -> List[Path]:
    output = _run(["rg", "--files", "-g", "*.md"], cwd=REPO_ROOT)
    files = [REPO_ROOT / line.strip() for line in output.splitlines() if line.strip()]
    files.sort()
    return files


def _check_cleaned_content(path: Path, cleaned: str) -> List[str]:
    issues: List[str] = []
    if not cleaned.strip():
        issues.append("cleaned_empty")
    if DECORATIVE_RE.search(cleaned):
        issues.append("decorative_left")
    if QUOTED_FENCE_RE.search(cleaned):
        issues.append("quoted_fence_left")
    if EMPTY_FENCE_RE.search(cleaned):
        issues.append("empty_fence")

    fence_count = sum(1 for line in cleaned.splitlines() if FENCE_LINE_RE.match(line.strip()))
    if fence_count % 2 != 0:
        issues.append("unclosed_fence")

    orphan_lang_lines = [
        idx + 1 for idx, line in enumerate(cleaned.splitlines()) if LANG_ORPHAN_RE.match(line.strip())
    ]
    if orphan_lang_lines:
        issues.append(f"orphan_lang_line:{orphan_lang_lines[:5]}")

    isolated_number_lines = [
        idx + 1 for idx, line in enumerate(cleaned.splitlines()) if ISOLATED_NUMBER_RE.match(line.strip())
    ]
    if isolated_number_lines:
        issues.append(f"isolated_number_line:{isolated_number_lines[:5]}")

    lines = cleaned.splitlines()
    in_bash = False
    bash_cn_lines: List[int] = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if FENCE_LINE_RE.match(stripped):
            token = stripped[3:].strip().lower()
            if not in_bash:
                in_bash = token in {"bash", "sh", "shell", "zsh"}
            else:
                in_bash = False
            continue
        if in_bash and re.search(r"[一-龥]", stripped) and not stripped.startswith("#"):
            bash_cn_lines.append(i)

    if bash_cn_lines:
        issues.append(f"bash_cn_line:{bash_cn_lines[:5]}")

    return issues


def run_repository_scan() -> None:
    files = _collect_markdown_files()
    if not files:
        raise AssertionError("No markdown files found in repository.")

    problems: List[Tuple[Path, List[str]]] = []
    raw_chars = 0
    cleaned_chars = 0

    for file_path in files:
        raw = file_path.read_text(encoding="utf-8", errors="ignore")
        cleaned = clean_document_content(raw, "markdown")
        raw_chars += len(raw)
        cleaned_chars += len(cleaned)

        issues = _check_cleaned_content(file_path, cleaned)
        if issues:
            problems.append((file_path.relative_to(REPO_ROOT), issues))

    print("=== Markdown Format Validation ===")
    print(f"files={len(files)} raw_chars={raw_chars} cleaned_chars={cleaned_chars}")
    print(f"problem_files={len(problems)}")

    if problems:
        for path, issue_list in problems:
            print(f"- {path}: {'; '.join(issue_list)}")
        raise AssertionError("Markdown format validation failed.")


def main() -> int:
    try:
        run_synthetic_cases()
        run_repository_scan()
    except Exception as exc:  # pragma: no cover - command-line failure path
        print(f"[verify_markdown_format] ERROR: {exc}")
        return 1

    print("[verify_markdown_format] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
