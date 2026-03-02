import re
from typing import AsyncGenerator, Dict, List, Tuple

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import settings
from src.core.vector_store import VectorStoreManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """你是 Galay 框架的 AI 助手，专门回答关于 Galay 高性能 C++ 网络框架的问题。

Galay 是一个基于 C++20/23 协程的高性能异步网络框架，包含以下核心组件：
- galay-kernel: 核心协程运行时，支持 kqueue/epoll/io_uring 多后端
- galay-ssl: TLS/SSL 传输层，基于 OpenSSL 的异步加密通信，支持 SNI/ALPN/Session 复用
- galay-http: HTTP/1.1 + HTTP/2 + WebSocket 协议实现，支持同步与协程异步
- galay-rpc: RPC 框架，支持 unary/双向流/服务发现
- galay-redis: 协程 Redis 客户端，支持 Pipeline 批处理与超时控制
- galay-mysql: 协程 MySQL 客户端，支持预处理语句与事务
- galay-mongo: MongoDB 客户端，支持 OP_MSG 协议、SCRAM-SHA-256 认证与异步 Pipeline
- galay-etcd: etcd v3 客户端，支持 KV/Lease/Pipeline 操作
- galay-utils: 工具库（线程池、一致性哈希、熔断器等）
- galay-mcp: MCP 协议实现，支持 Stdio 与 HTTP 传输

回答要求：
1. 准确引用文档内容
2. 提供代码示例（如果相关）
3. 说明性能指标（如果相关）
4. 如果文档中没有相关信息，诚实告知
5. 使用中文回答
6. 保持专业和友好的语气
7. 不要使用 emoji 或花哨符号（如 ✅🌟🔥📌）
8. 输出要结构化分块：先简要结论，再用 1. 2. 3. 列点说明
9. 对“如何开始/入门/安装/快速开始”类问题，优先按这 4 节回答：
   - 环境要求
   - 安装步骤
   - 最小示例
   - 运行与验证
10. 代码必须使用独立 fenced code block（```cpp ... ```），不要把代码和正文写在同一行。
11. 回答“支持哪些能力/调用模式/特性”时，优先穷举文档中列出的能力点，并保留原始术语（如 Unary、流式、服务发现）。
12. 严禁编造不存在的 API（例如 `IoContext`、`ioContext`、`IoContext::GetInstance()`）。
13. 仅在讲解 `galay-kernel` 或显式需要手动调度器时，才使用 `Runtime` 获取调度器：
    - IO 调度器：`runtime.getNextIOScheduler()`
    - 计算调度器：`runtime.getNextComputeScheduler()`。
14. 涉及 `HttpServer` 示例时，必须严格使用文档流程：
    - `HttpRouter router;`
    - `HttpServerConfig config;`
    - `HttpServer server(config);`
    - `server.start(std::move(router));`
    严禁输出未文档化写法：`HttpServer server;`、`HttpServer(...scheduler...)`、`server.get/post/...`、`server.start(8080)`。
15. 协程返回类型统一使用 `Coroutine`；不要输出 `Task<void>` / `Task<T>`。
16. 严禁使用协程 lambda（如 `auto task = [](...) { co_await ... };`），必须使用具名 `Coroutine` 函数。
17. `Runtime` 不是单例，不存在 `Runtime::getInstance()`，应直接创建对象（如 `galay::kernel::Runtime runtime;`）。
18. 回答 `galay-http` 的安装/最小示例时，依赖清单必须包含 `galay-utils`（通常为 `kernel + utils + http`，TLS 场景再加 `ssl`）。
19. 只要给 C++ 代码示例，必须同时给两段代码：`#include` 版本 + `import` 版本（各自独立 fenced code block）。
20. C++ 代码排版必须统一：4 空格缩进，花括号对齐，`#include` 预处理行顶格。
21. 回答“用法/示例/demo/example/快速开始”时，必须优先依据 demo/example/test/README/快速开始/使用示例中已有调用链；若示例没有该写法，必须明确说“示例中未提供”，不要补脑编造。
22. 以下调用链必须与示例保持一致：
    - `galay-http`：`HttpServerConfig` + `HttpRouter` + `HttpServer server(config)` + `server.start(std::move(router))`
    - `galay-rpc`：`RpcServerConfig` + `RpcServer server(config)` + `server.start()`
    - `galay-redis`：`Runtime` + `runtime.getNextIOScheduler()` + `RedisClient client(scheduler)`
    - `galay-mysql`：`AsyncMysqlClient client(scheduler)`（异步场景）
    - `galay-mongo`：`AsyncMongoClient client(scheduler)`（异步场景）
    - `galay-etcd`：`AsyncEtcdClient client(scheduler)`（异步场景）
    - `galay-mcp`：`McpStdioServer::run()` 或 `McpHttpServer(host, port).start()`。
23. 只要出现 `co_await` 调用，必须显式处理返回值；不能只写一行裸 `co_await ...;`。若返回 `void`，请明确注释“仅等待完成”。 
24. 对上一轮的追问（如“websocket 呢”“那 HTTP2 呢”），默认沿用前文已给出的环境/安装信息，不要重复整段安装流程，除非用户明确要求重述。"""

