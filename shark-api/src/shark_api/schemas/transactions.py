"""Transaction schemas."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .base import TimestampMixin, PaginatedResponse

class AssetBase(BaseModel):
    """Base asset schema."""
    token_id: str
    amount: int
    name: Optional[str] = None
    decimals: Optional[int] = None

class InputBase(BaseModel):
    """Base input schema."""
    box_id: str
    index_in_tx: int = Field(..., alias="index")
    proof_bytes: Optional[str] = None
    extension: Optional[Dict[str, Any]] = None

class OutputBase(BaseModel):
    """Base output schema."""
    box_id: str
    index_in_tx: int = Field(..., alias="index")
    value: int
    creation_height: int
    address: Optional[str] = None
    ergo_tree: str
    assets: List[AssetBase] = []
    additional_registers: Dict[str, Any] = {}

class TransactionBase(BaseModel):
    """Base transaction schema."""
    id: str
    block_id: str
    timestamp: int
    index: int
    size: int
    fee: Optional[int] = None

class TransactionDetail(TransactionBase, TimestampMixin):
    """Detailed transaction schema."""
    inputs: List[InputBase] = []
    outputs: List[OutputBase] = []
    inclusion_height: int
    confirmations: Optional[int] = None
    
    class Config:
        """Pydantic config."""
        allow_population_by_field_name = True

class AddressTransaction(BaseModel):
    """Transaction schema for address endpoints."""
    id: str
    timestamp: int
    type: str = Field(..., description="input/output")
    value: int
    assets: List[AssetBase] = []

class TransactionList(PaginatedResponse[TransactionBase]):
    """Transaction list response schema."""
    pass

class AddressTransactionList(PaginatedResponse[AddressTransaction]):
    """Address transaction list response schema."""
    pass 