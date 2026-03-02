from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    use_memory: Optional[bool] = True


class SearchRequest(BaseModel):
    query: str
    k: Optional[int] = 3
