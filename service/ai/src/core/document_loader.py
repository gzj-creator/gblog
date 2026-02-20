from pathlib import Path
from typing import List, Optional, Set

from langchain_core.documents import Document

from src.config import settings
from src.core.text_splitter import GalayCodeSplitter, GalayTextSplitter
from src.utils.exceptions import DocumentLoadError
from src.utils.logger import get_logger

logger = get_logger(__name__)

SKIP_PATTERNS = {"node_modules", ".git", "build", ".cache", "LICENSE", "CHANGELOG"}
MARKDOWN_SUFFIX = ".md"


class GalayDocumentLoader:
    """Galay 文档加载器"""

    def __init__(self):
        self._markdown_splitter = GalayTextSplitter()
        self._code_splitter = GalayCodeSplitter()
        self._code_extensions = self._parse_extensions(settings.CODE_FILE_EXTENSIONS)

    def load_file(self, path: str, base_path: Optional[str] = None) -> List[Document]:
        """加载单个文件并分割"""
        file_path = Path(path)
        file_type = self._detect_file_type(file_path)
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            raise DocumentLoadError(f"Failed to read {path}: {e}")

        project = self._extract_project(path, base_path)
        metadata = {
            "source": self._relative_path(path, base_path),
            "project": project,
            "file_name": file_path.name,
            "file_type": file_type,
        }

        doc = Document(page_content=content, metadata=metadata)
        splitter = self._markdown_splitter if file_type == "markdown" else self._code_splitter
        chunks = splitter.split([doc])
        logger.info(f"Loaded {len(chunks)} chunks from {metadata['source']}")
        return chunks

    def load_all(self) -> List[Document]:
        """加载所有配置路径下的可索引文档与代码文件"""
        all_docs: List[Document] = []
        valid_paths = settings.validate_docs_paths()
        markdown_files = 0
        code_files = 0

        if not valid_paths:
            logger.warning("No valid documentation paths found")
            return all_docs

        for docs_path in valid_paths:
            logger.info(f"Loading documents from: {docs_path}")
            for file_path in self._iter_indexable_files(Path(docs_path)):
                if self._should_skip(str(file_path)):
                    continue
                try:
                    all_docs.extend(self.load_file(str(file_path), base_path=docs_path))
                    if self._detect_file_type(file_path) == "markdown":
                        markdown_files += 1
                    else:
                        code_files += 1
                except DocumentLoadError as e:
                    logger.warning(str(e))

        logger.info(f"Indexed files: markdown={markdown_files}, code={code_files}")
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
        lower_path = file_path.lower()
        return any(p.lower() in lower_path for p in SKIP_PATTERNS)

    @staticmethod
    def _parse_extensions(raw: str) -> Set[str]:
        extensions: Set[str] = set()
        for item in raw.split(","):
            ext = item.strip().lower()
            if not ext:
                continue
            if not ext.startswith("."):
                ext = "." + ext
            extensions.add(ext)
        return extensions

    def _detect_file_type(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix == MARKDOWN_SUFFIX:
            return "markdown"
        if suffix in self._code_extensions:
            return "code"
        return "unknown"

    def _iter_indexable_files(self, root: Path) -> List[Path]:
        patterns = ["*.md"]
        if settings.ENABLE_CODE_INDEXING:
            patterns.extend([f"*{ext}" for ext in sorted(self._code_extensions)])

        files: List[Path] = []
        seen: Set[str] = set()
        for pattern in patterns:
            for file_path in root.rglob(pattern):
                normalized = str(file_path.resolve())
                if normalized in seen:
                    continue
                seen.add(normalized)
                if not self._is_indexable_file(file_path):
                    continue
                files.append(file_path)

        files.sort()
        return files

    def _is_indexable_file(self, file_path: Path) -> bool:
        if not file_path.is_file():
            return False

        max_size = max(1, settings.MAX_INDEX_FILE_SIZE_KB) * 1024
        try:
            if file_path.stat().st_size > max_size:
                logger.debug(f"Skip large file: {file_path}")
                return False
            with file_path.open("rb") as f:
                head = f.read(2048)
        except OSError as e:
            logger.warning(f"Skip unreadable file {file_path}: {e}")
            return False

        if b"\x00" in head:
            logger.debug(f"Skip binary-like file: {file_path}")
            return False
        return True
