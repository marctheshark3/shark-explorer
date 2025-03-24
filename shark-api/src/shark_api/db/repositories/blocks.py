"""Repository for block-related database operations."""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shark_api.db.models import Block
from shark_api.schemas.blocks import BlockDetail

class BlockRepository:
    """Repository for block-related database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_latest(self) -> Optional[Block]:
        """Get the latest block."""
        result = await self.session.execute(
            select(Block).order_by(Block.height.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_height(self, height: int) -> Optional[Block]:
        """Get block by height."""
        result = await self.session.execute(
            select(Block).where(Block.height == height)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, block_hash: str) -> Optional[Block]:
        """Get block by hash."""
        result = await self.session.execute(
            select(Block).where(Block.id == block_hash)
        )
        return result.scalar_one_or_none()

    async def get_blocks_range(self, start_height: int, end_height: int) -> List[Block]:
        """Get blocks within a height range."""
        result = await self.session.execute(
            select(Block)
            .where(Block.height >= start_height)
            .where(Block.height <= end_height)
            .order_by(Block.height.desc())
        )
        return result.scalars().all()

    async def get_block_with_details(self, block_id: str) -> Optional[BlockDetail]:
        """Get block with transaction and mining reward details."""
        result = await self.session.execute(
            select(Block)
            .where(Block.id == block_id)
            .options(
                selectinload(Block.transactions),
                selectinload(Block.mining_rewards)
            )
        )
        block = result.scalar_one_or_none()
        if not block:
            return None
        
        return BlockDetail(
            block=block,
            transactions=block.transactions,
            mining_rewards=block.mining_rewards
        ) 