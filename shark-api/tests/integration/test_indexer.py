import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from shark_api.db.models import Block, Transaction, Input, Output, Asset
from shark_api.db.repositories.blocks import BlockRepository
from shark_api.db.repositories.transactions import TransactionRepository
from shark_api.db.repositories.addresses import AddressRepository

@pytest.mark.integration
@pytest.mark.asyncio
async def test_block_indexing_flow(db_session: AsyncSession, test_block_data, test_transaction_data):
    """Test the complete flow of indexing a block with transactions."""
    # Create repositories
    block_repo = BlockRepository(db_session)
    tx_repo = TransactionRepository(db_session)

    # Create block with transaction
    block = Block(**test_block_data)
    db_session.add(block)
    await db_session.commit()

    transaction = Transaction(**test_transaction_data)
    db_session.add(transaction)
    await db_session.commit()

    # Test block retrieval
    indexed_block = await block_repo.get_by_height(test_block_data["height"])
    assert indexed_block is not None
    assert indexed_block.id == test_block_data["id"]

    # Test transaction retrieval
    tx_details = await tx_repo.get_transaction_with_details(test_transaction_data["id"])
    assert tx_details is not None
    assert tx_details.id == test_transaction_data["id"]

@pytest.mark.integration
@pytest.mark.asyncio
async def test_address_balance_flow(db_session: AsyncSession):
    """Test the flow of tracking address balances through transactions."""
    # Create repositories
    address_repo = AddressRepository(db_session)

    # Create test data
    address = "test_address"
    value = 1000000

    # Create output (UTXO)
    output_data = {
        "box_id": "test_box",
        "tx_id": "test_tx",
        "index_in_tx": 0,
        "value": value,
        "creation_height": 1000000,
        "address": address,
        "ergo_tree": "test_ergo_tree"
    }
    output = Output(**output_data)
    db_session.add(output)
    await db_session.commit()

    # Test balance calculation
    balance = await address_repo.get_address_balance(address)
    assert balance is not None
    assert balance.confirmed == value

    # Test spending the output
    output.spent_by_tx_id = "spending_tx"
    await db_session.commit()

    # Test balance after spending
    balance = await address_repo.get_address_balance(address)
    assert balance is not None
    assert balance.confirmed == 0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_asset_tracking_flow(db_session: AsyncSession, test_asset_data):
    """Test the flow of tracking assets through transactions."""
    # Create output for asset
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

    # Test asset retrieval
    result = await db_session.get(Asset, test_asset_data["id"])
    assert result is not None
    assert result.token_id == test_asset_data["token_id"]
    assert result.amount == test_asset_data["amount"]

@pytest.mark.integration
@pytest.mark.asyncio
async def test_chain_reorganization_flow(db_session: AsyncSession, test_block_data):
    """Test handling of chain reorganization."""
    # Create initial chain
    main_block = Block(**test_block_data)
    db_session.add(main_block)
    await db_session.commit()

    # Create fork block
    fork_data = dict(test_block_data)
    fork_data["id"] = "fork_block_hash"
    fork_block = Block(**fork_data)
    db_session.add(fork_block)
    await db_session.commit()

    # Test block retrieval
    block_repo = BlockRepository(db_session)
    result = await block_repo.get_by_height(test_block_data["height"])
    assert result is not None
    
    # Simulate chain reorganization by updating main_chain flag
    main_block.main_chain = False
    fork_block.main_chain = True
    await db_session.commit()

    # Verify fork block is now main chain
    result = await block_repo.get_by_height(test_block_data["height"])
    assert result.id == fork_block.id 