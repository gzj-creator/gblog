import re
from typing import List, Optional, Tuple


_DECORATIVE_SYMBOLS_PATTERN = re.compile(
    r"[✅☑✔✳✴★☆⭐🔥🌟✨💡🔧⚙🛠📈📌📍🚀🎯▶►■□▪▫◆◇•·]+"
)
_ZERO_WIDTH_PATTERN = re.compile(r"[\u200b-\u200f\ufeff]+")

_LANG_HINTS = {
    "cpp": "cpp",
    "c++": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "hpp": "cpp",
    "h": "cpp",
    "bash": "bash",
    "shell": "bash",
    "sh": "bash",
    "zsh": "bash",
    "cmake": "cmake",
    "text": "text",
    "plaintext": "text",
}

_SHELL_COMMAND_PATTERN = (
    r"(?:git|docker|kubectl|curl|wget|npm|pnpm|yarn|pip|python|python3|cmake|make|"
    r"mkdir|cd|ls|pwd|echo|export|sudo|apt|apt-get|brew|dnf|yum|nc|telnet|cat|grep|sed|awk|"
    r"find|cp|mv|rm|chmod|chown|tar|unzip|zip|"
    r"g\+\+|gcc|clang\+\+|clang|go|cargo|javac|java)"
)
_SHELL_LINE_RE = re.compile(
    rf"^\$?\s*(?P<cmd>{_SHELL_COMMAND_PATTERN}|\.\/[^\s]+)(?=\s|$)(?P<tail>.*)$",
    re.IGNORECASE,
)
_CMAKE_LINE_RE = re.compile(
    r"^(cmake_minimum_required|project|add_executable|add_library|target_link_libraries|"
    r"target_include_directories|find_package|install)\s*\(",
    re.IGNORECASE,
)
_COMPILER_COMMANDS = {"gcc", "g++", "clang", "clang++"}


def normalize_markdown_content(
    content: str,
    *,
    target: str = "answer",
    strip_decorative: bool = True,
) -> str:
    """Normalize markdown into canonical blocks for both indexing and answer rendering."""
    if not content:
        return ""

    text = str(content).replace("\r\n", "\n").replace("\r", "\n")
    text = _ZERO_WIDTH_PATTERN.sub("", text)

    if strip_decorative:
        text = _DECORATIVE_SYMBOLS_PATTERN.sub("", text)

    text = _normalize_inline_fences(text)
    text = _normalize_outside_fences(text, lambda segment: _normalize_plain_segment(segment, target=target))
    text = _canonicalize_code_blocks(text)
    text = _normalize_fenced_blocks(text)
    text = _drop_empty_fences(text)
    text = _cleanup_whitespace(text)
    return text.strip()


def _normalize_inline_fences(text: str) -> str:
    normalized = text
    normalized = re.sub(r"([^\n])\s*[“”\"']?\s*```([A-Za-z0-9_-]*)", r"\1\n```\2", normalized)
    normalized = re.sub(r"```([A-Za-z0-9_-]+)\s+(?=\S)", r"```\1\n", normalized)
    normalized = re.sub(r"([^\n])```[“”\"']?(?=\s*(?:\n|$))", r"\1\n```", normalized)
    normalized = re.sub(r"(^|\n)[“”\"']+```([A-Za-z0-9_-]*)\s*(?=\n|$)", r"\1```\2", normalized)
    normalized = re.sub(r"(^|\n)```([A-Za-z0-9_-]*)[“”\"']+\s*(?=\n|$)", r"\1```\2", normalized)
    normalized = re.sub(r"([:：])\s*[“”\"']\s*(?=\n```[A-Za-z0-9_-]*\s*\n)", r"\1", normalized)
    return normalized


