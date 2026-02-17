from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class SourceInfo(BaseModel):
    project: str
    file: str
    file_name: str


class ChatResponse(BaseModel):
    success: bool
    response: str
    sources: List[SourceInfo] = []
    session_id: Optional[str] = None
    error: Optional[str] = None


class SearchResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float


class SearchResponse(BaseModel):
    success: bool
    results: List[SearchResult] = []


class StatsResponse(BaseModel):
    success: bool
    stats: Dict[str, Any] = {}