_USAGE_QUERY_RE = re.compile(
    r"(示例|demo|example|sample|用法|怎么用|如何用|如何使用|入门|快速开始|最小示例|最小用例|代码示例|样例)",
    re.IGNORECASE,
)
_EXAMPLE_SOURCE_STRONG_HINTS = (
    "/example/",
    "/examples/",
    "/demo/",
    "/demos/",
    "/test/",
    "/tests/",
)
_EXAMPLE_SOURCE_WEAK_HINTS = (
    "readme.md",
    "快速开始",
    "使用示例",
    "示例代码",
    "使用指南",
)


class RAGService:
    """RAG 检索增强生成服务"""

    def __init__(self, vector_store: VectorStoreManager):
        self._vector_store = vector_store
        self._llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=settings.TEMPERATURE,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
        )
        self._lexical_cache: List[Document] | None = None

    def invalidate_cache(self) -> None:
        self._lexical_cache = None

    def retrieve(self, query: str, k: int = 4) -> List[Document]:
        """检索相关文档片段（向量召回 + 关键词重排）"""
        return [doc for doc, _ in self.retrieve_with_score(query, k=k)]

    def retrieve_with_score(self, query: str, k: int = 4) -> List[Tuple[Document, float]]:
        """检索相关文档片段并返回重排分数（值越大相关性越高）"""
        ranked = self._retrieve_ranked(query, k)
        return [(doc, score) for doc, score in ranked]

    def _retrieve_ranked(self, query: str, k: int) -> List[Tuple[Document, float]]:
        if not query.strip():
            return []

        project_hint = _extract_project_hint(query)
        usage_intent = is_usage_query(query)
        candidate_k = min(max(k * 32, 64), 256)
        dense = self._vector_store.search_with_score(query, k=candidate_k)
        if not dense:
            return []

        terms = _extract_query_terms(query)
        rank_map: Dict[str, Tuple[float, Document]] = {}
        for doc, distance in dense:
            dense_score = 1.0 / (1.0 + max(float(distance), 0.0))
            lexical_score = _lexical_overlap_score(doc.page_content, terms)
            source_boost = _source_path_boost(doc, terms)
            project_boost = _project_hint_boost(doc, project_hint)
            example_boost = _example_source_boost(doc)
            # dense 为主，关键词为辅；避免被噪声关键词完全盖过语义召回。
            example_weight = 0.18 if usage_intent else 0.08
            final_score = (
                dense_score * 0.52
                + lexical_score * 0.16
                + source_boost * 0.04
                + project_boost * 0.1
                + example_boost * example_weight
            )
            key = _doc_key(doc)
            old = rank_map.get(key)
            if old is None or final_score > old[0]:
                rank_map[key] = (final_score, doc)

        # 关键词兜底：从全量 chunks 再做一次词项匹配，提升明确术语的命中率。
        if terms:
            for score, doc in self._lexical_fallback(
                terms,
                project_hint,
                usage_intent=usage_intent,
                limit=max(24, k * 8),
            ):
                key = _doc_key(doc)
                old = rank_map.get(key)
                if old is None or score > old[0]:
                    rank_map[key] = (score, doc)

        ranked: List[Tuple[float, Document]] = sorted(rank_map.values(), key=lambda x: x[0], reverse=True)
        project_first: List[Tuple[float, Document]] = []
        project_fallback: List[Tuple[float, Document]] = []
        seen: set[str] = set()
        for score, doc in ranked:
            key = _doc_key(doc)
            if key in seen:
                continue
            seen.add(key)
            if project_hint and str(doc.metadata.get("project", "")).lower() == project_hint:
                project_first.append((score, doc))
            else:
                project_fallback.append((score, doc))

        merged = project_first + project_fallback if project_hint else project_fallback
        unique: List[Tuple[Document, float]] = []
        for score, doc in merged:
            unique.append((doc, score))
            if len(unique) >= k:
                break
        return unique

    def _lexical_fallback(
        self,
        terms: List[str],
        project_hint: str | None = None,
        usage_intent: bool = False,
        limit: int = 24,
    ) -> List[Tuple[float, Document]]:
        docs = self._get_all_docs_for_rerank()
        if not docs:
            return []

        scored: List[Tuple[float, Document]] = []
        for doc in docs:
            lex = _lexical_overlap_score(doc.page_content, terms)
            if lex <= 0:
                continue
            source_boost = _source_path_boost(doc, terms)
            project_boost = _project_hint_boost(doc, project_hint)
            example_boost = _example_source_boost(doc)
            example_weight = 0.15 if usage_intent else 0.05
            score = lex * 0.65 + source_boost * 0.08 + project_boost * 0.12 + example_boost * example_weight
            scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[: max(1, limit)]

    def _get_all_docs_for_rerank(self) -> List[Document]:
        if self._lexical_cache is not None:
            return self._lexical_cache

        try:
            collection = self._vector_store.store._collection  # noqa: SLF001
            payload = collection.get(include=["documents", "metadatas"])
            documents = payload.get("documents", []) or []
            metadatas = payload.get("metadatas", []) or []
            docs: List[Document] = []
            for idx, content in enumerate(documents):
                meta = metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {}
                docs.append(Document(page_content=str(content or ""), metadata=dict(meta)))
            self._lexical_cache = docs
            return docs
        except Exception as exc:
            logger.warning(f"lexical fallback cache build failed: {exc}")
            self._lexical_cache = []
            return []

    def generate(self, query: str, context_docs: List[Document]) -> str:
        """基于检索到的文档生成回答"""
        messages = self._build_messages(query, context_docs)
        response = self._llm.invoke(messages)
        return response.content

    async def generate_stream(
        self, query: str, context_docs: List[Document]
    ) -> AsyncGenerator[str, None]:
        """流式生成回答"""
        messages = self._build_messages(query, context_docs)
        async for chunk in self._llm.astream(messages):
            if chunk.content:
                yield chunk.content

    def _build_messages(self, query: str, context_docs: List[Document]) -> list:
        """构建 LLM 消息列表"""
        context = format_context_docs(context_docs)
        guardrail = ""
        if is_usage_query(query) and not has_example_source(context_docs):
            guardrail = (
                "\n补充约束：当前检索上下文没有命中 demo/example/test/快速开始等示例来源。"
                "你必须避免编造 API；若文档未给出可执行示例，明确说明“示例中未提供该写法”。"
            )

        system_content = f"""{SYSTEM_PROMPT}
{guardrail}

请基于以下文档内容回答用户问题：

{context}"""

        return [
            SystemMessage(content=system_content),
            HumanMessage(content=query),
        ]


