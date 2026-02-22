from collections import OrderedDict
import re
from typing import Any, AsyncGenerator, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import settings
from src.core.markdown_blocks import markdown_to_blocks
from src.core.markdown_normalizer import normalize_markdown_content
from src.core.vector_store import VectorStoreManager
from src.services.rag_service import RAGService, SYSTEM_PROMPT
from src.utils.exceptions import ChatServiceError
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_SESSIONS = 100
MAX_HISTORY_ROUNDS = 20
STREAM_EMIT_MIN_CHARS = 16
STREAM_EMIT_MAX_CHARS = 120

_FORBIDDEN_SCHEDULER_APIS = (
    re.compile(r"\b(?:IoContext|IOContext)\s*::\s*GetInstance\s*\(\s*\)", re.IGNORECASE),
    re.compile(r"\bioContext\b"),
    re.compile(r"\bIoContext\b"),
)


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
            blocks = _build_answer_blocks(answer)

            self._append_history(session_id, message, answer)

            return {
                "success": True,
                "response": answer,
                "blocks": blocks,
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
            streamed_parts: List[str] = []
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
                        streamed_parts.append(emit_piece)
                        partial_text, partial_blocks = _build_stream_preview(streamed_parts)
                        if partial_text:
                            yield {"replace": partial_text, "blocks": partial_blocks, "partial": True}
                        else:
                            yield {"content": emit_piece}

            raw_answer = "".join(raw_answer_parts)
            if not raw_answer.strip():
                # 部分 OpenAI 兼容实现可能在 stream 中不给 content，兜底一次同步调用。
                fallback = self._llm.invoke(messages)
                raw_answer = _extract_message_text(fallback).strip()
                normalized_answer = _normalize_answer_text(raw_answer)
                if not normalized_answer:
                    normalized_answer = "抱歉，模型返回了空内容，请稍后重试。"
                answer_blocks = _build_answer_blocks(normalized_answer)
                yield {"replace": normalized_answer, "blocks": answer_blocks}
                answer = normalized_answer
            else:
                tail_piece = _finalize_stream_tail(stream_buffer)
                if tail_piece:
                    emitted_any = True
                    streamed_parts.append(tail_piece)
                    partial_text, partial_blocks = _build_stream_preview(streamed_parts)
                    if partial_text:
                        yield {"replace": partial_text, "blocks": partial_blocks, "partial": True}
                    else:
                        yield {"content": tail_piece}

                normalized_answer = _normalize_answer_text(raw_answer)
                if not normalized_answer:
                    normalized_answer = "抱歉，模型返回了空内容，请稍后重试。"
                answer_blocks = _build_answer_blocks(normalized_answer)

                # 防止清洗后无可显示内容时流为空，兜底补发标准分块文本。
                if not emitted_any:
                    yield {"replace": normalized_answer, "blocks": answer_blocks}
                else:
                    # 统一规则最终落地：始终以规范化后的全文覆盖流式中间态。
                    yield {"replace": normalized_answer, "blocks": answer_blocks}
                answer = normalized_answer

            self._append_history(session_id, message, answer)

            yield {"done": True, "sources": sources, "blocks": answer_blocks}
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
                    "blocks": _build_answer_blocks("抱歉，我在文档中没有找到相关信息。请尝试换个方式提问。"),
                    "sources": [],
                }
            answer = _normalize_answer_text(self._rag.generate(message, docs))
            blocks = _build_answer_blocks(answer)
            sources = _extract_sources(docs)
            return {"success": True, "response": answer, "blocks": blocks, "sources": sources}
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
    """统一规范模型输出，保证与入库文档一致的 markdown 规则。"""
    if not raw:
        return ""

    normalized = normalize_markdown_content(str(raw), target="answer", strip_decorative=True)
    return _enforce_scheduler_api_consistency(normalized)


def _enforce_scheduler_api_consistency(text: str) -> str:
    if not text:
        return ""

    if not any(pattern.search(text) for pattern in _FORBIDDEN_SCHEDULER_APIS):
        return text

    fixed = text
    fixed = re.sub(
        r"\b(?:IoContext|IOContext)\s*::\s*GetInstance\s*\(\s*\)",
        "runtime.getNextIOScheduler()",
        fixed,
        flags=re.IGNORECASE,
    )
    fixed = re.sub(r"\bioContext\b", "ioScheduler", fixed)
    fixed = re.sub(r"\bIoContext\b", "IOScheduler", fixed)

    note = (
        "说明：Galay 当前没有 `IoContext` 单例 API，请使用 `Runtime` 获取调度器："
        "`runtime.getNextIOScheduler()` / `runtime.getNextComputeScheduler()`。"
    )
    if note not in fixed:
        fixed = f"{fixed.rstrip()}\n\n{note}"

    logger.warning("Detected forbidden IoContext API in model output, auto-corrected")
    return fixed


def _build_answer_blocks(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []
    try:
        return markdown_to_blocks(text)
    except Exception as exc:
        logger.warning(f"build markdown blocks failed: {exc}")
        return [{"type": "paragraph", "text": text}]


def _build_stream_preview(streamed_parts: List[str]) -> tuple[str, List[Dict[str, Any]]]:
    if not streamed_parts:
        return "", []
    preview_raw = "".join(streamed_parts).strip()
    if not preview_raw:
        return "", []
    preview_text = _normalize_answer_text(preview_raw)
    if not preview_text:
        return "", []
    return preview_text, _build_answer_blocks(preview_text)


def _strip_decorative_symbols(text: str) -> str:
    # 去掉常见装饰 emoji / 图标符号，保留中文标点与 Markdown 基础结构。
    decorative = (
        "[✅☑✔✳✴★☆⭐🔥🌟✨💡🔧⚙🛠📈📌📍🚀🎯▶►■□▪▫◆◇•·]"
    )
    stripped = re.sub(decorative, "", text)
    stripped = re.sub(r"\s*---+\s*", "\n", stripped)
    return stripped


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
