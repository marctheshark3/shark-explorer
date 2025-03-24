"""Asset schemas."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .base import TimestampMixin, PaginatedResponse

class AssetMetadata(BaseModel):
    """Asset metadata schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    decimals: Optional[int] = None
    type: Optional[str] = None
    issuer_address: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None

class AssetDetail(TimestampMixin):
    """Detailed asset schema."""
    id: str = Field(..., description="Token ID")
    box_id: str = Field(..., description="Box where token was minted")
    metadata: AssetMetadata
    total_supply: int
    circulating_supply: int
    holders_count: Optional[int] = None
    first_minted: Optional[int] = None
    last_activity: Optional[int] = None

class AssetSummary(BaseModel):
    """Asset summary schema for search results."""
    id: str
    name: Optional[str] = None
    decimals: Optional[int] = None
    total_supply: int
    type: Optional[str] = None

class AssetList(PaginatedResponse[AssetSummary]):
    """Asset list response schema."""
    pass 