_ASCII_TERM_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./:+-]{1,}")
_CN_TERM_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_PROJECT_HINT_RE = re.compile(
    r"(galay-(?:kernel|ssl|http|rpc|redis|mysql|mongo|etcd|utils|mcp|ecosystem))",
    re.IGNORECASE,
)


def _extract_query_terms(query: str) -> List[str]:
    text = str(query or "")
    terms: List[str] = []
    for token in _ASCII_TERM_RE.findall(text):
        token = token.strip().lower()
        if len(token) >= 2:
            terms.append(token)
    for token in _CN_TERM_RE.findall(text):
        token = token.strip()
        if len(token) >= 2:
            terms.append(token)
    # 去重保序
    ordered: Dict[str, None] = {}
    for t in terms:
        ordered.setdefault(t, None)
    return list(ordered.keys())


def _extract_project_hint(query: str) -> str | None:
    text = str(query or "")
    match = _PROJECT_HINT_RE.search(text)
    if not match:
        lowered = text.lower()
        if "ecosystem" in lowered or ("galay" in lowered and "生态" in text):
            return "galay-ecosystem"
        return None
    return match.group(1).lower()


def is_usage_query(text: str) -> bool:
    return bool(_USAGE_QUERY_RE.search(str(text or "")))


def is_example_source_path(source: str) -> bool:
    normalized = str(source or "").replace("\\", "/").lower()
    if not normalized:
        return False
    if any(hint in normalized for hint in _EXAMPLE_SOURCE_STRONG_HINTS):
        return True
    if any(hint in normalized for hint in _EXAMPLE_SOURCE_WEAK_HINTS):
        return True
    return False


