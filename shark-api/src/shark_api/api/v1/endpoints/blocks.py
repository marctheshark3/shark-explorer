"""Block endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....db.dependencies import get_db
from ....db.repositories.blocks import BlockRepository
from ....schemas.blocks import BlockDetail, BlockHeader
from ....schemas.base import PaginatedResponse

router = APIRouter()

@router.get("/latest", response_model=BlockHeader)
async def get_latest_block(
    db: AsyncSession = Depends(get_db)
) -> BlockHeader:
    """Get latest block."""
    repo = BlockRepository(db)
    block = await repo.get_latest()
    if not block:
        raise HTTPException(status_code=404, detail="No blocks found")
    return BlockHeader.from_orm(block)

@router.get("/{block_id}", response_model=BlockDetail)
async def get_block_by_id(
    block_id: str,
    db: AsyncSession = Depends(get_db)
) -> BlockDetail:
    """Get block by ID."""
    repo = BlockRepository(db)
    block = await repo.get_block_with_details(block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    return BlockDetail.from_orm(block)

@router.get("/height/{height}", response_model=BlockDetail)
async def get_block_by_height(
    height: int,
    db: AsyncSession = Depends(get_db)
) -> BlockDetail:
    """Get block by height."""
    repo = BlockRepository(db)
    block = await repo.get_by_height(height)
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    return BlockDetail.from_orm(block)

@router.get("", response_model=PaginatedResponse[BlockHeader])
async def get_blocks(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    from_height: Optional[int] = Query(None, ge=0),
    to_height: Optional[int] = Query(None, ge=0),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[BlockHeader]:
    """Get blocks with pagination."""
    repo = BlockRepository(db)
    
    # Build filters
    filters = {}
    if from_height is not None:
        filters["height__ge"] = from_height
    if to_height is not None:
        filters["height__le"] = to_height
        
    # Get blocks
    blocks = await repo.get_multi(
        skip=offset,
        limit=limit,
        order_by="-height",
        **filters
    )
    total = await repo.count(**filters)
    
    return PaginatedResponse(
        items=[BlockHeader.from_orm(block) for block in blocks],
        total=total,
        offset=offset,
        limit=limit
    ) 