def _canonicalize_code_blocks(text: str) -> str:
    lines = text.split("\n")
    output: List[str] = []
    in_fence = False
    synthetic_fence = False
    pending_language_hint = ""

    def close_synthetic() -> None:
        nonlocal synthetic_fence
        if synthetic_fence:
            output.append("```")
            synthetic_fence = False

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        fence_candidate = _normalize_fence_token(stripped)

        if _is_fence_line(fence_candidate):
            if synthetic_fence:
                close_synthetic()
                pending_language_hint = ""
                if _is_fence_close(fence_candidate):
                    continue
                output.append(fence_candidate)
                in_fence = True
                continue

            if not in_fence:
                close_synthetic()
                pending_language_hint = ""
                output.append(fence_candidate if re.match(r"^```[A-Za-z0-9_-]+\s*$", fence_candidate) else "```")
                in_fence = True
                continue

            if _is_fence_close(fence_candidate):
                output.append("```")
                in_fence = False
                pending_language_hint = ""
                continue

            nested_hint = re.sub(r"^```", "", fence_candidate).strip()
            if nested_hint:
                output.append(nested_hint)
            continue

        if in_fence:
            output.append(line)
            continue

        if not stripped:
            close_synthetic()
            pending_language_hint = ""
            output.append("")
            continue

        language_hint = _normalize_language_hint(stripped)
        if language_hint and not synthetic_fence:
            pending_language_hint = language_hint
            continue

        inline_start = _find_inline_code_start(stripped)
        if inline_start > 0:
            plain_text = stripped[:inline_start].strip()
            code_text = stripped[inline_start:].strip()
            if plain_text:
                close_synthetic()
                if pending_language_hint:
                    output.append(pending_language_hint)
                    pending_language_hint = ""
                output.append(plain_text)

            if not synthetic_fence:
                code_lang = pending_language_hint or _guess_code_language(code_text)
                output.append(f"```{code_lang}")
                synthetic_fence = True
            pending_language_hint = ""
            for code_line in _split_compact_code_line(code_text):
                output.append(_normalize_code_hint_line(code_line))
            continue

        if _looks_like_code_line(stripped):
            if not synthetic_fence:
                code_lang = pending_language_hint or _guess_code_language(stripped)
                output.append(f"```{code_lang}")
                synthetic_fence = True
            pending_language_hint = ""
            for code_line in _split_compact_code_line(stripped):
                output.append(_normalize_code_hint_line(code_line))
            continue

        close_synthetic()
        if pending_language_hint:
            output.append(pending_language_hint)
            pending_language_hint = ""
        output.append(stripped)

    close_synthetic()
    if pending_language_hint:
        output.append(pending_language_hint)
    return "\n".join(output)


def _normalize_outside_fences(text: str, normalizer) -> str:
    lines = text.split("\n")
    output: List[str] = []
    plain_buffer: List[str] = []
    in_fence = False

    def flush_plain() -> None:
        if not plain_buffer:
            return
        segment = "\n".join(plain_buffer)
        plain_buffer.clear()
        normalized = normalizer(segment)
        if normalized:
            output.extend(normalized.split("\n"))

    for line in lines:
        stripped = line.strip()
        fence_candidate = _normalize_fence_token(stripped)
        if _is_fence_line(fence_candidate):
            flush_plain()
            output.append(fence_candidate)
            in_fence = not in_fence if _is_fence_close(fence_candidate) else True
            if _is_fence_close(fence_candidate):
                in_fence = False
            continue

        if in_fence:
            output.append(line)
            continue

        plain_buffer.append(line)

    flush_plain()
    return "\n".join(output)


