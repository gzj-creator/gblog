from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document

from src.config import settings
from src.core.text_splitter import GalayTextSplitter
from src.utils.exceptions import DocumentLoadError
from src.utils.logger import get_logger

logger = get_logger(__name__)

SKIP_PATTERNS = {"node_modules", ".git", "build", ".cache", "LICENSE", "CHANGELOG"}


class GalayDocumentLoader:
    """Galay 文档加载器"""

    def __init__(self):
        self._splitter = GalayTextSplitter()

    def load_file(self, path: str, base_path: Optional[str] = None) -> List[Document]:
        """加载单个 Markdown 文件并分割"""
        try:
            content = Path(path).read_text(encoding="utf-8")
        except Exception as e:
            raise DocumentLoadError(f"Failed to read {path}: {e}")

        project = self._extract_project(path, base_path)
        metadata = {
            "source": self._relative_path(path, base_path),
            "project": project,
            "file_name": Path(path).name,
        }

        doc = Document(page_content=content, metadata=metadata)
        chunks = self._splitter.split([doc])
        logger.info(f"Loaded {len(chunks)} chunks from {metadata['source']}")
        return chunks

    def load_all(self) -> List[Document]:
        """加载所有配置路径下的 Markdown 文档"""
        all_docs: List[Document] = []
        valid_paths = settings.validate_docs_paths()

        if not valid_paths:
            logger.warning("No valid documentation paths found")
            return all_docs

        for docs_path in valid_paths:
            logger.info(f"Loading documents from: {docs_path}")
            for md_file in Path(docs_path).rglob("*.md"):
                if self._should_skip(str(md_file)):
                    continue
                try:
                    all_docs.extend(self.load_file(str(md_file), base_path=docs_path))
                except DocumentLoadError as e:
                    logger.warning(str(e))

        logger.info(f"Total loaded {len(all_docs)} document chunks")
        return all_docs

    # ------------------------------------------------------------------
    def _relative_path(self, file_path: str, base_path: Optional[str] = None) -> str:
        if base_path:
            try:
                return str(Path(file_path).relative_to(Path(base_path)))
            except ValueError:
                pass

        for base in settings.validate_docs_paths():
            try:
                return str(Path(file_path).relative_to(Path(base)))
            except ValueError:
                continue
        return file_path

    def _extract_project(self, file_path: str, base_path: Optional[str] = None) -> str:
        if base_path:
            return Path(base_path).name

        for base in settings.validate_docs_paths():
            try:
                Path(file_path).relative_to(Path(base))
                return Path(base).name
            except ValueError:
                continue
        return "unknown"

    @staticmethod
    def _should_skip(file_path: str) -> bool:
        return any(p in file_path for p in SKIP_PATTERNS)
