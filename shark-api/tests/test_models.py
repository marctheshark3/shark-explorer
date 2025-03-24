import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from shark_api.db.models import Block, Transaction, Input, Output, Asset

@pytest.mark.asyncio
async def test_block_model(db_session: AsyncSession, test_block_data):
    """Test Block model creation and relationships."""
    block = Block(**test_block_data)
    db_session.add(block)
    await db_session.commit()
    await db_session.refresh(block)

    assert block.id == test_block_data["id"]
    assert block.height == test_block_data["height"]
    assert block.timestamp == test_block_data["timestamp"]
    assert block.parent_id == test_block_data["parent_id"]
    assert block.difficulty == test_block_data["difficulty"]
    assert block.block_size == test_block_data["block_size"]

@pytest.mark.asyncio
async def test_transaction_model(db_session: AsyncSession, test_block_data, test_transaction_data):
    """Test Transaction model creation and relationships."""
    # Create block first
    block = Block(**test_block_data)
    db_session.add(block)
    await db_session.commit()

    # Create transaction
    transaction = Transaction(**test_transaction_data)
    db_session.add(transaction)
    await db_session.commit()
    await db_session.refresh(transaction)

    assert transaction.id == test_transaction_data["id"]
    assert transaction.block_id == test_transaction_data["block_id"]
    assert transaction.timestamp == test_transaction_data["timestamp"]
    assert transaction.index == test_transaction_data["index"]
    assert transaction.size == test_transaction_data["size"]

@pytest.mark.asyncio
async def test_input_output_relationship(db_session: AsyncSession, test_transaction_data):
    """Test Input and Output models and their relationships."""
    # Create transaction
    transaction = Transaction(**test_transaction_data)
    db_session.add(transaction)
    await db_session.commit()

    # Create input
    input_data = {
        "box_id": "test_input_box",
        "tx_id": transaction.id,
        "index_in_tx": 0,
        "proof_bytes": "test_proof"
    }
    input_box = Input(**input_data)
    db_session.add(input_box)

    # Create output
    output_data = {
        "box_id": "test_output_box",
        "tx_id": transaction.id,
        "index_in_tx": 0,
        "value": 1000000,
        "creation_height": 1000000,
        "address": "test_address",
        "ergo_tree": "test_ergo_tree"
    }
    output_box = Output(**output_data)
    db_session.add(output_box)

    await db_session.commit()
    await db_session.refresh(transaction)

    assert len(transaction.inputs) == 1
    assert len(transaction.outputs) == 1
    assert transaction.inputs[0].box_id == input_data["box_id"]
    assert transaction.outputs[0].box_id == output_data["box_id"]

@pytest.mark.asyncio
async def test_asset_model(db_session: AsyncSession, test_asset_data):
    """Test Asset model creation."""
    # Create output first
    output_data = {
        "box_id": test_asset_data["box_id"],
        "tx_id": "test_tx_id",
        "index_in_tx": 0,
        "value": 1000000,
        "creation_height": 1000000,
        "address": "test_address",
        "ergo_tree": "test_ergo_tree"
    }
    output = Output(**output_data)
    db_session.add(output)
    await db_session.commit()

    # Create asset
    asset = Asset(**test_asset_data)
    db_session.add(asset)
    await db_session.commit()
    await db_session.refresh(asset)

    assert asset.id == test_asset_data["id"]
    assert asset.box_id == test_asset_data["box_id"]
    assert asset.token_id == test_asset_data["token_id"]
    assert asset.amount == test_asset_data["amount"]
    assert asset.name == test_asset_data["name"]
    assert asset.decimals == test_asset_data["decimals"] 