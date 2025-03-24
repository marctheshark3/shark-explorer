"""Status endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....db.dependencies import get_db
from ....db.repositories.blocks import BlockRepository
from ....schemas.status import SystemStatus, NodeStatus, IndexerStatus
from ....core.node import get_node_status
from ....core.config import settings

router = APIRouter()

@router.get("", response_model=SystemStatus)
async def get_system_status(
    db: AsyncSession = Depends(get_db)
) -> SystemStatus:
    """Get system status."""
    # Get node status
    node_status = await get_node_status()
    
    # Get indexer status
    repo = BlockRepository(db)
    latest_block = await repo.get_latest()
    indexer_height = latest_block.height if latest_block else 0
    
    # Calculate sync percentage
    sync_percentage = (indexer_height / node_status.block_height * 100) if node_status.block_height > 0 else 0
    
    return SystemStatus(
        node=NodeStatus(
            version=node_status.version,
            network=settings.NETWORK,
            block_height=node_status.block_height,
            is_mining=node_status.is_mining,
            peers_count=node_status.peers_count,
            unconfirmed_count=node_status.unconfirmed_count
        ),
        indexer=IndexerStatus(
            version=settings.VERSION,
            block_height=indexer_height,
            sync_percentage=sync_percentage,
            is_syncing=sync_percentage < 100
        )
    ) 