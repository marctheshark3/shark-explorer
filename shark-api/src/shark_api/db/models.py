"""Database models for the shark-api."""
from sqlalchemy import Column, Integer, String, ForeignKey, BigInteger, Float, JSON, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column, deferred
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Block(Base):
    """Block model."""
    __tablename__ = "blocks"

    id = Column(String(64), primary_key=True)
    header_id = Column(String(64), nullable=False)
    parent_id = Column(String(64), nullable=True)  # Can be null for genesis block
    height = Column(Integer, nullable=False)
    timestamp = Column(BigInteger, nullable=False)
    difficulty = Column(BigInteger, nullable=False)
    block_size = Column(Integer, nullable=False)
    block_coins = Column(BigInteger, nullable=False)
    block_mining_time = Column(BigInteger, nullable=True)
    txs_count = Column(Integer, nullable=False)
    txs_size = Column(Integer, nullable=False)
    miner_address = Column(String(64), nullable=True)
    miner_name = Column(String(128), nullable=True)
    main_chain = Column(Boolean, nullable=False)
    version = Column(Integer, nullable=False)
    transactions_root = Column(String(128), nullable=True)
    state_root = Column(String(128), nullable=True)
    pow_solutions = Column(JSONB, nullable=True)

    transactions = relationship("Transaction", back_populates="block")
    mining_rewards = relationship("MiningReward", back_populates="block")

class Transaction(Base):
    """Transaction model."""
    __tablename__ = "transactions"

    id = Column(String, primary_key=True)
    block_id = Column(String, ForeignKey("blocks.id"), nullable=False)
    header_id = Column(String, nullable=False)
    inclusion_height = Column(Integer, nullable=False)
    timestamp = Column(BigInteger, nullable=False)
    index = Column(Integer, nullable=False)
    main_chain = Column(Boolean, nullable=False)
    size = Column(Integer, nullable=False)
    fee = Column(BigInteger, nullable=True)
    status = Column(String, nullable=False, default="confirmed")

    block = relationship("Block", back_populates="transactions")
    inputs = relationship("Input", back_populates="transaction")
    outputs = relationship("Output", foreign_keys="[Output.tx_id]", back_populates="transaction")

class Input(Base):
    """Input model."""
    __tablename__ = "inputs"

    box_id = Column(String, primary_key=True)
    tx_id = Column(String, ForeignKey("transactions.id"), primary_key=True)
    index_in_tx = Column(Integer, nullable=False)
    proof_bytes = Column(String)
    extension = Column(JSON)

    transaction = relationship("Transaction", back_populates="inputs")

class Output(Base):
    """Output model."""
    __tablename__ = "outputs"

    box_id = Column(String, primary_key=True)
    tx_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    index_in_tx = Column(Integer, nullable=False)
    value = Column(BigInteger, nullable=False)
    creation_height = Column(Integer, nullable=False)
    address = Column(String)
    ergo_tree = Column(String, nullable=False)
    additional_registers = Column(JSON)
    spent_by_tx_id = Column(String, ForeignKey("transactions.id"))

    transaction = relationship("Transaction", foreign_keys=[tx_id], back_populates="outputs")
    spending_transaction = relationship("Transaction", foreign_keys=[spent_by_tx_id])
    assets = relationship("Asset", back_populates="output")

class Asset(Base):
    """Asset model."""
    __tablename__ = "assets"

    id = Column(String, primary_key=True)
    box_id = Column(String, ForeignKey("outputs.box_id"), nullable=False)
    index_in_outputs = Column(Integer, nullable=False)
    token_id = Column(String, nullable=False)
    amount = Column(BigInteger, nullable=False)
    name = Column(String)
    decimals = Column(Integer)

    output = relationship("Output", back_populates="assets")

class MiningReward(Base):
    """Mining reward model."""
    __tablename__ = "mining_rewards"

    block_id = Column(String, ForeignKey("blocks.id"), primary_key=True)
    reward_amount = Column(BigInteger, nullable=False)
    fees_amount = Column(BigInteger, nullable=False)
    miner_address = Column(String)

    block = relationship("Block", back_populates="mining_rewards")

class AddressStats(Base):
    """Address statistics model."""
    __tablename__ = "address_stats"

    address = Column(String, primary_key=True)
    first_active_time = Column(BigInteger)
    last_active_time = Column(BigInteger)
    address_type = Column(String)
    script_complexity = Column(Integer)

class TokenInfo(Base):
    """Token information model."""
    __tablename__ = "token_info"

    id = Column(String, primary_key=True)  # token_id
    box_id = Column(String)
    total_supply = Column(Integer)
    circulating_supply = Column(Integer)
    holders_count = Column(Integer, nullable=True)
    first_minted = Column(Integer, nullable=True)
    last_activity = Column(Integer, nullable=True)
    asset_metadata = relationship("AssetMetadata", back_populates="token", uselist=False)

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