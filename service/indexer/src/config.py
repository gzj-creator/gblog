from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8011
    LOG_LEVEL: str = "INFO"

    INDEXER_DB_BASE_URL: str = "http://127.0.0.1:8082"
    INDEXER_POLL_INTERVAL_SECONDS: float = 2.0
    INDEXER_AUTO_START: bool = True
    INDEXER_MAX_ERROR_MESSAGE_LENGTH: int = 1000

    INDEXER_AI_ROOT: str = "../ai"
    INDEXER_BUILD_SCRIPT: str = "scripts/build_index.py"
    INDEXER_BUILD_FORCE: bool = True

    PYTHON_BIN: str = "python3"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def ai_root_path(self) -> Path:
        raw = Path(self.INDEXER_AI_ROOT).expanduser()
        if raw.is_absolute():
            return raw
        return (Path(__file__).resolve().parents[2] / raw).resolve()

    def build_script_path(self) -> Path:
        return (self.ai_root_path() / self.INDEXER_BUILD_SCRIPT).resolve()


settings = Settings()
