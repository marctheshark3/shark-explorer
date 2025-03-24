"""Transaction endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....db.dependencies import get_db
from ....db.repositories.transactions import TransactionRepository
from ....schemas.transactions import TransactionDetail, AddressTransaction
from ....schemas.base import PaginatedResponse

router = APIRouter()

@router.get("/{tx_id}", response_model=TransactionDetail)
async def get_transaction(
    tx_id: str,
    db: AsyncSession = Depends(get_db)
) -> TransactionDetail:
    """Get transaction by ID."""
    repo = TransactionRepository(db)
    tx = await repo.get_transaction_with_details(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionDetail.from_orm(tx)

@router.get("/address/{address}", response_model=PaginatedResponse[AddressTransaction])
async def get_address_transactions(
    address: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[AddressTransaction]:
    """Get transactions for address."""
    repo = TransactionRepository(db)
    
    # Get transactions
    transactions = await repo.get_address_transactions(
        address=address,
        skip=offset,
        limit=limit
    )
    total = await repo.count_address_transactions(address)
    
    return PaginatedResponse(
        items=[AddressTransaction.from_orm(tx) for tx in transactions],
        total=total,
        offset=offset,
        limit=limit
    ) 