"""Search schemas."""
from typing import List, Optional
from pydantic import BaseModel
from .blocks import BlockBase
from .transactions import TransactionBase
from .addresses import AddressBalance

class SearchResult(BaseModel):
    """Search result schema."""
    blocks: List[BlockBase] = []
    transactions: List[TransactionBase] = []
    addresses: List[str] = []
    assets: List[str] = []
    total_blocks: int = 0
    total_transactions: int = 0
    total_addresses: int = 0
    total_assets: int = 0 