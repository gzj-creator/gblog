import shutil
from pathlib import Path
from typing import List, Tuple

from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma

from src.config import settings
from src.core.embeddings import EmbeddingManager
from src.utils.exceptions import VectorStoreError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStoreManager:
    """Chroma 向量存储管理"""

    def __init__(self):
        self._embedding_mgr = EmbeddingManager()
        self._store: Chroma | None = None
        self._persist_dir = settings.VECTOR_STORE_PATH

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def initialize(self, force_rebuild: bool = False) -> None:
        if force_rebuild or not self._exists():
            logger.info("Building vector store from documents...")
            self._build()
        else:
            logger.info("Loading existing vector store...")
            self._load()

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def search(self, query: str, k: int = 3) -> List[Document]:
        self._ensure_ready()
        return self._store.similarity_search(query, k=k)

    def search_with_score(self, query: str, k: int = 3) -> List[Tuple[Document, float]]:
        self._ensure_ready()
        return self._store.similarity_search_with_score(query, k=k)

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------
    def add_documents(self, docs: List[Document]) -> None:
        self._ensure_ready()
        self._store.add_documents(docs)
        logger.info(f"Added {len(docs)} documents to vector store")

    def rebuild(self) -> None:
        logger.info("Rebuilding vector store...")
        if Path(self._persist_dir).exists():
            shutil.rmtree(self._persist_dir)
        self._build()

    # ------------------------------------------------------------------
    # 状态
    # ------------------------------------------------------------------
    @property
    def store(self) -> Chroma:
        self._ensure_ready()
        return self._store

    @property
    def is_ready(self) -> bool:
        return self._store is not None

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _exists(self) -> bool:
        p = Path(self._persist_dir)
        return p.exists() and any(p.iterdir())

    def _load(self) -> None:
        self._store = Chroma(
            persist_directory=self._persist_dir,
            embedding_function=self._embedding_mgr.get_embeddings(),
        )
        logger.info("Vector store loaded")

    def _build(self) -> None:
        from src.core.document_loader import GalayDocumentLoader

        loader = GalayDocumentLoader()
        documents = loader.load_all()
        if not documents:
            logger.warning("No documents loaded — creating empty vector store")
            self._store = Chroma(
                persist_directory=self._persist_dir,
                embedding_function=self._embedding_mgr.get_embeddings(),
            )
            return

        logger.info(f"Creating vector store with {len(documents)} documents...")
        self._store = Chroma.from_documents(
            documents=documents,
            embedding=self._embedding_mgr.get_embeddings(),
            persist_directory=self._persist_dir,
        )
        logger.info("Vector store created and persisted")

    def _ensure_ready(self) -> None:
        if self._store is None:
            raise VectorStoreError("Vector store not initialized — call initialize() first")
