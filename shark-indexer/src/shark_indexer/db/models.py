from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, BigInteger, ForeignKey, 
    DateTime, Boolean, Numeric, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, JSON
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship,
    registry
)

# Create a new registry
mapper_registry = registry()

# Create a new base class using the registry
class Base(DeclarativeBase):
    registry = mapper_registry

class Block(Base):
    __tablename__ = 'blocks'

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    header_id: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    difficulty: Mapped[int] = mapped_column(BigInteger, nullable=False)
    block_size: Mapped[int] = mapped_column(Integer, nullable=False)
    block_coins: Mapped[int] = mapped_column(BigInteger, nullable=False)
    block_mining_time: Mapped[Optional[int]] = mapped_column(BigInteger)
    txs_count: Mapped[int] = mapped_column(Integer, nullable=False)
    txs_size: Mapped[int] = mapped_column(Integer, nullable=False)
    miner_address: Mapped[Optional[str]] = mapped_column(String(64))
    miner_name: Mapped[Optional[str]] = mapped_column(String(128))
    main_chain: Mapped[bool] = mapped_column(Boolean, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    transactions_root: Mapped[Optional[str]] = mapped_column(String(128))
    state_root: Mapped[Optional[str]] = mapped_column(String(128))
    pow_solutions: Mapped[Optional[dict]] = mapped_column(JSONB)

    transactions = relationship("Transaction", back_populates="block")
    mining_reward = relationship("MiningReward", back_populates="block", uselist=False)

class Transaction(Base):
    __tablename__ = 'transactions'

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    block_id: Mapped[str] = mapped_column(String(64), ForeignKey('blocks.id'), nullable=False)
    header_id: Mapped[str] = mapped_column(String(64), nullable=False)
    inclusion_height: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    main_chain: Mapped[bool] = mapped_column(Boolean, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    fee: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

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

    box_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tx_id: Mapped[str] = mapped_column(String(64), ForeignKey('transactions.id'), primary_key=True)
    index_in_tx: Mapped[int] = mapped_column(Integer, nullable=False)
    proof_bytes: Mapped[Optional[str]] = mapped_column(Text)
    extension: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="inputs")

class Output(Base):
    __tablename__ = 'outputs'

    box_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tx_id: Mapped[str] = mapped_column(String(64), ForeignKey('transactions.id'), nullable=False)
    index_in_tx: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    creation_height: Mapped[int] = mapped_column(Integer, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(64))
    ergo_tree: Mapped[str] = mapped_column(Text, nullable=False)
    additional_registers: Mapped[Optional[dict]] = mapped_column(JSON)
    spent_by_tx_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey('transactions.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    transaction = relationship("Transaction", foreign_keys=[tx_id], back_populates="outputs")
    spent_by = relationship(
        "Transaction",
        foreign_keys=[spent_by_tx_id],
        viewonly=True
    )
    assets = relationship("Asset", back_populates="output")

class Asset(Base):
    __tablename__ = 'assets'

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    box_id: Mapped[str] = mapped_column(String(64), ForeignKey('outputs.box_id'), nullable=False)
    index_in_outputs: Mapped[int] = mapped_column(Integer, nullable=False)
    token_id: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    decimals: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    output = relationship("Output", back_populates="assets")

class TokenInfo(Base):
    """Token information model."""
    __tablename__ = "token_info"

    id = Column(String, primary_key=True)  # token_id
    box_id = Column(String, nullable=True)
    total_supply = Column(Integer, nullable=True)
    circulating_supply = Column(Integer, nullable=True)
    holders_count = Column(Integer, nullable=True)
    first_minted = Column(Integer, nullable=True)
    last_activity = Column(Integer, nullable=True)
    asset_metadata = relationship("AssetMetadata", back_populates="token", uselist=False)

class SyncStatus(Base):
    __tablename__ = 'sync_status'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    current_height: Mapped[int] = mapped_column(Integer, nullable=False)
    target_height: Mapped[int] = mapped_column(Integer, nullable=False)
    is_syncing: Mapped[bool] = mapped_column(Boolean, default=False)
    last_block_time: Mapped[Optional[int]] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('id', name='sync_status_single_row'),
    )

class MiningReward(Base):
    __tablename__ = 'mining_rewards'

    block_id: Mapped[str] = mapped_column(String(64), ForeignKey('blocks.id'), primary_key=True)
    reward_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fees_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    miner_address: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    block = relationship("Block", back_populates="mining_reward")

class AssetMetadata(Base):
    """Asset metadata model."""
    __tablename__ = "asset_metadata"

    token_id = Column(String, ForeignKey("token_info.id"), primary_key=True)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    decimals = Column(Integer, nullable=True)
    type = Column(String, nullable=True)
    issuer_address = Column(String, nullable=True)
    additional_info = Column(JSON, nullable=True)
    token = relationship("TokenInfo", back_populates="asset_metadata")

class AddressStats(Base):
    __tablename__ = 'address_stats'

    address: Mapped[str] = mapped_column(String(64), primary_key=True)
    first_active_time: Mapped[Optional[int]] = mapped_column(BigInteger)
    last_active_time: Mapped[Optional[int]] = mapped_column(BigInteger)
    address_type: Mapped[Optional[str]] = mapped_column(String(32))
    script_complexity: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)