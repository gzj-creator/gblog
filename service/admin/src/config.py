from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8010
    LOG_LEVEL: str = "INFO"

    DB_SERVICE_BASE_URL: str = "http://127.0.0.1:8082"

    ADMIN_MANAGED_DOCS_PATH: str = "./managed_docs"
    ADMIN_RUNTIME_CONFIG_PATH: str = "./runtime/admin_config.json"

    ADMIN_AUTH_ENABLED: bool = True
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123456"
    ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    ADMIN_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ADMIN_AUTO_REINDEX_ON_DOC_CHANGE: bool = True
    ADMIN_ALLOWED_DOC_EXTENSIONS: str = ".md,.txt,.rst"
    ADMIN_MAX_UPLOAD_SIZE_KB: int = 1024
    ADMIN_DEFAULT_DOC_PROJECT: str = "custom"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