def _normalize_plain_segment(segment: str, *, target: str) -> str:
    text = segment
    text = re.sub(r"\n?\s*[-*_]{3,}\s*\n?", "\n\n", text)
    text = re.sub(r"([^\n#])\s*(#{1,6}\s)", r"\1\n\2", text)
    text = re.sub(r"([。！？!?;；:：])\s*([1-9]\d?)\.(?=[^\d\s])", r"\1\n\2. ", text)
    text = re.sub(r"(^|\n)([1-9]\d?)\.(?=[^\d\s])", r"\1\2. ", text)
    text = re.sub(r"([。！？!?;；:：])\s*(\d+\.\s)", r"\1\n\2", text)
    text = re.sub(r"([。！？!?;；:：])\s*([-*]\s)", r"\1\n\2", text)
    text = re.sub(r"([一-龥A-Za-z0-9）)])-\s+", r"\1\n- ", text)
    text = re.sub(r"(^|\n)(#{1,6})\s*\n(?=\S)", r"\1\2 ", text)
    text = re.sub(r"(?m)^\s*[“”\"']+\s*$", "", text)

    # 编号列表的“纯命令项”直接下沉为命令行，避免出现“1.”独立成行。
    text = re.sub(
        rf"(?m)^\s*\d+\.\s+(\$?\s*(?:{_SHELL_COMMAND_PATTERN}|\.\/[^\s]+)(?=\s|$).*)$",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        rf"([:：。；;])\s*(\$?\s*(?:{_SHELL_COMMAND_PATTERN}|\.\/[^\s]+)(?=\s|$))",
        r"\1\n\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"([:：])\s*(?:cpp|c\+\+)?\s*(#include\s*<)", r"\1\ncpp \2", text, flags=re.IGNORECASE)
    text = re.sub(r"([:：。；;])\s*(int\s+main\s*\()", r"\1\n\2", text)
    text = _split_mixed_command_and_prose(text)

    if target == "answer":
        text = _normalize_answer_section_lines(text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip("\n")


def _normalize_answer_section_lines(text: str) -> str:
    lines = text.split("\n")
    output: List[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            output.append("")
            continue

        section_match = re.match(
            r"^\s*(?:\d+\.\s*)?(环境要求|安装步骤|最小示例|运行与验证|编译运行命令|编译与运行|运行命令)\s*[：:]?\s*(.*)$",
            line,
        )
        if section_match:
            output.append(f"## {section_match.group(1)}")
            tail = section_match.group(2).strip()
            if tail:
                output.append(tail)
            continue

        output.append(line)

    return "\n".join(output)


def _split_mixed_command_and_prose(text: str) -> str:
    output: List[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            output.append("")
            continue

        split_line = _split_mixed_command_prose_line(line)
        if split_line:
            output.append(split_line[0])
            output.append(split_line[1])
            continue

        output.append(line)

    return "\n".join(output)


def _split_mixed_command_prose_line(line: str) -> Optional[Tuple[str, str]]:
    stripped = (line or "").strip()
    if not stripped:
        return None

    match = _SHELL_LINE_RE.match(stripped)
    if not match:
        return None

    tail = (match.group("tail") or "").strip()
    if not tail or not re.search(r"[一-龥]", tail):
        return None

    prose_match = re.search(
        r"\s+((?:使用|然后|接着|再|并|并且|说明|示例|构建|运行|验证)[^。\n]*[：:])\s*$",
        tail,
    )
    if not prose_match:
        return None

    command_tail = tail[: prose_match.start()].rstrip()
    prose_text = prose_match.group(1).strip()

    cmd = (match.group("cmd") or "").strip()
    if not cmd:
        return None

    prefix = "$ " if stripped.startswith("$") else ""
    command_line = f"{prefix}{cmd} {command_tail}".strip()
    if not _looks_like_shell_command(command_line):
        return None

    return command_line, prose_text


def _normalize_fenced_blocks(text: str) -> str:
    lines = text.split("\n")
    output: List[str] = []
    in_fence = False
    fence_lang = ""
    fence_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        fence_candidate = _normalize_fence_token(stripped)

        if _is_fence_line(fence_candidate):
            if not in_fence:
                in_fence = True
                fence_lang = re.sub(r"^```", "", fence_candidate).strip().lower()
                fence_lines = []
                continue

            if _is_fence_close(fence_candidate):
                prose_lines, code_lines = _sanitize_fenced_block(fence_lines, fence_lang)
                output.extend(prose_lines)
                if code_lines:
                    output.append(f"```{fence_lang}" if fence_lang else "```")
                    output.extend(code_lines)
                    output.append("```")
                in_fence = False
                fence_lang = ""
                fence_lines = []
                continue

            fence_lines.append(fence_candidate)
            continue

        if in_fence:
            fence_lines.append(line.rstrip())
            continue

        output.append(line)

    if in_fence:
        prose_lines, code_lines = _sanitize_fenced_block(fence_lines, fence_lang)
        output.extend(prose_lines)
        if code_lines:
            output.append(f"```{fence_lang}" if fence_lang else "```")
            output.extend(code_lines)
            output.append("```")

    return "\n".join(output)


def _sanitize_fenced_block(lines: List[str], language: str) -> Tuple[List[str], List[str]]:
    if not lines:
        return [], []

    idx = 0
    prose_lines: List[str] = []
    while idx < len(lines):
        current = lines[idx].strip()
        if not current:
            idx += 1
            continue
        split_line = _split_mixed_command_prose_line(current)
        if split_line:
            prose_lines.append(split_line[1])
            lines[idx] = split_line[0]
            break
        if _is_code_line_for_language(current, language):
            break
        if _is_explanatory_line(current):
            prose_lines.append(current)
            idx += 1
            continue
        break

    code_lines = [line.rstrip() for line in lines[idx:]]
    while code_lines and not code_lines[0].strip():
        code_lines.pop(0)
    while code_lines and not code_lines[-1].strip():
        code_lines.pop()

    if not code_lines:
        return prose_lines, []

    if not any(_is_code_line_for_language(line.strip(), language) for line in code_lines if line.strip()):
        prose_lines.extend(line for line in code_lines if line.strip())
        return prose_lines, []

    return prose_lines, code_lines


def _is_code_line_for_language(line: str, language: str) -> bool:
    stripped = (line or "").strip()
    if not stripped:
        return True

    lang = (language or "").strip().lower()

    if lang in {"bash", "shell", "sh", "zsh"}:
        if stripped.startswith("#"):
            return True
        return _looks_like_shell_command(stripped)

    if lang == "cmake":
        if stripped.startswith("#"):
            return True
        return _CMAKE_LINE_RE.search(stripped) is not None or bool(re.match(r"^[A-Za-z_]+\s*\(", stripped))

    if lang in {"cpp", "c++", "cc", "cxx", "hpp", "h"}:
        if re.match(r"^\s*(//|/\*|\*|\*/)", stripped):
            return True
        return _looks_like_code_line(stripped)

    return _looks_like_code_line(stripped)


def _is_explanatory_line(line: str) -> bool:
    stripped = (line or "").strip()
    if not stripped:
        return False

    if _looks_like_code_line(stripped):
        return False

    if re.search(r"[一-龥]", stripped):
        if re.search(r"[：:。；;!?！？]$", stripped):
            return True
        if re.search(r"(说明|步骤|示例|构建|运行|验证|如下|例如|命令)", stripped):
            return True

    return False


def _drop_empty_fences(text: str) -> str:
    return re.sub(r"(?ms)^```[A-Za-z0-9_-]*\n\s*```[ \t]*\n?", "", text)


def _cleanup_whitespace(text: str) -> str:
    normalized = re.sub(r"[ \t]+\n", "\n", text)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized


def _normalize_fence_token(line: str) -> str:
    return re.sub(r"^[“”\"']+|[“”\"']+$", "", line.strip())


def _is_fence_line(line: str) -> bool:
    return re.match(r"^```[A-Za-z0-9_-]*\s*$", line) is not None


def _is_fence_close(line: str) -> bool:
    return re.match(r"^```\s*$", line) is not None


def _normalize_language_hint(line: str) -> str:
    normalized = (line or "").strip().lower()
    normalized = re.sub(r"^\s*[-*+]\s*", "", normalized)
    normalized = re.sub(r"^`+|`+$", "", normalized)
    normalized = re.sub(r"[：:]\s*$", "", normalized)
    normalized = re.sub(r"^language\s*[：:]\s*", "", normalized)
    normalized = normalized.strip()
    return _LANG_HINTS.get(normalized, "")


def _looks_like_shell_command(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False

    if re.search(r"[一-龥]", stripped):
        return False

    if re.search(r"[：:]\s*$", stripped):
        return False

    match = _SHELL_LINE_RE.match(stripped)
    if not match:
        return False

    cmd = match.group("cmd").lower()
    tail = (match.group("tail") or "").strip()
    if cmd.startswith("./"):
        return True

    if not tail:
        return cmd in {"make", "cmake", "ls", "pwd"}

    if not re.match(r"^[A-Za-z0-9_./:@=-]", tail):
        return False

    if re.match(r"^\d+(?:\.\d+)*\+?$", tail):
        return False

    # 避免把“GCC 11+/Clang 14+”这类环境要求误判成命令。
    if cmd in _COMPILER_COMMANDS:
        compiler_tail_ok = re.search(
            r"(?:^|\s)(-[-\w=:.+]+|\S+\.(?:c|cc|cpp|cxx|h|hpp|o|so|a))(?:\s|$)",
            tail,
            flags=re.IGNORECASE,
        )
        if not compiler_tail_ok:
            return False

    return True


def _looks_like_code_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False

    has_cn = re.search(r"[一-龥]", stripped) is not None

    if re.search(r"^(?:cpp|c\+\+)?\s*#include\s*<", stripped, flags=re.IGNORECASE):
        return True
    if re.search(r"^(template\s*<|class\s+\w+|struct\s+\w+|namespace\s+\w+)", stripped):
        return True
    if _CMAKE_LINE_RE.search(stripped):
        return True
    if _looks_like_shell_command(stripped):
        return True
    if re.search(r"^\s*(int|void|bool|auto|size_t)\s+\w+.*[;{]\s*$", stripped):
        return True
    if re.search(r"\bco_(return|await|yield)\b", stripped) and not has_cn:
        return True
    if re.search(r"^\s*return\b[^一-龥]*[;}]\s*$", stripped) and not has_cn:
        return True
    if re.search(r"->\s*\w+\(", stripped) and not has_cn:
        return True
    if re.search(r"^[{}]+[;,]?$", stripped):
        return True
    if re.search(r"^[)\]}]+[;,]?$", stripped):
        return True
    if stripped.endswith(";") and not has_cn and len(stripped) >= 12:
        return True
    if re.search(r"[{}]", stripped) and re.search(r"\(", stripped) and not has_cn:
        return True

    return False


def _find_inline_code_start(line: str) -> int:
    if not line:
        return -1

    if _looks_like_code_line(line):
        return -1

    patterns = [
        re.compile(r"(?:cpp|c\+\+)?\s*#include\s*<", re.IGNORECASE),
        re.compile(r"\bint\s+main\s*\("),
        re.compile(r"\bcmake_minimum_required\s*\(", re.IGNORECASE),
        re.compile(r"\bproject\s*\(", re.IGNORECASE),
        re.compile(rf"\$?\s*(?:{_SHELL_COMMAND_PATTERN}|\.\/[^\s]+)(?=\s|$)", re.IGNORECASE),
    ]

    starts: List[int] = []
    for pattern in patterns:
        for match in pattern.finditer(line):
            if match.start() <= 0:
                continue
            candidate = line[match.start():].strip()
            if pattern.pattern.startswith(r"\$?") and not _looks_like_shell_command(candidate):
                continue
            starts.append(match.start())

    return min(starts) if starts else -1


def _guess_code_language(line: str) -> str:
    stripped = (line or "").strip()
    if not stripped:
        return "text"

    if re.search(r"^(?:cpp|c\+\+)?\s*#include\s*<", stripped, flags=re.IGNORECASE) or re.search(r"\bint\s+main\s*\(", stripped):
        return "cpp"
    if _CMAKE_LINE_RE.search(stripped):
        return "cmake"
    if _looks_like_shell_command(stripped):
        return "bash"
    return "text"


def _normalize_code_hint_line(line: str) -> str:
    cleaned = re.sub(r"^(?:cpp|c\+\+)\s*(?=#include\b)", "", line, flags=re.IGNORECASE)
    cleaned = re.sub(
        rf"^(?:bash|shell)\s*(?=\$?\s*(?:{_SHELL_COMMAND_PATTERN}|\.\/[^\s]+)(?=\s|$))",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned


def _split_compact_code_line(line: str) -> List[str]:
    stripped = line.strip()
    if not stripped:
        return [""]

    if _looks_like_shell_command(stripped):
        normalized = stripped
        normalized = re.sub(r"(\.git)(?=cd\s+)", r"\1\n", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(\$\([^)]+\))(?=(?:sudo\b|make\b|cmake\b|cd\b|git\b|\.\/|nc\b|telnet\b))", r"\1\n", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(\S)(?=sudo\s+make\b)", r"\1\n", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(\bcd\s+\S*?)(cmake\s+\.\.)", r"\1\n\2", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"&&\s*(?=\S)", "&&\n", normalized)
        return [part.strip() for part in normalized.split("\n") if part.strip()]

    normalized = stripped
    normalized = re.sub(
        r"(#include\s*<[^>]+>)\s*(?=(?:#include|int\s+main\s*\(|template\s*<|class\s+\w+|struct\s+\w+))",
        r"\1\n",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"([;{}])\s*(?=(?:#include|int\s+main\s*\(|template\s*<|class\s+\w+|struct\s+\w+|return\b))",
        r"\1\n",
        normalized,
    )
    return [part.strip() for part in normalized.split("\n") if part.strip()]
