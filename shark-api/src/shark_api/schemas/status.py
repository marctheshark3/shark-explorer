"""Status schemas."""
from typing import Optional
from pydantic import BaseModel

class NodeStatus(BaseModel):
    """Node status schema."""
    height: int
    headerId: str
    lastBlockTime: int
    isMining: bool
    peersCount: int
    unconfirmedCount: int

class IndexerStatus(BaseModel):
    """Indexer status schema."""
    height: int
    synced: bool
    processing: bool
    last_block_time: int
    sync_percent: float
    blocks_remaining: int
    estimated_time_remaining: Optional[int] = None

class SystemStatus(BaseModel):
    """System status schema."""
    node: NodeStatus
    indexer: IndexerStatus
    api_version: str
    uptime: int 