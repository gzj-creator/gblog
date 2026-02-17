from src.core.document_loader import GalayDocumentLoader
from src.core.vector_store import VectorStoreManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IndexService:
    """索引构建/重建服务"""

    def __init__(self, vector_store: VectorStoreManager):
        self._vector_store = vector_store
        self._loader = GalayDocumentLoader()

    def build_index(self) -> dict:
        """构建向量索引"""
        logger.info("Building index...")
        docs = self._loader.load_all()
        if not docs:
            return {"success": False, "message": "No documents found", "doc_count": 0}

        self._vector_store.add_documents(docs)
        logger.info(f"Index built with {len(docs)} documents")
        return {"success": True, "message": "Index built", "doc_count": len(docs)}

    def rebuild_index(self) -> dict:
        """清除旧索引并重建"""
        logger.info("Rebuilding index...")
        self._vector_store.rebuild()
        return {"success": True, "message": "Index rebuilt"}

    def get_index_stats(self) -> dict:
        """返回索引统计信息"""
        if not self._vector_store.is_ready:
            return {"status": "not_initialized", "doc_count": 0}

        collection = self._vector_store.store._collection
        count = collection.count()
        return {"status": "ready", "doc_count": count}
