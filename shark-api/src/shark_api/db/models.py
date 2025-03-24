"""Database models for the shark-api."""
from sqlalchemy import Column, Integer, String, ForeignKey, BigInteger, Float, JSON, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Block(Base):
    """Block model."""
    __tablename__ = "blocks"

    id = Column(String, primary_key=True)
    height = Column(Integer, nullable=False, index=True)
    timestamp = Column(BigInteger, nullable=False)
    difficulty = Column(BigInteger, nullable=False)
    block_size = Column(Integer, nullable=False)
    block_coins = Column(Float, nullable=False)
    block_mining_time = Column(Integer, nullable=False)
    txs_count = Column(Integer, nullable=False)
    miner_address = Column(String, nullable=False)
    miner_name = Column(String, nullable=True)
    block_fee = Column(Float, nullable=False)
    block_chain_total_size = Column(BigInteger, nullable=False)
    main_chain = Column(Boolean, nullable=False)
    parent_id = Column(String, nullable=False)
    extension_hash = Column(String, nullable=False)
    version = Column(Integer, nullable=False)
    votes = Column(String, nullable=False)
    ad_proofs_root = Column(String, nullable=False)
    state_root = Column(String, nullable=False)
    transactions_root = Column(String, nullable=False)
    pow_solutions = Column(JSON, nullable=False)

    transactions = relationship("Transaction", back_populates="block")
    mining_rewards = relationship("MiningReward", back_populates="block")

class Transaction(Base):
    """Transaction model."""
    __tablename__ = "transactions"

    id = Column(String, primary_key=True)
    block_id = Column(String, ForeignKey("blocks.id"), nullable=False)
    timestamp = Column(BigInteger, nullable=False)
    size = Column(Integer, nullable=False)
    index = Column(Integer, nullable=False)
    global_index = Column(BigInteger, nullable=False)
    inputs_count = Column(Integer, nullable=False)
    outputs_count = Column(Integer, nullable=False)
    inputs_raw = Column(String, nullable=False)
    outputs_raw = Column(String, nullable=False)
    total_value = Column(Float, nullable=False)
    fee = Column(BigInteger, nullable=True)
    inclusion_height = Column(Integer, nullable=False)

    block = relationship("Block", back_populates="transactions")
    inputs = relationship("Input", back_populates="transaction")
    outputs = relationship("Output", back_populates="transaction")

class Input(Base):
    """Input model."""
    __tablename__ = "inputs"

    id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    box_id = Column(String, nullable=False)
    index_in_tx = Column(Integer, nullable=False)
    proof_bytes = Column(String, nullable=True)
    extension = Column(JSON, nullable=True)

    transaction = relationship("Transaction", back_populates="inputs")

class Output(Base):
    """Output model."""
    __tablename__ = "outputs"

    id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    box_id = Column(String, nullable=False)
    index_in_tx = Column(Integer, nullable=False)
    value = Column(BigInteger, nullable=False)
    creation_height = Column(Integer, nullable=False)
    address = Column(String, nullable=True)
    ergo_tree = Column(String, nullable=False)
    additional_registers = Column(JSON, nullable=False)

    transaction = relationship("Transaction", back_populates="outputs")
    assets = relationship("Asset", back_populates="output")

class Asset(Base):
    """Asset model."""
    __tablename__ = "assets"

    id = Column(String, primary_key=True)
    output_id = Column(String, ForeignKey("outputs.id"), nullable=False)
    token_id = Column(String, nullable=False)
    amount = Column(BigInteger, nullable=False)
    name = Column(String, nullable=True)
    decimals = Column(Integer, nullable=True)

    output = relationship("Output", back_populates="assets")

class MiningReward(Base):
    """Mining reward model."""
    __tablename__ = "mining_rewards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    block_id = Column(String, ForeignKey("blocks.id"), nullable=False)
    address = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    type = Column(String, nullable=False)

    block = relationship("Block", back_populates="mining_rewards")

class AddressStats(Base):
    """Address statistics model."""
    __tablename__ = 'address_stats'

    address = Column(String, primary_key=True)
    first_active = Column(Integer)
    last_active = Column(Integer)
    total_transactions = Column(Integer, nullable=False, default=0)
    total_received = Column(Integer, nullable=False, default=0)
    total_sent = Column(Integer, nullable=False, default=0)

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