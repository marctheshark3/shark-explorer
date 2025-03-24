"""Asset repository."""
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, desc, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models import Asset, TokenInfo, AssetMetadata, Output
from ...schemas.assets import AssetDetail, AssetSummary, AssetList

class AssetRepository:
    """Repository for asset operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository."""
        self.session = session

    async def get_asset_details(self, token_id: str) -> Optional[AssetDetail]:
        """Get asset details."""
        # Get token info
        token_result = await self.session.execute(
            select(TokenInfo)
            .where(TokenInfo.token_id == token_id)
            .options(joinedload(TokenInfo.metadata))
        )
        token = token_result.scalar_one_or_none()
        if not token:
            return None

        # Get circulating supply
        supply_result = await self.session.execute(
            select(func.sum(Asset.amount))
            .join(Output, Asset.box_id == Output.box_id)
            .where(
                Asset.token_id == token_id,
                Output.spent_by_tx_id.is_(None)
            )
        )
        circulating_supply = supply_result.scalar_one() or 0

        # Get holders count
        holders_result = await self.session.execute(
            select(func.count(func.distinct(Output.address)))
            .join(Asset, Asset.box_id == Output.box_id)
            .where(
                Asset.token_id == token_id,
                Output.spent_by_tx_id.is_(None)
            )
        )
        holders_count = holders_result.scalar_one() or 0

        # Get first and last activity
        activity_result = await self.session.execute(
            select(
                func.min(Asset.created_at),
                func.max(Asset.created_at)
            )
            .where(Asset.token_id == token_id)
        )
        first_seen, last_seen = activity_result.one()

        return AssetDetail(
            id=token_id,
            box_id=token.metadata.box_id if token.metadata else None,
            metadata={
                'name': token.name,
                'description': token.description,
                'decimals': token.decimals,
                'type': token.metadata.asset_type if token.metadata else None,
                'issuer_address': token.metadata.issuer_address if token.metadata else None,
                'additional_info': token.metadata.metadata if token.metadata else None
            },
            total_supply=token.total_supply,
            circulating_supply=circulating_supply,
            holders_count=holders_count,
            first_minted=int(first_seen.timestamp()) if first_seen else None,
            last_activity=int(last_seen.timestamp()) if last_seen else None
        )

    async def search_assets(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> AssetList:
        """Search assets by name or ID."""
        # Search query
        search_query = select(TokenInfo).where(
            or_(
                TokenInfo.name.ilike(f"%{query}%"),
                TokenInfo.token_id.ilike(f"%{query}%")
            )
        )

        # Get total count
        count_result = await self.session.execute(
            select(func.count()).select_from(search_query.subquery())
        )
        total = count_result.scalar_one()

        # Get paginated results
        result = await self.session.execute(
            search_query
            .order_by(TokenInfo.name)
            .offset(skip)
            .limit(limit)
        )
        tokens = result.scalars().all()

        return AssetList(
            items=[
                AssetSummary(
                    id=token.token_id,
                    name=token.name,
                    decimals=token.decimals,
                    total_supply=token.total_supply,
                    type=token.metadata.asset_type if token.metadata else None
                )
                for token in tokens
            ],
            total=total,
            page=skip // limit + 1,
            page_size=limit
        ) 