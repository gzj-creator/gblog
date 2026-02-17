from collections import OrderedDict
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
            answer = response.content

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

            full_answer = []
            async for chunk in self._llm.astream(messages):
                if chunk.content:
                    full_answer.append(chunk.content)
                    yield {"content": chunk.content}

            answer = "".join(full_answer)
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
            answer = self._rag.generate(message, docs)
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
