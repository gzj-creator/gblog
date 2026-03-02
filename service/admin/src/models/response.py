from pydantic import BaseModel, Field
from typing import Any, Dict


class StatsResponse(BaseModel):
    success: bool
    stats: Dict[str, Any] = Field(default_factory=dict)
