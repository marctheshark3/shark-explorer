"""Schemas for block-related data."""
from typing import List, Dict, Optional
from pydantic import BaseModel


class BlockBase(BaseModel):
    """Base block schema."""
    id: str
    header_id: str
    parent_id: Optional[str]
    height: int
    timestamp: int
    difficulty: int
    block_size: int
    block_coins: int
    block_mining_time: Optional[int]
    txs_count: int
    txs_size: int
    miner_address: Optional[str]
    miner_name: Optional[str]
    main_chain: bool
    version: int
    transactions_root: Optional[str]
    state_root: Optional[str]
    pow_solutions: Optional[Dict]

    class Config:
        from_attributes = True


class BlockHeader(BlockBase):
    """Block header schema."""
    pass


class TransactionBase(BaseModel):
    """Base transaction schema."""
    id: str
    block_id: str
    header_id: str
    inclusion_height: int
    timestamp: int
    index: int
    main_chain: bool
    size: int

    class Config:
        from_attributes = True


class MiningRewardBase(BaseModel):
    """Base mining reward schema."""
    block_id: str
    reward_amount: int
    fees_amount: int
    miner_address: Optional[str]

    class Config:
        from_attributes = True


class BlockDetail(BaseModel):
    """Block detail schema."""
    block: BlockBase
    transactions: List[TransactionBase]
    mining_rewards: List[MiningRewardBase]

    class Config:
        from_attributes = True


class BlockDetail(BaseModel):
    """Block detail schema."""
    block: BlockBase
    transactions: List[TransactionBase] = []
    mining_rewards: List[MiningRewardBase] = []
    
    @classmethod
    def from_orm(cls, obj):
        """Create from ORM object."""
        if isinstance(obj, dict):
            return cls(**obj)
        
        # If the object has all the attributes directly, use it
        if hasattr(obj, "block") and hasattr(obj, "transactions") and hasattr(obj, "mining_rewards"):
            return cls(
                block=obj.block,
                transactions=obj.transactions,
                mining_rewards=obj.mining_rewards
            )
        
        # Otherwise, assume the object is a Block and create the BlockDetail
        return cls(
            block=obj,
            transactions=getattr(obj, "transactions", []),
            mining_rewards=getattr(obj, "mining_rewards", [])
        )

    class Config:
        from_attributes = True