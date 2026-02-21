from typing import AsyncGenerator, List

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
8. 输出要结构化分块：先简要结论，再用 1. 2. 3. 列点说明"""


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

    def retrieve(self, query: str, k: int = 4) -> List[Document]:
        """检索相关文档片段"""
        return self._vector_store.search(query, k=k)

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
