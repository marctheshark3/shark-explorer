"""Status schemas."""
from typing import Optional
from pydantic import BaseModel

class NodeStatus(BaseModel):
    """Node status schema."""
    version: str
    network: str
    block_height: int
    is_mining: bool
    peers_count: int
    unconfirmed_count: int

class IndexerStatus(BaseModel):
    """Indexer status schema."""
    version: str
    block_height: int
    sync_percentage: float
    is_syncing: bool

class SystemStatus(BaseModel):
    """System status schema."""
    node: NodeStatus
    indexer: IndexerStatus

    class Config:
        from_attributes = True 