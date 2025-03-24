"""Search endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....db.dependencies import get_db
from ....db.repositories.search import SearchRepository
from ....schemas.search import SearchResult

router = APIRouter()

@router.get("", response_model=SearchResult)
async def search(
    query: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> SearchResult:
    """Search blocks, transactions, addresses, and assets."""
    repo = SearchRepository(db)
    result = await repo.search(query=query, limit=limit)
    return SearchResult.from_orm(result) 