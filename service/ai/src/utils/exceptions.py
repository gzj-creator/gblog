class AIServiceError(Exception):
    """AI 服务基础异常"""

    def __init__(self, message: str = "AI service error", status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ConfigurationError(AIServiceError):
    """配置校验失败"""

    def __init__(self, message: str = "Configuration error"):
        super().__init__(message, status_code=500)


class VectorStoreError(AIServiceError):
    """向量存储操作失败"""

    def __init__(self, message: str = "Vector store error"):
        super().__init__(message, status_code=500)


class DocumentLoadError(AIServiceError):
    """文档加载失败"""

    def __init__(self, message: str = "Document load error"):
        super().__init__(message, status_code=500)


class ChatServiceError(AIServiceError):
    """聊天服务异常"""

    def __init__(self, message: str = "Chat service error"):
        super().__init__(message, status_code=500)


class ServiceUnavailableError(AIServiceError):
    """服务未就绪/不可用"""

    def __init__(self, message: str = "Service unavailable"):
        super().__init__(message, status_code=503)
