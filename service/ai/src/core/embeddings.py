import time
from typing import List

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SafeEmbeddingAdapter(Embeddings):
    """Provider-safe wrapper for embedding batch failures."""

    def __init__(self, base: OpenAIEmbeddings, batch_size: int = 32):
        self._base = base
        self._batch_size = max(1, int(batch_size or 1))

    def embed_query(self, text: str) -> List[float]:
        return self._base.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        vectors: List[List[float]] = []
        for start in range(0, len(texts), self._batch_size):
            chunk = texts[start : start + self._batch_size]
            vectors.extend(self._embed_chunk_with_fallback(chunk))
        return vectors

    def _embed_chunk_with_fallback(self, chunk: List[str]) -> List[List[float]]:
        max_attempts = max(1, int(settings.EMBEDDING_MAX_RETRIES or 1))
        last_error: Exception | None = None

        for attempt in range(max_attempts):
            try:
                data = self._base.embed_documents(chunk)
                if not isinstance(data, list) or len(data) != len(chunk):
                    raise ValueError(
                        f"invalid embedding response size={None if data is None else len(data)} "
                        f"expected={len(chunk)}"
                    )
                return data
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                message = str(exc)
                transient = "429" in message or "rate limit" in message.lower() or "NoneType" in message
                if transient and attempt < max_attempts - 1:
                    time.sleep(min(1.5 ** attempt, 3.0))
                    continue
                break

        if len(chunk) == 1 and last_error is not None:
            raise last_error

        if len(chunk) > 1:
            mid = len(chunk) // 2
            logger.warning(
                "Embedding batch failed, split chunk",
                extra={"chunk_size": len(chunk), "left": mid, "right": len(chunk) - mid},
            )
            left = self._embed_chunk_with_fallback(chunk[:mid])
            right = self._embed_chunk_with_fallback(chunk[mid:])
            return left + right

        if last_error is not None:
            raise last_error
        raise RuntimeError("embedding failed without explicit error")


class EmbeddingManager:
    """Embedding 模型管理"""

    def __init__(self):
        self._embeddings: Embeddings | None = None

    def get_embeddings(self) -> Embeddings:
        if self._embeddings is None:
            logger.info(f"Initializing embedding model: {settings.EMBEDDING_MODEL}")
            base = OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                chunk_size=max(1, settings.EMBEDDING_BATCH_SIZE),
                max_retries=max(1, settings.EMBEDDING_MAX_RETRIES),
                request_timeout=max(1, settings.EMBEDDING_REQUEST_TIMEOUT),
                model_kwargs={"encoding_format": "float"},
            )
            self._embeddings = SafeEmbeddingAdapter(
                base=base,
                batch_size=settings.EMBEDDING_BATCH_SIZE,
            )
        return self._embeddings
