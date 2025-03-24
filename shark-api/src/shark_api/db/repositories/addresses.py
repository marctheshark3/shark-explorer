"""Address repository."""
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, desc
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models import Output, Asset, AddressStats
from ...schemas.addresses import AddressDetail, AddressBalance

class AddressRepository:
    """Repository for address operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository."""
        self.session = session

    async def get_address_balance(self, address: str) -> AddressBalance:
        """Get address balance."""
        # Get confirmed balance
        balance_result = await self.session.execute(
            select(func.sum(Output.value))
            .where(
                Output.address == address,
                Output.spent_by_tx_id.is_(None)
            )
        )
        confirmed = balance_result.scalar_one() or 0

        # Get asset balances
        asset_result = await self.session.execute(
            select(
                Asset.token_id,
                func.sum(Asset.amount).label('amount'),
                Asset.name,
                Asset.decimals
            )
            .join(Output, Asset.box_id == Output.box_id)
            .where(
                Output.address == address,
                Output.spent_by_tx_id.is_(None)
            )
            .group_by(Asset.token_id, Asset.name, Asset.decimals)
        )
        assets = [
            {
                'token_id': token_id,
                'amount': amount,
                'name': name,
                'decimals': decimals
            }
            for token_id, amount, name, decimals in asset_result
        ]

        return AddressBalance(
            confirmed=confirmed,
            unconfirmed=0,  # We don't track mempool yet
            assets=assets
        )

    async def get_address_stats(self, address: str) -> Optional[AddressStats]:
        """Get address statistics."""
        result = await self.session.execute(
            select(AddressStats).where(AddressStats.address == address)
        )
        return result.scalar_one_or_none()

    async def get_address_details(self, address: str) -> AddressDetail:
        """Get address details."""
        # Get balance
        balance = await self.get_address_balance(address)
        
        # Get stats
        stats = await self.get_address_stats(address)
        
        # Get first and last transaction times if no stats
        if not stats:
            time_result = await self.session.execute(
                select(
                    func.min(Output.created_at),
                    func.max(Output.created_at)
                )
                .where(Output.address == address)
            )
            first_seen, last_seen = time_result.one()
            
            # Get total received
            received_result = await self.session.execute(
                select(func.sum(Output.value))
                .where(Output.address == address)
            )
            total_received = received_result.scalar_one() or 0
            
            # Get total sent
            sent_result = await self.session.execute(
                select(func.sum(Output.value))
                .join(Output, Output.box_id == Input.box_id)
                .where(Output.address == address)
            )
            total_sent = sent_result.scalar_one() or 0
            
            stats = AddressStats(
                first_active=int(first_seen.timestamp()) if first_seen else None,
                last_active=int(last_seen.timestamp()) if last_seen else None,
                total_received=total_received,
                total_sent=total_sent
            )

        return AddressDetail(
            address=address,
            balance=balance,
            stats=stats
        ) 