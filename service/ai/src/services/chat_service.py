from collections import OrderedDict
import re
from typing import Any, AsyncGenerator, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import settings
from src.core.vector_store import VectorStoreManager
from src.services.rag_service import RAGService, SYSTEM_PROMPT
from src.utils.exceptions import ChatServiceError
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_SESSIONS = 100
MAX_HISTORY_ROUNDS = 20
STREAM_BLOCK_SUFFIX = "\n\n"
STREAM_EMIT_MIN_CHARS = 16
STREAM_EMIT_MAX_CHARS = 120


class ChatService:
    """对话服务（含会话记忆）"""

    def __init__(self, vector_store: VectorStoreManager):
        self._vector_store = vector_store
        self._rag = RAGService(vector_store)
        self._llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=settings.TEMPERATURE,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
        )
        # session_id -> List[{"role": "user"|"assistant", "content": str}]
        self._histories: OrderedDict[str, List[dict]] = OrderedDict()

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------
    def chat(self, message: str, session_id: str = "default") -> Dict[str, Any]:
        """带会话记忆的对话"""
        try:
            docs = self._rag.retrieve(message, k=4)
            sources = _extract_sources(docs)
            messages = self._build_messages(message, docs, session_id)

            response = self._llm.invoke(messages)
            answer = _normalize_answer_text(_extract_message_text(response))
            if not answer.strip():
                answer = "抱歉，模型返回了空内容，请稍后重试。"

            self._append_history(session_id, message, answer)

            return {
                "success": True,
                "response": answer,
                "sources": sources,
                "session_id": session_id,
            }
        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise ChatServiceError(f"Chat failed: {e}")

    async def chat_stream(
        self, message: str, session_id: str = "default"
    ) -> AsyncGenerator[dict, None]:
        """带会话记忆的流式对话"""
        try:
            docs = self._rag.retrieve(message, k=4)
            sources = _extract_sources(docs)
            messages = self._build_messages(message, docs, session_id)

            raw_answer_parts: List[str] = []
            stream_buffer = ""
            emitted_any = False

            async for chunk in self._llm.astream(messages):
                text = _extract_message_text(chunk)
                if text:
                    raw_answer_parts.append(text)
                    stream_buffer += _sanitize_stream_fragment(text)
                    while True:
                        emit_piece, stream_buffer = _pop_stream_emit_piece(stream_buffer)
                        if not emit_piece:
                            break
                        emitted_any = True
                        yield {"content": emit_piece}

            raw_answer = "".join(raw_answer_parts)
            if not raw_answer.strip():
                # 部分 OpenAI 兼容实现可能在 stream 中不给 content，兜底一次同步调用。
                fallback = self._llm.invoke(messages)
                raw_answer = _extract_message_text(fallback).strip()
                normalized_answer = _normalize_answer_text(raw_answer)
                if not normalized_answer:
                    normalized_answer = "抱歉，模型返回了空内容，请稍后重试。"
                for block in _split_answer_blocks(normalized_answer):
                    yield {"content": block}
                answer = normalized_answer
            else:
                tail_piece = _finalize_stream_tail(stream_buffer)
                if tail_piece:
                    emitted_any = True
                    yield {"content": tail_piece}

                normalized_answer = _normalize_answer_text(raw_answer)
                if not normalized_answer:
                    normalized_answer = "抱歉，模型返回了空内容，请稍后重试。"

                # 防止清洗后无可显示内容时流为空，兜底补发标准分块文本。
                if not emitted_any:
                    for block in _split_answer_blocks(normalized_answer):
                        yield {"content": block}
                answer = normalized_answer

            self._append_history(session_id, message, answer)

            yield {"done": True, "sources": sources}
        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield {"error": str(e)}

    def query(self, message: str) -> Dict[str, Any]:
        """无记忆的单次问答"""
        try:
            docs = self._rag.retrieve(message, k=4)
            if not docs:
                return {
                    "success": True,
                    "response": "抱歉，我在文档中没有找到相关信息。请尝试换个方式提问。",
                    "sources": [],
                }
            answer = _normalize_answer_text(self._rag.generate(message, docs))
            sources = _extract_sources(docs)
            return {"success": True, "response": answer, "sources": sources}
        except Exception as e:
            logger.error(f"Query error: {e}")
            raise ChatServiceError(f"Query failed: {e}")

    def clear_session(self, session_id: str) -> None:
        if session_id in self._histories:
            del self._histories[session_id]
            logger.info(f"Cleared memory for session: {session_id}")

    def get_active_sessions(self) -> List[str]:
        return list(self._histories.keys())

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _build_messages(self, message: str, docs: list, session_id: str) -> list:
        """构建 LLM 消息列表：system + context + history + user"""
        context = "\n\n".join(doc.page_content for doc in docs)

        system_content = f"""{SYSTEM_PROMPT}

请基于以下文档内容回答用户问题：

{context}"""

        messages = [SystemMessage(content=system_content)]

        # 追加历史对话
        history = self._histories.get(session_id, [])
        for entry in history:
            if entry["role"] == "user":
                messages.append(HumanMessage(content=entry["content"]))
            else:
                messages.append(AIMessage(content=entry["content"]))

        messages.append(HumanMessage(content=message))
        return messages

    def _append_history(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        """追加对话记录，维护 LRU 淘汰和轮数限制"""
        if session_id in self._histories:
            # 移到末尾（LRU）
            self._histories.move_to_end(session_id)
        else:
            # 淘汰最旧的 session
            if len(self._histories) >= MAX_SESSIONS:
                evicted = next(iter(self._histories))
                del self._histories[evicted]
                logger.info(f"Evicted oldest session: {evicted}")
            self._histories[session_id] = []

        history = self._histories[session_id]
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": assistant_msg})

        # 保留最近 N 轮（每轮 2 条）
        max_entries = MAX_HISTORY_ROUNDS * 2
        if len(history) > max_entries:
            self._histories[session_id] = history[-max_entries:]


def _extract_sources(documents: list) -> List[Dict[str, str]]:
    """提取去重后的源文档信息"""
    sources: List[Dict[str, str]] = []
    seen: set = set()
    for doc in documents:
        meta = doc.metadata
        key = f"{meta.get('project', 'unknown')}:{meta.get('source', 'unknown')}"
        if key not in seen:
            sources.append({
                "project": meta.get("project", "unknown"),
                "file": meta.get("source", "unknown"),
                "file_name": meta.get("file_name", "unknown"),
            })
            seen.add(key)
    return sources


def _extract_message_text(message: Any) -> str:
    """兼容不同 OpenAI 兼容服务的消息结构，尽可能提取文本内容。"""
    if message is None:
        return ""

    content = getattr(message, "content", message)
    additional = getattr(message, "additional_kwargs", {}) or {}
    return (
        _coerce_text(content)
        or _coerce_text(additional.get("content"))
        or _coerce_text(additional.get("reasoning_content"))
        or ""
    )


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            piece = _coerce_text(item)
            if piece:
                parts.append(piece)
        return "".join(parts)

    if isinstance(value, dict):
        for key in ("text", "content", "reasoning_content"):
            piece = _coerce_text(value.get(key))
            if piece:
                return piece
        return ""

    return str(value)


def _normalize_answer_text(raw: str) -> str:
    """清洗模型输出中的装饰符号，并重排为结构化分块文本。"""
    if not raw:
        return ""

    text = str(raw).replace("\r\n", "\n").replace("\r", "\n")
    text = _strip_decorative_symbols(text)
    text = _insert_structural_breaks(text)
    text = re.sub(r"(?i)\bcpp\s*(?=#include\b)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    if not text:
        return ""

    blocks: List[str] = []
    paragraph_lines: List[str] = []
    code_lines: List[str] = []
    in_code_block = False
    synthetic_code_block = False

    def flush_paragraph() -> None:
        if paragraph_lines:
            blocks.append(" ".join(paragraph_lines).strip())
            paragraph_lines.clear()

    def flush_code() -> None:
        if code_lines:
            blocks.append("\n".join(code_lines).strip())
            code_lines.clear()

    for raw_line in text.split("\n"):
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                code_lines.append(stripped)
                flush_code()
                in_code_block = False
                synthetic_code_block = False
            else:
                flush_paragraph()
                in_code_block = True
                synthetic_code_block = False
                code_lines = [stripped]
            continue

        if in_code_block and not synthetic_code_block:
            code_lines.append(line)
            continue

        if in_code_block and synthetic_code_block:
            if not stripped or _looks_like_code_line(stripped):
                if stripped:
                    code_lines.append(_normalize_code_hint_line(stripped))
                else:
                    code_lines.append("")
                continue

            code_lines.append("```")
            flush_code()
            in_code_block = False
            synthetic_code_block = False

        inline_code_start = _find_inline_code_start(stripped)
        if inline_code_start > 0:
            plain_text = stripped[:inline_code_start].strip()
            candidate_code = stripped[inline_code_start:].strip()
            if plain_text:
                paragraph_lines.append(plain_text)
                flush_paragraph()
            stripped = candidate_code

        if not stripped:
            flush_paragraph()
            continue

        if _looks_like_code_line(stripped):
            flush_paragraph()
            in_code_block = True
            synthetic_code_block = True
            code_lines = [f"```{_guess_code_language(stripped)}", _normalize_code_hint_line(stripped)]
            continue

        is_header = re.match(r"^#{1,6}\s+\S", stripped) is not None
        is_ol = re.match(r"^\d+\.\s+\S", stripped) is not None
        is_ul = re.match(r"^[-*]\s+\S", stripped) is not None
        if is_ol or is_ul:
            flush_paragraph()
            blocks.append(stripped)
            continue

        if is_header:
            flush_paragraph()
            blocks.append(stripped)
            continue

        paragraph_lines.append(stripped)

    if in_code_block:
        if not code_lines or code_lines[-1] != "```":
            code_lines.append("```")
        flush_code()

    flush_paragraph()
    blocks = [block for block in blocks if block]
    return "\n\n".join(blocks).strip()


def _strip_decorative_symbols(text: str) -> str:
    # 去掉常见装饰 emoji / 图标符号，保留中文标点与 Markdown 基础结构。
    decorative = (
        "[✅☑✔✳✴★☆⭐🔥🌟✨💡🔧⚙🛠📈📌📍🚀🎯▶►■□▪▫◆◇•·]"
    )
    stripped = re.sub(decorative, "", text)
    stripped = re.sub(r"\s*---+\s*", "\n", stripped)
    return stripped


def _insert_structural_breaks(text: str) -> str:
    # 标题、编号、列表粘在同一行时，尽量拆成独立块。
    normalized = text
    normalized = re.sub(r"([^\n#])\s*(#{1,6}\s)", r"\1\n\2", normalized)
    normalized = re.sub(r"([^\n#])\s+(\d+\.\s)", r"\1\n\2", normalized)
    normalized = re.sub(r"([。！？!?;；:：])\s*(\d+\.\s)", r"\1\n\2", normalized)
    normalized = re.sub(r"([。！？!?;；:：])\s*([-*]\s)", r"\1\n\2", normalized)
    normalized = re.sub(r"([一-龥A-Za-z0-9）)])-\s+", r"\1\n- ", normalized)
    normalized = re.sub(r"(^|\n)(#{1,6})\s*\n(?=\S)", r"\1\2 ", normalized)
    normalized = re.sub(r"([^\n])\s*((?:环境要求|安装步骤|最小示例|运行与验证)\s*[：:])", r"\1\n\2", normalized)
    normalized = re.sub(r"(?m)^\s*(环境要求|安装步骤|最小示例|运行与验证)\s*[：:]\s*", r"## \1\n", normalized)
    normalized = re.sub(r"([:：])\s*(?:cpp|c\+\+)?\s*(#include\s*<)", r"\1\ncpp \2", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"([:：。；;])\s*(int\s+main\s*\()", r"\1\n\2", normalized)
    normalized = re.sub(
        r"([>;}])\s*(?=(?:#include|int\s+main\s*\(|template\s*<|class\s+\w+|struct\s+\w+))",
        r"\1\n",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"([:：。；;])\s*(\$?\s*(?:git|docker|kubectl|curl|wget|npm|pnpm|yarn|pip|python3?|cmake)\b)",
        r"\1\n\2",
        normalized,
        flags=re.IGNORECASE,
    )
    return normalized


def _looks_like_code_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False

    has_cn = re.search(r"[一-龥]", stripped) is not None

    if re.search(r"^(?:cpp|c\+\+)?\s*#include\s*<", stripped, flags=re.IGNORECASE):
        return True
    if re.search(r"^\s*(template\s*<|class\s+\w+|struct\s+\w+|namespace\s+\w+)", stripped):
        return True
    if re.search(r"^\$?\s*(git|docker|kubectl|curl|wget|npm|pnpm|yarn|pip|python3?|cmake)\b", stripped, flags=re.IGNORECASE):
        return True
    if re.search(r"^(cmake_minimum_required|project|add_executable|add_library|target_link_libraries)\s*\(", stripped, flags=re.IGNORECASE):
        return True
    if re.search(r"^\s*(int|void|bool|auto|size_t)\s+\w+.*[;{]\s*$", stripped):
        return True
    if re.search(r"\bco_(return|await|yield)\b", stripped) and not has_cn:
        return True
    if re.search(r"->\s*\w+\(", stripped) and not has_cn:
        return True
    if stripped.endswith(";") and not has_cn and len(stripped) >= 12:
        return True
    if re.search(r"[{}]", stripped) and re.search(r"\(", stripped) and not has_cn:
        return True

    return False


def _normalize_code_hint_line(line: str) -> str:
    cleaned = re.sub(r"^(?:cpp|c\+\+)\s*(?=#include\b)", "", line, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"^(?:bash|shell)\s*(?=\$?\s*(?:git|docker|kubectl|curl|wget|npm|pnpm|yarn|pip|python3?|cmake)\b)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned


def _find_inline_code_start(line: str) -> int:
    if not line:
        return -1

    if re.search(r"^(?:cpp|c\+\+)?\s*#include\s*<", line, flags=re.IGNORECASE):
        return -1
    if re.search(r"^(template\s*<|class\s+\w+|struct\s+\w+|namespace\s+\w+)", line):
        return -1
    if re.search(r"^\$?\s*(git|docker|kubectl|curl|wget|npm|pnpm|yarn|pip|python3?|cmake)\b", line, flags=re.IGNORECASE):
        return -1
    if re.search(r"^(cmake_minimum_required|project|add_executable|add_library|target_link_libraries)\s*\(", line, flags=re.IGNORECASE):
        return -1
    if re.search(r"^\s*(int|void|bool|auto|size_t)\s+\w+.*[;{]?\s*$", line):
        return -1

    patterns = (
        r"(?:cpp|c\+\+)?\s*#include\s*<",
        r"\bint\s+main\s*\(",
        r"\bcmake_minimum_required\s*\(",
        r"\bproject\s*\(",
        r"\$?\s*(?:git|docker|kubectl|curl|wget|npm|pnpm|yarn|pip|python3?|cmake)\b",
    )

    starts: List[int] = []
    for pattern in patterns:
        match = re.search(pattern, line, flags=re.IGNORECASE)
        if not match:
            continue
        if match.start() <= 0:
            continue
        starts.append(match.start())

    return min(starts) if starts else -1


def _guess_code_language(line: str) -> str:
    stripped = (line or "").strip()
    if not stripped:
        return "text"

    if re.search(r"^(?:cpp|c\+\+)?\s*#include\s*<", stripped, flags=re.IGNORECASE) or re.search(r"\bint\s+main\s*\(", stripped):
        return "cpp"
    if re.search(r"^(cmake_minimum_required|project|add_executable|add_library|target_link_libraries)\s*\(", stripped, flags=re.IGNORECASE):
        return "cmake"
    if re.search(r"^\$?\s*(git|docker|kubectl|curl|wget|npm|pnpm|yarn|pip|python3?|cmake)\b", stripped, flags=re.IGNORECASE):
        return "bash"

    return "text"


def _split_answer_blocks(answer: str) -> List[str]:
    blocks = [block.strip() for block in answer.split("\n\n") if block.strip()]
    if not blocks:
        return []

    chunks: List[str] = []
    for index, block in enumerate(blocks):
        suffix = STREAM_BLOCK_SUFFIX if index + 1 < len(blocks) else ""
        chunks.append(f"{block}{suffix}")
    return chunks


def _sanitize_stream_fragment(fragment: str) -> str:
    if not fragment:
        return ""

    text = str(fragment).replace("\r\n", "\n").replace("\r", "\n")
    text = _strip_decorative_symbols(text)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _pop_stream_emit_piece(buffer: str) -> tuple[str, str]:
    if not buffer:
        return "", ""

    # 优先在句子边界输出，增强“逐步出现”的体感。
    for idx, ch in enumerate(buffer):
        if idx + 1 < STREAM_EMIT_MIN_CHARS:
            continue
        if ch in "\n。！？!?；;":
            emit = buffer[: idx + 1].strip()
            rest = buffer[idx + 1 :]
            return emit, rest

    # 太长则强制切一段，避免前端长时间无更新。
    if len(buffer) >= STREAM_EMIT_MAX_CHARS:
        cut = buffer.rfind(" ", 0, STREAM_EMIT_MAX_CHARS)
        if cut <= 0:
            cut = STREAM_EMIT_MAX_CHARS
        emit = buffer[:cut].strip()
        rest = buffer[cut:]
        return emit, rest

    return "", buffer


def _finalize_stream_tail(buffer: str) -> str:
    if not buffer:
        return ""
    return buffer.strip()
