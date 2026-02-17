from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    use_memory: Optional[bool] = True


class SearchRequest(BaseModel):
    query: str
    k: Optional[int] = 3


class RebuildRequest(BaseModel):
    confirm: bool = False
