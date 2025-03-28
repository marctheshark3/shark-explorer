"""Transaction repository."""
from typing import Optional, List, Dict, Any
from sqlalchemy import select, desc, func, text
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from .base import BaseRepository
from ..models import Transaction, Input, Output, Asset
from ...schemas.transactions import TransactionDetail, AddressTransaction

logger = logging.getLogger(__name__)

class TransactionRepository(BaseRepository[Transaction]):
    """Repository for transaction operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize repository."""
        super().__init__(Transaction, session)

    async def get_transaction_with_details(self, tx_id: str) -> Optional[TransactionDetail]:
        """Get transaction with all details."""
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.id == tx_id)
            .options(
                joinedload(Transaction.inputs),
                joinedload(Transaction.outputs).joinedload(Output.assets)
            )
        )
        tx = result.scalar_one_or_none()
        if not tx:
            return None

        # Get current height for confirmations
        height_result = await self.session.execute(
            select(func.max(Transaction.inclusion_height))
        )
        current_height = height_result.scalar_one() or tx.inclusion_height
        confirmations = current_height - tx.inclusion_height + 1

        return TransactionDetail(
            **tx.__dict__,
            inputs=[input.__dict__ for input in tx.inputs],
            outputs=[{
                **output.__dict__,
                'assets': [asset.__dict__ for asset in output.assets]
            } for output in tx.outputs],
            confirmations=confirmations
        )

    async def get_address_transactions(
        self,
        address: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AddressTransaction]:
        """Get transactions for address."""
        # Get transactions where address is in inputs
        input_txs = await self.session.execute(
            select(Transaction, Input)
            .join(Input, Transaction.id == Input.tx_id)
            .join(Output, Input.box_id == Output.box_id)
            .where(Output.address == address)
            .order_by(desc(Transaction.timestamp))
            .offset(skip)
            .limit(limit)
        )

        # Get transactions where address is in outputs
        output_txs = await self.session.execute(
            select(Transaction, Output)
            .join(Output, Transaction.id == Output.tx_id)
            .where(Output.address == address)
            .order_by(desc(Transaction.timestamp))
            .offset(skip)
            .limit(limit)
        )

        # Combine and format results
        transactions = []
        for tx, box in input_txs:
            transactions.append(
                AddressTransaction(
                    id=tx.id,
                    timestamp=tx.timestamp,
                    type="input",
                    value=box.value,
                    assets=[asset.__dict__ for asset in box.assets]
                )
            )

        for tx, output in output_txs:
            transactions.append(
                AddressTransaction(
                    id=tx.id,
                    timestamp=tx.timestamp,
                    type="output",
                    value=output.value,
                    assets=[asset.__dict__ for asset in output.assets]
                )
            )

        # Sort by timestamp
        transactions.sort(key=lambda x: x.timestamp, reverse=True)
        return transactions[:limit]

    async def count_address_transactions(self, address: str) -> int:
        """Count transactions for address."""
        # Count inputs
        input_count = await self.session.execute(
            select(func.count(Transaction.id))
            .join(Input, Transaction.id == Input.tx_id)
            .join(Output, Input.box_id == Output.box_id)
            .where(Output.address == address)
        )

        # Count outputs
        output_count = await self.session.execute(
            select(func.count(Transaction.id))
            .join(Output, Transaction.id == Output.tx_id)
            .where(Output.address == address)
        )

        return (input_count.scalar_one() or 0) + (output_count.scalar_one() or 0)
        
    async def get_total_count(self) -> int:
        """
        Get the total count of transactions using a direct SQL query for performance.
        
        Returns:
            int: The total count of transactions in the database
        """
        try:
            # Use direct SQL for better performance on large tables
            result = await self.session.execute(text("SELECT COUNT(*) FROM transactions"))
            count = result.scalar_one() or 0
            
            # Log the count for debugging
            logger.info(f"Transaction count from direct SQL: {count}")
            
            # If the count is zero but we know there should be transactions,
            # fall back to the SQLAlchemy query as a verification
            if count == 0:
                logger.warning("Direct SQL count returned zero, verifying with SQLAlchemy query")
                backup_query = select(func.count()).select_from(Transaction)
                backup_result = await self.session.execute(backup_query)
                backup_count = backup_result.scalar_one() or 0
                
                if backup_count > 0:
                    logger.warning(f"SQLAlchemy query returned {backup_count} transactions, using this count instead")
                    return backup_count
            
            return count
        except Exception as e:
            logger.error(f"Error getting transaction count: {e}")
            # Return 0 instead of raising to avoid breaking metrics
            return 0 