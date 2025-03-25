"""
Token related models.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class TokenInfo(BaseModel):
    """Token information model."""
    tokenId: str
    name: Optional[str] = None
    description: Optional[str] = None
    decimals: int = 0
    totalSupply: Optional[int] = None


class TokenHolder(BaseModel):
    """Token holder model with balance information."""
    address: str
    balance: int
    percentage: float = Field(..., description="Percentage of total supply held by this address")


class TokenHolderResponse(BaseModel):
    """Response model for token holders endpoint."""
    token: TokenInfo
    holders: List[TokenHolder]
    total: int = Field(..., description="Total number of holders")
    limit: int
    offset: int


class TokenWithHolderCount(BaseModel):
    """Token model with holder count."""
    tokenId: str
    name: Optional[str] = None
    description: Optional[str] = None
    decimals: int = 0
    totalSupply: Optional[int] = None
    holderCount: int


class TopTokensResponse(BaseModel):
    """Response model for top tokens endpoint."""
    tokens: List[TokenWithHolderCount]
    total: int = Field(..., description="Total number of tokens")
    limit: int
    offset: int


class AddressToken(BaseModel):
    """Token balance for an address."""
    tokenId: str
    name: Optional[str] = None
    description: Optional[str] = None
    decimals: int = 0
    balance: int


class AddressTokensResponse(BaseModel):
    """Response model for address tokens endpoint."""
    address: str
    tokens: List[AddressToken]
    total: int = Field(..., description="Total number of tokens held by this address")
    limit: int
    offset: int 