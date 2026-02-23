from collections import OrderedDict
from pathlib import Path
import re
from typing import Any, AsyncGenerator, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import settings
from src.core.markdown_blocks import markdown_to_blocks
from src.core.markdown_normalizer import normalize_markdown_content
from src.core.vector_store import VectorStoreManager
from src.services.rag_service import (
    RAGService,
    SYSTEM_PROMPT,
    format_context_docs,
    has_example_source,
    is_usage_query,
)
from src.utils.exceptions import ChatServiceError
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_SESSIONS = 100
MAX_HISTORY_ROUNDS = 20
STREAM_EMIT_MIN_CHARS = 16
STREAM_EMIT_MAX_CHARS = 120
USAGE_CODE_MIN_CONFIDENCE = 0.45

_FORBIDDEN_SCHEDULER_APIS = (
    re.compile(r"\b(?:IoContext|IOContext)\s*::\s*GetInstance\s*\(\s*\)", re.IGNORECASE),
    re.compile(r"\bioContext\b"),
    re.compile(r"\bIoContext\b"),
)
_TASK_RETURN_ANNOTATION_RE = re.compile(
    r"->\s*(?:galay::kernel::)?Task\s*<\s*[^>]+\s*>",
    re.IGNORECASE,
)
_TASK_VOID_RE = re.compile(
    r"\b(?:galay::kernel::)?Task\s*<\s*void\s*>",
    re.IGNORECASE,
)
_EMPTY_CAPTURE_COROUTINE_LAMBDA_START_RE = re.compile(
    r"^(?P<indent>\s*)auto\s+(?P<name>[A-Za-z_]\w*)\s*=\s*\[\s*\]\s*"
    r"\((?P<params>[^)]*)\)\s*(?:->\s*[^{]+)?\s*\{\s*$"
)
_COROUTINE_LAMBDA_END_RE = re.compile(r"^\s*};\s*$")
_RUNTIME_SINGLETON_REF_ASSIGN_RE = re.compile(
    r"(?m)^(?P<indent>\s*)(?:auto|(?:galay::kernel::)?Runtime)\s*&\s*"
    r"(?P<name>[A-Za-z_]\w*)\s*=\s*(?:galay::kernel::)?Runtime::getInstance\(\s*\)\s*;\s*$"
)
_RUNTIME_SINGLETON_PTR_ASSIGN_RE = re.compile(
    r"(?m)^(?P<indent>\s*)(?:auto|(?:galay::kernel::)?Runtime)\s*\*\s*"
    r"(?P<name>[A-Za-z_]\w*)\s*=\s*(?:&\s*)?(?:galay::kernel::)?Runtime::getInstance\(\s*\)\s*;\s*$"
)
_RUNTIME_SINGLETON_CALL_RE = re.compile(
    r"(?:galay::kernel::)?Runtime::getInstance\(\s*\)"
)
_HTTP_SERVER_DECL_RE = re.compile(
    r"(?m)^(?P<indent>\s*)HttpServer\s+(?P<name>[A-Za-z_]\w*)\s*"
    r"(?P<ctor>\((?P<args>[^)]*)\))?\s*;\s*$"
)
_HTTP_SERVER_START_CALL_RE = re.compile(
    r"(?m)^(?P<indent>\s*)(?P<name>[A-Za-z_]\w*)\s*\.\s*start\s*"
    r"\(\s*(?P<arg>[^)]*)\)\s*;\s*$"
)
_HTTP_SERVER_ROUTE_CALL_RE = re.compile(
    r"(?m)^(?P<indent>\s*)(?P<name>[A-Za-z_]\w*)\s*\.\s*"
    r"(?P<method>get|post|put|del|delete|patch|head|options)\s*"
    r"\((?P<args>.*)\)\s*;\s*$",
    re.IGNORECASE,
)
_HTTP_ROUTER_DECL_RE = re.compile(r"(?m)^\s*HttpRouter\s+\w+\s*;\s*$")
_HTTP_SERVER_SCHEDULER_ARG_TOKENS = (
    "scheduler",
    "getnextioscheduler",
    "getnextcomputescheduler",
)
_HTTP_METHOD_MAP = {
    "get": "GET",
    "post": "POST",
    "put": "PUT",
    "del": "DELETE",
    "delete": "DELETE",
    "patch": "PATCH",
    "head": "HEAD",
    "options": "OPTIONS",
}
_RPC_SERVER_DECL_RE = re.compile(
    r"(?m)^(?P<indent>\s*)RpcServer\s+(?P<name>[A-Za-z_]\w*)\s*"
    r"(?P<ctor>\((?P<args>[^)]*)\))?\s*;\s*$"
)
_RPC_SERVER_START_CALL_RE = re.compile(
    r"(?m)^(?P<indent>\s*)(?P<name>[A-Za-z_]\w*)\s*\.\s*start\s*"
    r"\(\s*(?P<arg>[^)]*)\)\s*;\s*$"
)
_RPC_SERVER_CONFIG_DECL_RE = re.compile(
    r"(?m)^\s*RpcServerConfig\s+[A-Za-z_]\w*\s*;\s*$"
)
_SCHEDULER_CLIENT_DEFAULT_CTOR_RE = re.compile(
    r"(?m)^(?P<indent>\s*)(?P<type>"
    r"(?:galay::redis::)?RedisClient|"
    r"(?:galay::mysql::)?AsyncMysqlClient|"
    r"(?:galay::mongo::)?AsyncMongoClient|"
    r"(?:galay::etcd::)?AsyncEtcdClient"
    r")\s+(?P<name>[A-Za-z_]\w*)\s*;\s*$"
)
_HTTP_KERNEL_CLONE_LINE_RE = re.compile(
    r"(?m)^(?P<indent>\s*)git\s+clone\s+https://github\.com/gzj-creator/galay-kernel\.git\s*$"
)
_HTTP_UTILS_CLONE_LINE_RE = re.compile(
    r"(?m)^\s*git\s+clone\s+https://github\.com/gzj-creator/galay-utils\.git\s*$"
)
_HTTP_HTTP_CLONE_LINE_RE = re.compile(
    r"(?m)^(?P<indent>\s*)git\s+clone\s+https://github\.com/gzj-creator/galay-http\.git\s*$"
)
_CPP_FENCE_BLOCK_RE = re.compile(
    r"(?ms)(?P<open>```(?P<lang>[A-Za-z0-9_+\-]*)\s*\n)(?P<code>.*?)(?P<close>\n```)"
)
_CPP_INCLUDE_LINE_RE = re.compile(r'^\s*#\s*include\s*[<"](?P<header>[^>"]+)[>"]\s*$')
_CPP_IMPORT_LINE_RE = re.compile(r'^\s*import\s+(?P<module>[A-Za-z_][A-Za-z0-9_.]*)\s*;\s*$')
_CPP_LANGS = {"cpp", "c++", "cc", "cxx", "hpp", "h"}
_COMMAND_FENCE_LANGS = {"bash", "shell", "sh", "zsh", "cmake", "text", "plaintext"}
_FENCED_CODE_BLOCK_RE = re.compile(r"(?ms)```.*?```")
_GALAY_INCLUDE_PREFIX_TO_MODULE = (
    ("galay-kernel/", "galay.kernel"),
    ("galay-ssl/", "galay.ssl"),
    ("galay-http/", "galay.http"),
    ("galay-rpc/", "galay.rpc"),
    ("galay-redis/", "galay.redis"),
    ("galay-mysql/", "galay.mysql"),
    ("galay-mongo/", "galay.mongo"),
    ("galay-etcd/", "galay.etcd"),
    ("galay-utils/", "galay.utils"),
    ("galay-mcp/", "galay.mcp"),
)
_GALAY_MODULE_TO_INCLUDE = {
    "galay.kernel": '#include "galay-kernel/kernel/Runtime.h"',
    "galay.ssl": '#include "galay-ssl/async/SslSocket.h"',
    "galay.http": '#include "galay-http/kernel/http/HttpServer.h"',
    "galay.rpc": '#include "galay-rpc/kernel/RpcServer.h"',
    "galay.redis": '#include "galay-redis/async/RedisClient.h"',
    "galay.mysql": '#include "galay-mysql/async/AsyncMysqlClient.h"',
    "galay.mongo": '#include "galay-mongo/async/AsyncMongoClient.h"',
    "galay.etcd": '#include "galay-etcd/async/AsyncEtcdClient.h"',
    "galay.utils": '#include <galay-utils/galay-utils.hpp>',
    "galay.mcp": '#include "galay-mcp/server/McpStdioServer.h"',
}


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
            docs_with_score = self._rag.retrieve_with_score(message, k=4)
            docs = [doc for doc, _ in docs_with_score]
            sources = _extract_sources(docs)
            messages = self._build_messages(message, docs, session_id)

            response = self._llm.invoke(messages)
            answer = _normalize_answer_text(_extract_message_text(response))
            answer = _downgrade_answer_when_example_missing(answer, message, docs)
            answer = _enforce_confidence_gate_for_code(answer, message, docs_with_score)
            answer = _ensure_source_citations(answer, docs)
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
            docs_with_score = self._rag.retrieve_with_score(message, k=4)
            docs = [doc for doc, _ in docs_with_score]
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
                normalized_answer = _downgrade_answer_when_example_missing(normalized_answer, message, docs)
                normalized_answer = _enforce_confidence_gate_for_code(normalized_answer, message, docs_with_score)
                normalized_answer = _ensure_source_citations(normalized_answer, docs)
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
                normalized_answer = _downgrade_answer_when_example_missing(normalized_answer, message, docs)
                normalized_answer = _enforce_confidence_gate_for_code(normalized_answer, message, docs_with_score)
                normalized_answer = _ensure_source_citations(normalized_answer, docs)
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
            docs_with_score = self._rag.retrieve_with_score(message, k=4)
            docs = [doc for doc, _ in docs_with_score]
            if not docs:
                return {
                    "success": True,
                    "response": "抱歉，我在文档中没有找到相关信息。请尝试换个方式提问。",
                    "blocks": _build_answer_blocks("抱歉，我在文档中没有找到相关信息。请尝试换个方式提问。"),
                    "sources": [],
                }
            answer = _normalize_answer_text(self._rag.generate(message, docs))
            answer = _downgrade_answer_when_example_missing(answer, message, docs)
            answer = _enforce_confidence_gate_for_code(answer, message, docs_with_score)
            answer = _ensure_source_citations(answer, docs)
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
        context = format_context_docs(docs)
        guardrail = ""
        if is_usage_query(message) and not has_example_source(docs):
            guardrail = (
                "\n补充约束：当前检索上下文没有命中 demo/example/test/快速开始等示例来源。"
                "不要输出未被示例验证的 API 写法；若示例未覆盖，请明确说明。"
            )

        system_content = f"""{SYSTEM_PROMPT}
{guardrail}

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


def _normalize_answer_text(raw: str, *, finalize_examples: bool = True) -> str:
    """统一规范模型输出，保证与入库文档一致的 markdown 规则。"""
    if not raw:
        return ""

    normalized = normalize_markdown_content(str(raw), target="answer", strip_decorative=True)
    return _enforce_framework_output_consistency(normalized, finalize_examples=finalize_examples)


def _enforce_framework_output_consistency(text: str, *, finalize_examples: bool = True) -> str:
    if not text:
        return ""

    fixed = text
    changed = False
    notes: List[str] = []

    if any(pattern.search(fixed) for pattern in _FORBIDDEN_SCHEDULER_APIS):
        fixed = re.sub(
            r"\b(?:IoContext|IOContext)\s*::\s*GetInstance\s*\(\s*\)",
            "runtime.getNextIOScheduler()",
            fixed,
            flags=re.IGNORECASE,
        )
        fixed = re.sub(r"\bioContext\b", "ioScheduler", fixed)
        fixed = re.sub(r"\bIoContext\b", "IOScheduler", fixed)
        changed = True
        notes.append(
            "说明：Galay 当前没有 `IoContext` 单例 API，请使用 `Runtime` 获取调度器："
            "`runtime.getNextIOScheduler()` / `runtime.getNextComputeScheduler()`。"
        )

    if _TASK_RETURN_ANNOTATION_RE.search(fixed) or _TASK_VOID_RE.search(fixed):
        fixed = _TASK_RETURN_ANNOTATION_RE.sub("-> Coroutine", fixed)
        fixed = _TASK_VOID_RE.sub("Coroutine", fixed)
        changed = True
        notes.append(
            "说明：Galay 示例中的协程返回类型统一使用 `Coroutine`，不要使用 `Task<void>` / `Task<T>`。"
        )

    fixed, lambda_rewritten = _rewrite_empty_capture_coroutine_lambdas(fixed)
    if lambda_rewritten:
        changed = True
        notes.append(
            "说明：协程逻辑不要使用 lambda（避免生命周期问题），请使用具名 `Coroutine` 函数。"
        )

    runtime_fixed, runtime_rewritten = _rewrite_runtime_singleton_usage(fixed)
    if runtime_rewritten:
        fixed = runtime_fixed
        changed = True
        notes.append(
            "说明：`Runtime` 不是单例，没有 `Runtime::getInstance()`，请使用 `galay::kernel::Runtime runtime;`。"
        )

    http_server_fixed, http_server_rewritten = _rewrite_http_server_usage(fixed)
    if http_server_rewritten:
        fixed = http_server_fixed
        changed = True
        notes.append(
            "说明：`HttpServer` 示例已按文档 API 纠正为 `HttpServerConfig + HttpRouter + "
            "server.start(std::move(router))`。"
        )

    rpc_server_fixed, rpc_server_rewritten = _rewrite_rpc_server_usage(fixed)
    if rpc_server_rewritten:
        fixed = rpc_server_fixed
        changed = True
        notes.append("说明：`RpcServer` 示例已按文档 API 纠正为 `RpcServerConfig + RpcServer(config) + server.start()`。")

    scheduler_client_fixed, scheduler_client_rewritten = _rewrite_scheduler_client_constructors(fixed)
    if scheduler_client_rewritten:
        fixed = scheduler_client_fixed
        changed = True
        notes.append(
            "说明：`Redis/MySQL/Mongo/Etcd` 异步客户端示例已对齐为 `...Client(scheduler)` 构造。"
        )

    http_fixed, http_dependency_rewritten = _ensure_http_dependency_steps(fixed)
    if http_dependency_rewritten:
        fixed = http_fixed
        changed = True
        notes.append(
            "说明：`galay-http` 的安装依赖包含 `galay-utils`，拉取源码时请同时 clone。"
        )

    if finalize_examples:
        dual_mode_fixed, dual_mode_rewritten = _ensure_dual_cpp_example_modes(fixed)
        if dual_mode_rewritten:
            fixed = dual_mode_fixed
            changed = True
            notes.append(
                "说明：代码示例已补齐 `#include` 与 `import` 双范式，便于在传统头文件模式与 C++23 模块模式间切换。"
            )

    reindented, cpp_reindented = _reindent_cpp_fenced_blocks(fixed)
    if cpp_reindented:
        fixed = reindented
        changed = True
        notes.append("说明：代码块已按统一缩进规则对齐（4 空格缩进，预处理行顶格）。")

    command_reindented, command_rewritten = _normalize_command_fenced_blocks(fixed)
    if command_rewritten:
        fixed = command_reindented
        changed = True

    if changed:
        logger.warning("Detected forbidden coroutine/API style in model output, auto-corrected")

    return fixed


def _rewrite_empty_capture_coroutine_lambdas(text: str) -> tuple[str, bool]:
    lines = text.split("\n")
    output: List[str] = []
    idx = 0
    rewritten = False

    while idx < len(lines):
        line = lines[idx]
        match = _EMPTY_CAPTURE_COROUTINE_LAMBDA_START_RE.match(line)
        if not match:
            output.append(line)
            idx += 1
            continue

        end = None
        has_coroutine_ops = False
        scan_limit = min(len(lines), idx + 240)
        cursor = idx + 1
        while cursor < scan_limit:
            cur_line = lines[cursor]
            if "co_await" in cur_line or "co_return" in cur_line:
                has_coroutine_ops = True
            if _COROUTINE_LAMBDA_END_RE.match(cur_line):
                end = cursor
                break
            cursor += 1

        if end is None or not has_coroutine_ops:
            output.append(line)
            idx += 1
            continue

        indent = match.group("indent")
        name = match.group("name")
        params = match.group("params").strip() or "/* params */"
        runner_name = f"{name}_coroutine_runner"
        body_lines = lines[idx + 1 : end]

        output.append(f"{indent}struct {runner_name} {{")
        output.append(f"{indent}    Coroutine operator()({params}) {{")
        output.extend(body_lines)
        output.append(f"{indent}    }}")
        output.append(f"{indent}}} {name};")

        rewritten = True
        idx = end + 1

    return "\n".join(output), rewritten


def _rewrite_runtime_singleton_usage(text: str) -> tuple[str, bool]:
    fixed = text
    before = fixed

    rewritten_names: List[str] = []

    def _replace_runtime_ref(match: re.Match[str]) -> str:
        name = match.group("name")
        if name not in rewritten_names:
            rewritten_names.append(name)
        return f"{match.group('indent')}galay::kernel::Runtime {name};"

    fixed = _RUNTIME_SINGLETON_REF_ASSIGN_RE.sub(_replace_runtime_ref, fixed)
    fixed = _RUNTIME_SINGLETON_PTR_ASSIGN_RE.sub(_replace_runtime_ref, fixed)

    fallback_name = rewritten_names[0] if rewritten_names else "runtime"
    fixed = _RUNTIME_SINGLETON_CALL_RE.sub(fallback_name, fixed)

    for name in rewritten_names:
        fixed = fixed.replace(f"{name}->", f"{name}.")

    return fixed, fixed != before


def _rewrite_http_server_usage(text: str) -> tuple[str, bool]:
    if "HttpServer" not in text:
        return text, False

    fixed = text
    before = fixed
    router_required = False

    def _rewrite_decl(match: re.Match[str]) -> str:
        nonlocal router_required
        indent = match.group("indent")
        name = match.group("name")
        args = (match.group("args") or "").strip()

        if not args:
            router_required = True
            return f"{indent}HttpServerConfig config;\n{indent}HttpServer {name}(config);"

        lowered_args = args.lower()
        has_scheduler_token = any(token in lowered_args for token in _HTTP_SERVER_SCHEDULER_ARG_TOKENS)
        has_multiple_args = "," in args
        if has_scheduler_token or has_multiple_args:
            router_required = True
            return f"{indent}HttpServerConfig config;\n{indent}HttpServer {name}(config);"

        return match.group(0)

    fixed = _HTTP_SERVER_DECL_RE.sub(_rewrite_decl, fixed)

    server_names = set(
        re.findall(
            r"(?m)^\s*HttpServer\s+([A-Za-z_]\w*)\s*\([^;]*\)\s*;\s*$",
            fixed,
        )
    )
    if not server_names:
        return fixed, fixed != before

    def _rewrite_start(match: re.Match[str]) -> str:
        nonlocal router_required
        indent = match.group("indent")
        name = match.group("name")
        arg = (match.group("arg") or "").strip()
        if name not in server_names:
            return match.group(0)
        if arg == "std::move(router)":
            return match.group(0)
        router_required = True
        return f"{indent}{name}.start(std::move(router));"

    fixed = _HTTP_SERVER_START_CALL_RE.sub(_rewrite_start, fixed)

    def _rewrite_route(match: re.Match[str]) -> str:
        nonlocal router_required
        indent = match.group("indent")
        name = match.group("name")
        method = (match.group("method") or "").strip().lower()
        args = (match.group("args") or "").strip()

        if name not in server_names:
            return match.group(0)

        http_method = _HTTP_METHOD_MAP.get(method)
        if not http_method:
            return match.group(0)

        router_required = True
        return f"{indent}router.addHandler<HttpMethod::{http_method}>({args});"

    fixed = _HTTP_SERVER_ROUTE_CALL_RE.sub(_rewrite_route, fixed)

    if router_required and not _HTTP_ROUTER_DECL_RE.search(fixed):
        fixed, inserted = _insert_http_router_decl(fixed)
        if not inserted:
            fixed = f"HttpRouter router;\n{fixed}"

    return fixed, fixed != before


def _insert_http_router_decl(text: str) -> tuple[str, bool]:
    config_decl = re.search(
        r"(?m)^(?P<indent>\s*)HttpServerConfig\s+[A-Za-z_]\w*\s*;\s*$",
        text,
    )
    if config_decl:
        indent = config_decl.group("indent")
        insertion = f"{indent}HttpRouter router;\n"
        return text[: config_decl.start()] + insertion + text[config_decl.start() :], True

    server_decl = re.search(
        r"(?m)^(?P<indent>\s*)HttpServer\s+[A-Za-z_]\w*\s*\([^;]*\)\s*;\s*$",
        text,
    )
    if server_decl:
        indent = server_decl.group("indent")
        insertion = f"{indent}HttpRouter router;\n"
        return text[: server_decl.start()] + insertion + text[server_decl.start() :], True

    return text, False


def _rewrite_rpc_server_usage(text: str) -> tuple[str, bool]:
    if "RpcServer" not in text:
        return text, False

    fixed = text
    before = fixed

    def _rewrite_decl(match: re.Match[str]) -> str:
        indent = match.group("indent")
        name = match.group("name")
        args = (match.group("args") or "").strip()
        if args == "config":
            return match.group(0)
        return f"{indent}RpcServerConfig config;\n{indent}RpcServer {name}(config);"

    fixed = _RPC_SERVER_DECL_RE.sub(_rewrite_decl, fixed)

    server_names = set(
        re.findall(
            r"(?m)^\s*RpcServer\s+([A-Za-z_]\w*)\s*\([^;]*\)\s*;\s*$",
            fixed,
        )
    )
    if not server_names:
        return fixed, fixed != before

    def _rewrite_start(match: re.Match[str]) -> str:
        name = match.group("name")
        indent = match.group("indent")
        arg = (match.group("arg") or "").strip()
        if name not in server_names:
            return match.group(0)
        if not arg:
            return match.group(0)
        return f"{indent}{name}.start();"

    fixed = _RPC_SERVER_START_CALL_RE.sub(_rewrite_start, fixed)

    if "RpcServer" in fixed and not _RPC_SERVER_CONFIG_DECL_RE.search(fixed):
        server_decl = re.search(
            r"(?m)^(?P<indent>\s*)RpcServer\s+[A-Za-z_]\w*\s*\([^;]*\)\s*;\s*$",
            fixed,
        )
        if server_decl:
            indent = server_decl.group("indent")
            insertion = f"{indent}RpcServerConfig config;\n"
            fixed = fixed[: server_decl.start()] + insertion + fixed[server_decl.start() :]

    return fixed, fixed != before


def _rewrite_scheduler_client_constructors(text: str) -> tuple[str, bool]:
    if "scheduler" not in text:
        return text, False

    fixed = text
    before = fixed

    def _rewrite_decl(match: re.Match[str]) -> str:
        indent = match.group("indent")
        ctype = match.group("type")
        name = match.group("name")
        if name.startswith("m_"):
            return match.group(0)
        # 避免误改类成员声明，优先改常见局部变量名。
        if name not in {"client", "session", "sub", "pub", "redis", "mysql", "mongo", "etcd"}:
            return match.group(0)
        return f"{indent}{ctype} {name}(scheduler);"

    fixed = _SCHEDULER_CLIENT_DEFAULT_CTOR_RE.sub(_rewrite_decl, fixed)
    return fixed, fixed != before


def _ensure_http_dependency_steps(text: str) -> tuple[str, bool]:
    fixed = text
    before = fixed

    if "galay-http" not in fixed:
        return fixed, False

    has_kernel = bool(_HTTP_KERNEL_CLONE_LINE_RE.search(fixed))
    has_http = bool(_HTTP_HTTP_CLONE_LINE_RE.search(fixed))
    has_utils = bool(_HTTP_UTILS_CLONE_LINE_RE.search(fixed))
    if not (has_kernel and has_http) or has_utils:
        return fixed, False

    def _insert_after_kernel(match: re.Match[str]) -> str:
        indent = match.group("indent")
        return (
            f"{indent}git clone https://github.com/gzj-creator/galay-kernel.git\n"
            f"{indent}git clone https://github.com/gzj-creator/galay-utils.git"
        )

    fixed = _HTTP_KERNEL_CLONE_LINE_RE.sub(_insert_after_kernel, fixed, count=1)

    if fixed == before:
        def _insert_before_http(match: re.Match[str]) -> str:
            indent = match.group("indent")
            return (
                f"{indent}git clone https://github.com/gzj-creator/galay-utils.git\n"
                f"{match.group(0)}"
            )

        fixed = _HTTP_HTTP_CLONE_LINE_RE.sub(_insert_before_http, fixed, count=1)

    return fixed, fixed != before


def _ensure_dual_cpp_example_modes(text: str) -> tuple[str, bool]:
    cpp_blocks = _extract_cpp_blocks(text)
    if not cpp_blocks:
        return text, False

    include_code = next((code for code in cpp_blocks if _contains_galay_include(code)), "")
    import_code = next((code for code in cpp_blocks if _contains_galay_import(code)), "")

    if include_code and import_code:
        return text, False

    if include_code:
        import_variant = _build_import_variant_from_include(include_code)
        if not import_variant:
            return text, False
        appendix = (
            "\n\n### import 版本\n\n```cpp\n"
            f"{import_variant}\n"
            "```"
        )
        return f"{text.rstrip()}{appendix}", True

    if import_code:
        include_variant = _build_include_variant_from_import(import_code)
        if not include_variant:
            return text, False
        appendix = (
            "\n\n### include 版本\n\n```cpp\n"
            f"{include_variant}\n"
            "```"
        )
        return f"{text.rstrip()}{appendix}", True

    return text, False


def _extract_cpp_blocks(text: str) -> List[str]:
    blocks: List[str] = []
    for match in _CPP_FENCE_BLOCK_RE.finditer(text):
        lang = (match.group("lang") or "").strip().lower()
        code = str(match.group("code") or "")
        if lang in _CPP_LANGS or (not lang and _looks_like_cpp_snippet(code)):
            blocks.append(code)
    return blocks


def _contains_galay_include(code: str) -> bool:
    for raw in code.split("\n"):
        match = _CPP_INCLUDE_LINE_RE.match(raw)
        if not match:
            continue
        if _module_from_include_header(match.group("header") or ""):
            return True
    return False


def _contains_galay_import(code: str) -> bool:
    for raw in code.split("\n"):
        match = _CPP_IMPORT_LINE_RE.match(raw)
        if not match:
            continue
        module = (match.group("module") or "").strip()
        if module in _GALAY_MODULE_TO_INCLUDE:
            return True
    return False


def _build_import_variant_from_include(code: str) -> str:
    modules: List[str] = []
    body: List[str] = []

    for raw in code.split("\n"):
        include_match = _CPP_INCLUDE_LINE_RE.match(raw)
        if include_match:
            module = _module_from_include_header(include_match.group("header") or "")
            if module:
                if module not in modules:
                    modules.append(module)
                continue
        body.append(raw.rstrip())

    if not modules:
        return ""

    body = _trim_blank_edges(body)
    output = [f"import {module};" for module in modules]
    if body:
        output.extend([""] + body)

    return _reindent_cpp_code("\n".join(output))


def _build_include_variant_from_import(code: str) -> str:
    includes: List[str] = []
    body: List[str] = []

    for raw in code.split("\n"):
        import_match = _CPP_IMPORT_LINE_RE.match(raw)
        if import_match:
            module = (import_match.group("module") or "").strip()
            include_line = _GALAY_MODULE_TO_INCLUDE.get(module)
            if include_line:
                if include_line not in includes:
                    includes.append(include_line)
                continue
        body.append(raw.rstrip())

    if not includes:
        return ""

    body = _trim_blank_edges(body)
    output = includes[:]
    if body:
        output.extend([""] + body)

    return _reindent_cpp_code("\n".join(output))


def _module_from_include_header(header: str) -> str:
    normalized = str(header or "").strip()
    for prefix, module in _GALAY_INCLUDE_PREFIX_TO_MODULE:
        if normalized.startswith(prefix):
            return module
    return ""


def _trim_blank_edges(lines: List[str]) -> List[str]:
    cleaned = [str(line or "").rstrip() for line in lines]
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()
    return cleaned


def _reindent_cpp_fenced_blocks(text: str) -> tuple[str, bool]:
    changed = False

    def _replace(match: re.Match[str]) -> str:
        nonlocal changed
        lang = (match.group("lang") or "").strip().lower()
        code = str(match.group("code") or "")
        if lang not in _CPP_LANGS and not (not lang and _looks_like_cpp_snippet(code)):
            return match.group(0)

        normalized_code = _reindent_cpp_code(code)
        normalized_lang = lang or "cpp"
        if normalized_code != code or normalized_lang != lang:
            changed = True

        return f"```{normalized_lang}\n{normalized_code}\n```"

    fixed = _CPP_FENCE_BLOCK_RE.sub(_replace, text)
    return fixed, changed


def _normalize_command_fenced_blocks(text: str) -> tuple[str, bool]:
    changed = False

    def _replace(match: re.Match[str]) -> str:
        nonlocal changed
        lang = (match.group("lang") or "").strip()
        lang_lower = lang.lower()
        code = str(match.group("code") or "")

        if lang_lower not in _COMMAND_FENCE_LANGS:
            return match.group(0)

        lines = code.split("\n")
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()

        normalized_lines: List[str] = []
        for line in lines:
            if not line.strip():
                normalized_lines.append("")
                continue
            normalized_lines.append(line.lstrip())

        normalized_code = "\n".join(normalized_lines).rstrip()
        if normalized_code != code:
            changed = True

        normalized_lang = lang_lower if lang_lower else "text"
        return f"```{normalized_lang}\n{normalized_code}\n```"

    fixed = _CPP_FENCE_BLOCK_RE.sub(_replace, text)
    return fixed, changed


def _looks_like_cpp_snippet(code: str) -> bool:
    sample_lines = [line.strip() for line in str(code or "").split("\n") if line.strip()]
    if not sample_lines:
        return False

    sample = "\n".join(sample_lines[:16])
    if "#include" in sample:
        return True
    if re.search(r"^\s*import\s+[A-Za-z_][A-Za-z0-9_.]*\s*;", sample, flags=re.MULTILINE):
        return True
    if "co_await" in sample or "co_return" in sample:
        return True
    if re.search(r"\b(?:int|void|auto|class|struct|namespace|template)\b", sample):
        return True
    if "{" in sample and "}" in sample:
        return True
    return False


def _reindent_cpp_code(code: str) -> str:
    lines = str(code or "").replace("\t", "    ").split("\n")
    lines = _trim_blank_edges(lines)
    if not lines:
        return ""

    output: List[str] = []
    depth = 0

    for raw in lines:
        stripped = str(raw).strip()
        if not stripped:
            output.append("")
            continue

        starts_with_close = stripped.startswith("}")
        indent_level = max(depth - 1, 0) if starts_with_close else depth
        indent = "" if stripped.startswith("#") else ("    " * indent_level)
        output.append(f"{indent}{stripped}")

        open_count = stripped.count("{")
        close_count = stripped.count("}")
        depth += open_count - close_count
        if depth < 0:
            depth = 0

    return "\n".join(output).rstrip()


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
    preview_text = _normalize_answer_text(preview_raw, finalize_examples=False)
    if not preview_text:
        return "", []
    return preview_text, _build_answer_blocks(preview_text)


def _compute_evidence_confidence(docs_with_score: list) -> float:
    if not docs_with_score:
        return 0.0

    scores: List[float] = []
    for item in docs_with_score:
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        try:
            score = float(item[1])
        except (TypeError, ValueError):
            continue
        if score < 0.0:
            score = 0.0
        if score > 1.0:
            score = 1.0
        scores.append(score)

    if not scores:
        return 0.0

    top = scores[0]
    avg_top = sum(scores[:3]) / min(len(scores), 3)
    confidence = top * 0.7 + avg_top * 0.3
    if confidence < 0.0:
        return 0.0
    if confidence > 1.0:
        return 1.0
    return confidence


def _enforce_confidence_gate_for_code(answer: str, message: str, docs_with_score: list) -> str:
    if not answer:
        return answer
    if not is_usage_query(message):
        return answer

    confidence = _compute_evidence_confidence(docs_with_score)
    if confidence >= USAGE_CODE_MIN_CONFIDENCE:
        return answer

    stripped = _FENCED_CODE_BLOCK_RE.sub("", answer).strip()
    if not stripped:
        stripped = "结论：当前证据不足，暂不提供代码示例。"
    note = (
        f"说明：当前证据置信度 {confidence:.2f} 低于阈值 {USAGE_CODE_MIN_CONFIDENCE:.2f}，"
        "为避免误导，已省略代码块。请补充更具体的问题或指定仓库/模块。"
    )
    if note not in stripped:
        stripped = f"{stripped.rstrip()}\n\n{note}"
    return stripped


def _ensure_source_citations(answer: str, docs: list) -> str:
    if not answer:
        return answer
    if not docs:
        return answer
    if "参考来源" in answer:
        return answer

    refs: List[tuple[str, str]] = []
    seen: set[str] = set()
    for doc in docs:
        meta = getattr(doc, "metadata", {}) or {}
        source = str(meta.get("source", "")).strip()
        if not source:
            continue
        project = str(meta.get("project", "unknown")).strip() or "unknown"
        key = f"{project}:{source}"
        if key in seen:
            continue
        seen.add(key)
        refs.append((project, source))

    if not refs:
        return answer

    lower_answer = answer.lower()
    has_inline_ref = False
    for _, source in refs:
        source_lc = source.lower()
        source_name_lc = Path(source).name.lower()
        if source_lc in lower_answer or source_name_lc in lower_answer:
            has_inline_ref = True
            break

    if has_inline_ref:
        return answer

    lines = [f"{idx}. `{project}/{source}`" for idx, (project, source) in enumerate(refs[:6], start=1)]
    appendix = "参考来源：\n" + "\n".join(lines)
    return f"{answer.rstrip()}\n\n{appendix}"


def _downgrade_answer_when_example_missing(answer: str, message: str, docs: list) -> str:
    if not answer:
        return answer
    if not is_usage_query(message):
        return answer
    if has_example_source(docs):
        return answer

    stripped = _FENCED_CODE_BLOCK_RE.sub("", answer).strip()
    if not stripped:
        stripped = (
            "结论：当前检索上下文未命中 demo/example/test/快速开始来源，无法安全给出可执行示例代码。\n\n"
            "1. 我可以先按仓库与模块补齐示例来源后再生成代码。\n"
            "2. 在此之前仅建议参考对应项目的 README 与 API 文档流程。"
        )
    note = (
        "说明：为避免无依据代码示例，已省略代码块；请补充具体仓库（如 `galay-http`）"
        "或确认允许仅按 API 文档回答。"
    )
    if note not in stripped:
        stripped = f"{stripped.rstrip()}\n\n{note}"
    return stripped


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
