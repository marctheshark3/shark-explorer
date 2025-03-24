"""Search repository."""
from typing import Optional, List, Dict, Any
from sqlalchemy import select, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, Transaction, Output, TokenInfo
from ...schemas.search import SearchResult

class SearchRepository:
    """Repository for search operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository."""
        self.session = session

    async def search(self, query: str, limit: int = 10) -> SearchResult:
        """Search across all entities."""
        # Search blocks
        block_result = await self.session.execute(
            select(Block)
            .where(
                or_(
                    Block.id.ilike(f"%{query}%"),
                    Block.height == query if query.isdigit() else False
                )
            )
            .order_by(desc(Block.height))
            .limit(limit)
        )
        blocks = block_result.scalars().all()

        # Search transactions
        tx_result = await self.session.execute(
            select(Transaction)
            .where(Transaction.id.ilike(f"%{query}%"))
            .order_by(desc(Transaction.timestamp))
            .limit(limit)
        )
        transactions = tx_result.scalars().all()

        # Search addresses
        address_result = await self.session.execute(
            select(Output.address)
            .where(Output.address.ilike(f"%{query}%"))
            .distinct()
            .limit(limit)
        )
        addresses = [row[0] for row in address_result if row[0]]

        # Search assets
        asset_result = await self.session.execute(
            select(TokenInfo.token_id)
            .where(
                or_(
                    TokenInfo.token_id.ilike(f"%{query}%"),
                    TokenInfo.name.ilike(f"%{query}%")
                )
            )
            .limit(limit)
        )
        assets = [row[0] for row in asset_result]

        return SearchResult(
            blocks=blocks,
            transactions=transactions,
            addresses=addresses,
            assets=assets,
            total_blocks=len(blocks),
            total_transactions=len(transactions),
            total_addresses=len(addresses),
            total_assets=len(assets)
        ) 