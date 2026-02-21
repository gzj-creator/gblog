import re


_DECORATIVE_SYMBOLS_PATTERN = re.compile(
    r"[✅☑✔✳✴★☆⭐🔥🌟✨💡🔧⚙🛠📈📌📍🚀🎯▶►■□▪▫◆◇•·]+"
)
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
    # 去掉常见的装饰符号（通常无语义价值，影响分块与检索）。
    text = _DECORATIVE_SYMBOLS_PATTERN.sub("", text)

    # 把过长分隔线处理为空行，避免污染 chunk。
    text = re.sub(r"\n?\s*-{3,}\s*\n?", "\n\n", text)
    text = re.sub(r"-{3,}", "\n", text)

    # 修复结构粘连：标题、编号、列表紧贴前文。
    text = re.sub(r"([^\n])\s*(#{1,6}\s)", r"\1\n\2", text)
    text = re.sub(r"([^\n#])\s+(\d+\.\s)", r"\1\n\2", text)
    text = re.sub(r"([。！？!?;；:：])\s*(\d+\.\s)", r"\1\n\2", text)
    text = re.sub(r"([。！？!?;；:：])\s*([-*]\s)", r"\1\n\2", text)
    text = re.sub(r"([一-龥A-Za-z0-9）)])-\s+", r"\1\n- ", text)
    text = re.sub(r"(^|\n)(#{1,6})\s*\n(?=\S)", r"\1\2 ", text)

    # 统一空白。
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text
