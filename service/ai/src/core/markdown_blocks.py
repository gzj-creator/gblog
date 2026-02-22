import re
from typing import Any, Dict, List


_FENCE_RE = re.compile(r"^```([A-Za-z0-9_-]*)\s*$")
_HR_RE = re.compile(r"^([-*_])\1{2,}$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")
_OL_RE = re.compile(r"^[✅☑️✔️🔥🌟🧠🔧⚙️🛠️📈📌]?\s*(\d+)\.\s+(.+)$", re.UNICODE)
_UL_RE = re.compile(r"^[-*]\s+(.+)$")


def markdown_to_blocks(markdown_text: str) -> List[Dict[str, Any]]:
    """Convert normalized markdown text into a structured block list."""
    text = str(markdown_text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return []

    lines = text.split("\n")
    blocks: List[Dict[str, Any]] = []

    paragraph_lines: List[str] = []
    quote_lines: List[str] = []
    list_items: List[str] = []
    list_ordered = False
    list_start = 1
    expected_ol = None

    in_code = False
    code_lang = "text"
    code_lines: List[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if not paragraph_lines:
            return
        text_value = "\n".join(paragraph_lines).strip()
        if text_value:
            blocks.append({"type": "paragraph", "text": text_value})
        paragraph_lines = []

    def flush_quote() -> None:
        nonlocal quote_lines
        if not quote_lines:
            return
        text_value = "\n".join(quote_lines).strip()
        if text_value:
            blocks.append({"type": "blockquote", "text": text_value})
        quote_lines = []

    def flush_list() -> None:
        nonlocal list_items, list_ordered, list_start, expected_ol
        if not list_items:
            return
        block: Dict[str, Any] = {
            "type": "list",
            "ordered": list_ordered,
            "items": list_items[:],
        }
        if list_ordered:
            block["start"] = list_start
        blocks.append(block)
        list_items = []
        list_ordered = False
        list_start = 1
        expected_ol = None

    def flush_code() -> None:
        nonlocal code_lines, code_lang
        text_value = "\n".join(code_lines).strip("\n")
        if text_value:
            blocks.append({"type": "code", "language": code_lang or "text", "code": text_value})
        code_lines = []
        code_lang = "text"

    def flush_all_non_code() -> None:
        flush_paragraph()
        flush_quote()
        flush_list()

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        fence_match = _FENCE_RE.match(stripped)
        if fence_match:
            if not in_code:
                flush_all_non_code()
                in_code = True
                code_lang = (fence_match.group(1) or "text").strip().lower() or "text"
                code_lines = []
                continue

            if stripped == "```":
                flush_code()
                in_code = False
                continue

            # Fence inside code block, keep literal.
            code_lines.append(line)
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            flush_all_non_code()
            continue

        if _HR_RE.match(stripped):
            flush_all_non_code()
            blocks.append({"type": "hr"})
            continue

        heading_match = _HEADING_RE.match(stripped)
        if heading_match:
            flush_all_non_code()
            blocks.append({
                "type": "heading",
                "level": len(heading_match.group(1)),
                "text": heading_match.group(2).strip(),
            })
            continue

        quote_match = _BLOCKQUOTE_RE.match(stripped)
        if quote_match:
            flush_paragraph()
            flush_list()
            quote_lines.append(quote_match.group(1).strip())
            continue

        ol_match = _OL_RE.match(stripped)
        if ol_match:
            flush_paragraph()
            flush_quote()
            current_number = int(ol_match.group(1))
            item_text = ol_match.group(2).strip()
            if not list_items or not list_ordered:
                flush_list()
                list_ordered = True
                list_start = current_number
                expected_ol = current_number + 1
            else:
                if expected_ol is not None and current_number not in {expected_ol, 1}:
                    flush_list()
                    list_ordered = True
                    list_start = current_number
                    expected_ol = current_number + 1
                else:
                    expected_ol = (expected_ol or current_number) + 1

            list_items.append(item_text)
            continue

        ul_match = _UL_RE.match(stripped)
        if ul_match:
            flush_paragraph()
            flush_quote()
            if not list_items or list_ordered:
                flush_list()
                list_ordered = False
            list_items.append(ul_match.group(1).strip())
            continue

        flush_quote()
        flush_list()
        paragraph_lines.append(stripped)

    if in_code:
        flush_code()
    else:
        flush_all_non_code()

    return blocks
