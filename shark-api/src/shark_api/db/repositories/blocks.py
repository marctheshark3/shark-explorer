"""Repository for block-related database operations."""
import logging
from typing import Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shark_api.db.models import Block, MiningReward
from shark_api.schemas.blocks import BlockDetail
from shark_api.db.repositories.base import BaseRepository

class BlockRepository(BaseRepository[Block]):
    """Repository for block-related database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository."""
        super().__init__(Block, session)
        self.logger = logging.getLogger(__name__)

    async def get_latest(self) -> Optional[Block]:
        """Get latest block."""
        try:
            result = await self.session.execute(
                select(
                    Block.id,
                    Block.header_id,
                    Block.parent_id,
                    Block.height,
                    Block.timestamp,
                    Block.difficulty,
                    Block.block_size,
                    Block.block_coins,
                    Block.block_mining_time,
                    Block.txs_count,
                    Block.txs_size,
                    Block.miner_address,
                    Block.miner_name,
                    Block.main_chain,
                    Block.version,
                    Block.transactions_root,
                    Block.state_root,
                    Block.pow_solutions
                )
                .order_by(Block.height.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Error getting latest block: {e}")
            raise

    async def get_latest_with_mining_rewards(self) -> Optional[Block]:
        """Get latest block with mining rewards."""
        try:
            result = await self.session.execute(
                select(Block)
                .options(selectinload(Block.mining_rewards))
                .order_by(Block.height.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Error getting latest block with mining rewards: {e}")
            raise

    async def get_by_height(self, height: int) -> Optional[Block]:
        """Get block by height."""
        result = await self.session.execute(
            select(
                Block.id,
                Block.header_id,
                Block.parent_id,
                Block.height,
                Block.timestamp,
                Block.difficulty,
                Block.block_size,
                Block.block_coins,
                Block.block_mining_time,
                Block.txs_count,
                Block.txs_size,
                Block.miner_address,
                Block.miner_name,
                Block.main_chain,
                Block.version,
                Block.transactions_root,
                Block.state_root,
                Block.pow_solutions
            ).where(Block.height == height)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, block_hash: str) -> Optional[Block]:
        """Get block by hash."""
        result = await self.session.execute(
            select(
                Block.id,
                Block.header_id,
                Block.parent_id,
                Block.height,
                Block.timestamp,
                Block.difficulty,
                Block.block_size,
                Block.block_coins,
                Block.block_mining_time,
                Block.txs_count,
                Block.txs_size,
                Block.miner_address,
                Block.miner_name,
                Block.main_chain,
                Block.version,
                Block.transactions_root,
                Block.state_root,
                Block.pow_solutions
            ).where(Block.id == block_hash)
        )
        return result.scalar_one_or_none()

    async def get_blocks_range(self, start_height: int, end_height: int) -> List[Block]:
        """Get blocks within a height range."""
        result = await self.session.execute(
            select(
                Block.id,
                Block.header_id,
                Block.parent_id,
                Block.height,
                Block.timestamp,
                Block.difficulty,
                Block.block_size,
                Block.block_coins,
                Block.block_mining_time,
                Block.txs_count,
                Block.txs_size,
                Block.miner_address,
                Block.miner_name,
                Block.main_chain,
                Block.version,
                Block.transactions_root,
                Block.state_root,
                Block.pow_solutions
            )
            .where(Block.height >= start_height)
            .where(Block.height <= end_height)
            .order_by(Block.height.desc())
        )
        return result.scalars().all()

    async def get_block_with_details(self, block_id: str) -> Optional[BlockDetail]:
        """Get block with transaction and mining reward details."""
        try:
            # First, try to fetch the block
            block_query = select(Block).where(Block.id == block_id)
            block_result = await self.session.execute(block_query)
            block = block_result.scalar_one_or_none()
            
            if not block:
                return None
                
            # Fetch transactions separately
            from sqlalchemy.orm import joinedload
            from ..models import Transaction
            transactions_query = select(Transaction).where(Transaction.block_id == block_id)
            transactions_result = await self.session.execute(transactions_query)
            transactions = transactions_result.scalars().all()
            
            # Fetch mining rewards separately
            rewards_query = select(MiningReward).where(MiningReward.block_id == block_id)
            rewards_result = await self.session.execute(rewards_query)
            mining_rewards = rewards_result.scalars().all()
            
            # Create the result
            return BlockDetail(
                block=block,
                transactions=transactions,
                mining_rewards=mining_rewards
            )
        except Exception as e:
            self.logger.error(f"Error in get_block_with_details: {e}")
            raise 