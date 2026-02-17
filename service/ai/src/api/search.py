from fastapi import APIRouter

from src.models.request import SearchRequest
from src.models.response import SearchResponse, SearchResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """文档搜索接口"""
    from src.app import get_vector_store

    vs = get_vector_store()
    results = vs.search_with_score(request.query, k=request.k)

    items = [
        SearchResult(
            content=doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
            metadata=doc.metadata,
            score=float(score),
        )
        for doc, score in results
    ]

    return SearchResponse(success=True, results=items)
