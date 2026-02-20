from langchain_openai import OpenAIEmbeddings

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingManager:
    """Embedding 模型管理"""

    def __init__(self):
        self._embeddings: OpenAIEmbeddings | None = None

    def get_embeddings(self) -> OpenAIEmbeddings:
        if self._embeddings is None:
            logger.info(f"Initializing embedding model: {settings.EMBEDDING_MODEL}")
            self._embeddings = OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                model_kwargs={"encoding_format": "float"},
            )
        return self._embeddings
