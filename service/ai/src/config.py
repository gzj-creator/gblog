from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置 — 自动从 .env 加载"""

    # LLM
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    MODEL_NAME: str = "gpt-4-turbo-preview"
    TEMPERATURE: float = 0.7

    # Embedding
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_REQUEST_TIMEOUT: int = 120
    EMBEDDING_MAX_RETRIES: int = 6

    # Vector Store
    VECTOR_STORE_PATH: str = "./vector_store"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    CODE_CHUNK_SIZE: int = 1400
    CODE_CHUNK_OVERLAP: int = 120

    # Ingestion
    ENABLE_CODE_INDEXING: bool = True
    CODE_FILE_EXTENSIONS: str = ".h,.hpp,.hh,.hxx,.c,.cc,.cpp,.cxx,.ixx,.tpp"
    MAX_INDEX_FILE_SIZE_KB: int = 512

    # Docs (recommended)
    GALAY_DOCS_ROOT_PATH: str = ""
    GALAY_DOCS_PATH: str = ""
    GALAY_DOCS_PATHS_FILE: str = ""

    # Docs (legacy variables, still supported)
    GALAY_KERNEL_DOCS_PATH: str = ""
    GALAY_SSL_DOCS_PATH: str = ""
    GALAY_HTTP_DOCS_PATH: str = ""
    GALAY_RPC_DOCS_PATH: str = ""
    GALAY_REDIS_DOCS_PATH: str = ""
    GALAY_MYSQL_DOCS_PATH: str = ""
    GALAY_MONGO_DOCS_PATH: str = ""
    GALAY_ETCD_DOCS_PATH: str = ""
    GALAY_UTILS_DOCS_PATH: str = ""
    GALAY_MCP_DOCS_PATH: str = ""

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def galay_docs_paths(self) -> List[str]:
        """
        所有 Galay 文档路径。

        优先支持通过 GALAY_DOCS_ROOT_PATH 自动扫描子目录，
        同时兼容历史逐仓库路径变量。
        """
        paths: List[str] = []

        # 配置文件路径列表（每行一个路径，支持 # 注释）
        paths_file = self.GALAY_DOCS_PATHS_FILE.strip()
        if paths_file:
            file_path = Path(paths_file).expanduser()
            if file_path.exists() and file_path.is_file():
                try:
                    lines = file_path.read_text(encoding="utf-8").splitlines()
                except OSError:
                    lines = []
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    candidate = Path(line).expanduser()
                    if not candidate.is_absolute():
                        candidate = file_path.parent.joinpath(candidate).resolve()
                    paths.append(str(candidate))

        root_path = self.GALAY_DOCS_ROOT_PATH.strip()
        if root_path:
            root = Path(root_path).expanduser()
            if root.exists() and root.is_dir():
                for child in sorted(root.iterdir()):
                    if child.is_dir() and not child.name.startswith("."):
                        paths.append(str(child))

        # 兼容旧变量（以及可选的单路径 GALAY_DOCS_PATH）
        legacy_paths = [
            self.GALAY_DOCS_PATH,
            self.GALAY_KERNEL_DOCS_PATH,
            self.GALAY_SSL_DOCS_PATH,
            self.GALAY_HTTP_DOCS_PATH,
            self.GALAY_RPC_DOCS_PATH,
            self.GALAY_REDIS_DOCS_PATH,
            self.GALAY_MYSQL_DOCS_PATH,
            self.GALAY_MONGO_DOCS_PATH,
            self.GALAY_ETCD_DOCS_PATH,
            self.GALAY_UTILS_DOCS_PATH,
            self.GALAY_MCP_DOCS_PATH,
        ]
        paths.extend([p.strip() for p in legacy_paths if p and p.strip()])

        # 去重并保序
        unique_paths: List[str] = []
        seen = set()
        for path in paths:
            normalized = str(Path(path).expanduser())
            if normalized in seen:
                continue
            seen.add(normalized)
            unique_paths.append(normalized)
        return unique_paths

    def validate_docs_paths(self) -> List[str]:
        """过滤不存在的路径，返回有效路径列表"""
        return [p for p in self.galay_docs_paths if Path(p).exists() and Path(p).is_dir()]


settings = Settings()
