"""Address schemas."""
from typing import List, Optional
from pydantic import BaseModel
from .base import TimestampMixin
from .transactions import AssetBase

class AddressBalance(BaseModel):
    """Address balance schema."""
    confirmed: int
    unconfirmed: int = 0
    assets: List[AssetBase] = []

class AddressStats(BaseModel):
    """Address statistics schema."""
    first_active: Optional[int] = None
    last_active: Optional[int] = None
    total_transactions: int = 0
    total_received: int = 0
    total_sent: int = 0

class AddressDetail(TimestampMixin):
    """Detailed address schema."""
    address: str
    balance: AddressBalance
    stats: AddressStats
    script_type: Optional[str] = None
    script_complexity: Optional[int] = None 