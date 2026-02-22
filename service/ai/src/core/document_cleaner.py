import re

from src.core.markdown_normalizer import normalize_markdown_content

_ZERO_WIDTH_PATTERN = re.compile(r"[\u200b-\u200f\ufeff]+")


def clean_document_content(content: str, file_type: str) -> str:
    """在分块前清洗文档内容。"""
    if not content:
        return ""

    text = str(content).replace("\r\n", "\n").replace("\r", "\n")
    text = _ZERO_WIDTH_PATTERN.sub("", text)

    if file_type == "markdown":
        text = _clean_markdown_text(text)
    else:
        # 代码文件仅做轻量规范化，避免影响语义。
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{4,}", "\n\n\n", text)

    return text.strip()


def _clean_markdown_text(text: str) -> str:
    return normalize_markdown_content(text, target="index", strip_decorative=True)
