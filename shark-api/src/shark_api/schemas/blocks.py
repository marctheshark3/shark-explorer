"""Schemas for block-related data."""
from typing import List
from pydantic import BaseModel


class BlockBase(BaseModel):
    """Base block schema."""
    id: str
    height: int
    timestamp: int
    difficulty: int
    block_size: int
    block_coins: int
    block_mining_time: int
    txs_count: int
    miner_address: str
    miner_name: str
    block_fee: int
    block_chain_total_size: int
    main_chain: bool
    parent_id: str
    extension_hash: str
    version: int
    votes: str
    ad_proofs_root: str
    state_root: str
    transactions_root: str
    pow_solutions: str

    class Config:
        from_attributes = True


class BlockHeader(BlockBase):
    """Block header schema."""
    pass


class TransactionBase(BaseModel):
    """Base transaction schema."""
    id: str
    block_id: str
    timestamp: int
    size: int
    index: int
    global_index: int
    inputs_count: int
    outputs_count: int
    inputs_raw: str
    outputs_raw: str
    total_value: int

    class Config:
        from_attributes = True


class MiningRewardBase(BaseModel):
    """Base mining reward schema."""
    id: str
    block_id: str
    address: str
    value: int
    type: str

    class Config:
        from_attributes = True


class BlockDetail(BaseModel):
    """Block detail schema."""
    block: BlockBase
    transactions: List[TransactionBase]
    mining_rewards: List[MiningRewardBase]

    class Config:
        from_attributes = True