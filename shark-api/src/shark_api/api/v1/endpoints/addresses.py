"""Address endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ....db.dependencies import get_db
from ....db.repositories.addresses import AddressRepository
from ....schemas.addresses import AddressBalance, AddressStats, AddressDetail

router = APIRouter()

@router.get("/{address}/balance", response_model=AddressBalance)
async def get_address_balance(
    address: str,
    db: AsyncSession = Depends(get_db)
) -> AddressBalance:
    """Get address balance."""
    repo = AddressRepository(db)
    balance = await repo.get_address_balance(address)
    if not balance:
        raise HTTPException(status_code=404, detail="Address not found")
    return AddressBalance.from_orm(balance)

@router.get("/{address}/stats", response_model=AddressStats)
async def get_address_stats(
    address: str,
    db: AsyncSession = Depends(get_db)
) -> AddressStats:
    """Get address statistics."""
    repo = AddressRepository(db)
    stats = await repo.get_address_stats(address)
    if not stats:
        raise HTTPException(status_code=404, detail="Address not found")
    return AddressStats.from_orm(stats)

@router.get("/{address}", response_model=AddressDetail)
async def get_address_details(
    address: str,
    db: AsyncSession = Depends(get_db)
) -> AddressDetail:
    """Get address details."""
    repo = AddressRepository(db)
    details = await repo.get_address_details(address)
    if not details:
        raise HTTPException(status_code=404, detail="Address not found")
    return AddressDetail.from_orm(details) 