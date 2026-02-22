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
13. 涉及调度器初始化时，使用 `Runtime` 获取调度器：
    - IO 调度器：`runtime.getNextIOScheduler()`
    - 计算调度器：`runtime.getNextComputeScheduler()`。
14. 协程返回类型统一使用 `Coroutine`；不要输出 `Task<void>` / `Task<T>`。
15. 严禁使用协程 lambda（如 `auto task = [](...) { co_await ... };`），必须使用具名 `Coroutine` 函数。"""


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
            # dense 为主，关键词为辅；避免被噪声关键词完全盖过语义召回。
            final_score = dense_score * 0.65 + lexical_score * 0.2 + source_boost * 0.05 + project_boost * 0.1
            key = _doc_key(doc)
            old = rank_map.get(key)
            if old is None or final_score > old[0]:
                rank_map[key] = (final_score, doc)

        # 关键词兜底：从全量 chunks 再做一次词项匹配，提升明确术语的命中率。
        if terms:
            for score, doc in self._lexical_fallback(terms, project_hint, limit=max(24, k * 8)):
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
            score = lex * 0.75 + source_boost * 0.1 + project_boost * 0.15
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
        context = "\n\n".join(doc.page_content for doc in context_docs)

        system_content = f"""{SYSTEM_PROMPT}

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
