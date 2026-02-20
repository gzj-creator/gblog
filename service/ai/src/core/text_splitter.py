from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GalayTextSplitter:
    """Markdown 优化的文本分割器"""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size or settings.CHUNK_SIZE,
            chunk_overlap=chunk_overlap or settings.CHUNK_OVERLAP,
            separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " ", ""],
        )

    def split(self, documents: List[Document]) -> List[Document]:
        """分割文档列表"""
        chunks = self._splitter.split_documents(documents)
        logger.debug(f"Split {len(documents)} documents into {len(chunks)} chunks")
        return chunks


class GalayCodeSplitter:
    """C/C++ 代码优化分割器"""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size or settings.CODE_CHUNK_SIZE,
            chunk_overlap=chunk_overlap or settings.CODE_CHUNK_OVERLAP,
            separators=[
                "\nnamespace ",
                "\nclass ",
                "\nstruct ",
                "\ntemplate<",
                "\nCoroutine ",
                "\nvoid ",
                "\nbool ",
                "\nint ",
                "\n\n",
                "\n",
                " ",
                "",
            ],
        )

    def split(self, documents: List[Document]) -> List[Document]:
        chunks = self._splitter.split_documents(documents)
        logger.debug(f"Split {len(documents)} code files into {len(chunks)} chunks")
        return chunks
