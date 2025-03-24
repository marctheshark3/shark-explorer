from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, BigInteger, ForeignKey, 
    DateTime, Boolean, Numeric, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Block(Base):
    __tablename__ = 'blocks'

    id = Column(String(64), primary_key=True)
    header_id = Column(String(64), nullable=False)
    parent_id = Column(String(64), nullable=True)
    height = Column(Integer, nullable=False)
    timestamp = Column(BigInteger, nullable=False)
    difficulty = Column(BigInteger, nullable=False)
    block_size = Column(Integer, nullable=False)
    block_coins = Column(BigInteger, nullable=False)
    block_mining_time = Column(BigInteger)
    txs_count = Column(Integer, nullable=False)
    txs_size = Column(Integer, nullable=False)
    miner_address = Column(String(64))
    miner_name = Column(String(128))
    main_chain = Column(Boolean, nullable=False)
    version = Column(Integer, nullable=False)
    transactions_root = Column(String(64))
    state_root = Column(String(64))
    pow_solutions = Column(JSONB)

    transactions = relationship("Transaction", back_populates="block")
    mining_reward = relationship("MiningReward", back_populates="block", uselist=False)

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(String(64), primary_key=True)
    block_id = Column(String(64), ForeignKey('blocks.id'), nullable=False)
    header_id = Column(String(64), nullable=False)
    inclusion_height = Column(Integer, nullable=False)
    timestamp = Column(BigInteger, nullable=False)
    index = Column(Integer, nullable=False)
    main_chain = Column(Boolean, nullable=False)
    size = Column(Integer, nullable=False)

    block = relationship("Block", back_populates="transactions")
    inputs = relationship("Input", back_populates="transaction")
    outputs = relationship("Output", primaryjoin="Transaction.id == Output.tx_id", back_populates="transaction")
    spent_outputs = relationship(
        "Output",
        primaryjoin="Transaction.id == Output.spent_by_tx_id",
        viewonly=True
    )

class Input(Base):
    __tablename__ = 'inputs'

    box_id = Column(String(64), primary_key=True)
    tx_id = Column(String(64), ForeignKey('transactions.id'), primary_key=True)
    index_in_tx = Column(Integer, nullable=False)
    proof_bytes = Column(Text)
    extension = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="inputs")

class Output(Base):
    __tablename__ = 'outputs'

    box_id = Column(String(64), primary_key=True)
    tx_id = Column(String(64), ForeignKey('transactions.id'), nullable=False)
    index_in_tx = Column(Integer, nullable=False)
    value = Column(BigInteger, nullable=False)
    creation_height = Column(Integer, nullable=False)
    address = Column(String(64))
    ergo_tree = Column(Text, nullable=False)
    additional_registers = Column(JSON)
    spent_by_tx_id = Column(String(64), ForeignKey('transactions.id'))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    transaction = relationship("Transaction", foreign_keys=[tx_id], back_populates="outputs")
    spent_by = relationship(
        "Transaction",
        foreign_keys=[spent_by_tx_id],
        viewonly=True
    )
    assets = relationship("Asset", back_populates="output")

class Asset(Base):
    __tablename__ = 'assets'

    id = Column(String(64), primary_key=True)
    box_id = Column(String(64), ForeignKey('outputs.box_id'), nullable=False)
    index_in_outputs = Column(Integer, nullable=False)
    token_id = Column(String(64), nullable=False)
    amount = Column(BigInteger, nullable=False)
    name = Column(String(255))
    decimals = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    output = relationship("Output", back_populates="assets")

class TokenInfo(Base):
    __tablename__ = 'token_info'

    token_id = Column(String(64), primary_key=True)
    name = Column(String(255))
    description = Column(Text)
    decimals = Column(Integer)
    total_supply = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class SyncStatus(Base):
    __tablename__ = 'sync_status'

    id = Column(Integer, primary_key=True, default=1)
    current_height = Column(Integer, nullable=False)
    target_height = Column(Integer, nullable=False)
    is_syncing = Column(Boolean, default=False)
    last_block_time = Column(BigInteger)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('id', name='sync_status_single_row'),
    )

class MiningReward(Base):
    __tablename__ = 'mining_rewards'

    block_id = Column(String(64), ForeignKey('blocks.id'), primary_key=True)
    reward_amount = Column(BigInteger, nullable=False)
    fees_amount = Column(BigInteger, nullable=False)
    miner_address = Column(String(64))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    block = relationship("Block", back_populates="mining_reward")

class AssetMetadata(Base):
    __tablename__ = 'asset_metadata'

    token_id = Column(String(64), ForeignKey('token_info.token_id'), primary_key=True)
    asset_type = Column(String(32))
    issuer_address = Column(String(64))
    minting_tx_id = Column(String(64), ForeignKey('transactions.id'))
    asset_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    token_info = relationship("TokenInfo", back_populates="metadata")
    minting_tx = relationship("Transaction")

class AddressStats(Base):
    __tablename__ = 'address_stats'

    address = Column(String(64), primary_key=True)
    first_active_time = Column(BigInteger)
    last_active_time = Column(BigInteger)
    address_type = Column(String(32))
    script_complexity = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)