def has_example_source(docs: List[Document]) -> bool:
    for doc in docs:
        source = str(doc.metadata.get("source", ""))
        if is_example_source_path(source):
            return True
    return False


def format_context_docs(context_docs: List[Document]) -> str:
    sections: List[str] = []
    for index, doc in enumerate(context_docs, start=1):
        project = str(doc.metadata.get("project", "unknown"))
        source = str(doc.metadata.get("source", "unknown"))
        header = f"[{index}] project={project} source={source}"
        body = str(doc.page_content or "").strip()
        if not body:
            continue
        sections.append(f"{header}\n{body}")
    return "\n\n".join(sections)


def _lexical_overlap_score(content: str, terms: List[str]) -> float:
    if not terms:
        return 0.0
    text = str(content or "")
    text_lc = text.lower()
    hits = 0
    for term in terms:
        if any(ord(ch) > 127 for ch in term):
            if term in text:
                hits += 1
        else:
            if term in text_lc:
                hits += 1
    return hits / len(terms)


def _source_path_boost(doc: Document, terms: List[str]) -> float:
    if not terms:
        return 0.0
    source = str(doc.metadata.get("source", "")).lower()
    if not source:
        return 0.0
    hits = 0
    for term in terms:
        if any(ord(ch) > 127 for ch in term):
            if term in source:
                hits += 1
        else:
            if term in source:
                hits += 1
    return min(1.0, hits / max(1, len(terms)))


def _example_source_boost(doc: Document) -> float:
    source = str(doc.metadata.get("source", ""))
    normalized = source.replace("\\", "/").lower()
    if not normalized:
        return 0.0
    if any(hint in normalized for hint in _EXAMPLE_SOURCE_STRONG_HINTS):
        return 1.0
    if any(hint in normalized for hint in _EXAMPLE_SOURCE_WEAK_HINTS):
        return 0.65
    return 0.0


def _project_hint_boost(doc: Document, project_hint: str | None) -> float:
    if not project_hint:
        return 0.0
    project = str(doc.metadata.get("project", "")).lower()
    return 1.0 if project == project_hint else 0.0


def _doc_key(doc: Document) -> str:
    meta = doc.metadata or {}
    source = str(meta.get("source", ""))
    chunk = str(meta.get("chunk", meta.get("chunk_id", meta.get("chunk_index", ""))))
    if source or chunk:
        return f"{source}:{chunk}"
    return str(hash(doc.page_content))
