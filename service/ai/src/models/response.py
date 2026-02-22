from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class SourceInfo(BaseModel):
    project: str
    file: str
    file_name: str


class ChatBlock(BaseModel):
    type: str
    text: Optional[str] = None
    level: Optional[int] = None
    ordered: Optional[bool] = None
    start: Optional[int] = None
    items: List[str] = Field(default_factory=list)
    language: Optional[str] = None
    code: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool
    response: str
    sources: List[SourceInfo] = Field(default_factory=list)
    blocks: List[ChatBlock] = Field(default_factory=list)
    session_id: Optional[str] = None
    error: Optional[str] = None


class SearchResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float


class SearchResponse(BaseModel):
    success: bool
    results: List[SearchResult] = Field(default_factory=list)


class StatsResponse(BaseModel):
    success: bool
    stats: Dict[str, Any] = Field(default_factory=dict)
