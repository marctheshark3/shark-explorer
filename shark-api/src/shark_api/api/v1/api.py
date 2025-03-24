"""API router configuration."""
from fastapi import APIRouter

from .endpoints import (
    blocks,
    transactions,
    addresses,
    assets,
    search,
    status
)

# Create API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(blocks.router, prefix="/blocks", tags=["blocks"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(addresses.router, prefix="/addresses", tags=["addresses"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(status.router, prefix="/status", tags=["status"]) 