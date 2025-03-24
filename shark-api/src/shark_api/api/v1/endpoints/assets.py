"""Asset endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....db.dependencies import get_db
from ....db.repositories.assets import AssetRepository
from ....schemas.assets import AssetDetail, AssetSummary
from ....schemas.base import PaginatedResponse

router = APIRouter()

@router.get("/{token_id}", response_model=AssetDetail)
async def get_asset_details(
    token_id: str,
    db: AsyncSession = Depends(get_db)
) -> AssetDetail:
    """Get asset details."""
    repo = AssetRepository(db)
    asset = await repo.get_asset_details(token_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return AssetDetail.from_orm(asset)

@router.get("", response_model=PaginatedResponse[AssetSummary])
async def search_assets(
    query: str = Query("", min_length=0),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[AssetSummary]:
    """Search assets."""
    repo = AssetRepository(db)
    
    # Search assets
    assets = await repo.search_assets(
        query=query,
        skip=offset,
        limit=limit
    )
    total = await repo.count_search_results(query)
    
    return PaginatedResponse(
        items=[AssetSummary.from_orm(asset) for asset in assets],
        total=total,
        offset=offset,
        limit=limit
    ) 