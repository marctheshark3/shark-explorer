import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from shark_api.db.models import Block, Transaction, Output, Asset

@pytest.mark.asyncio
async def test_get_latest_block(client: TestClient, db_session: AsyncSession, test_block_data):
    """Test GET /api/v1/blocks/latest endpoint."""
    # Create test block
    block = Block(**test_block_data)
    db_session.add(block)
    await db_session.commit()

    response = client.get("/api/v1/blocks/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["height"] == test_block_data["height"]
    assert data["id"] == test_block_data["id"]

@pytest.mark.asyncio
async def test_get_block_by_height(client: TestClient, db_session: AsyncSession, test_block_data):
    """Test GET /api/v1/blocks/{height} endpoint."""
    # Create test block
    block = Block(**test_block_data)
    db_session.add(block)
    await db_session.commit()

    response = client.get(f"/api/v1/blocks/{test_block_data['height']}")
    assert response.status_code == 200
    data = response.json()
    assert data["height"] == test_block_data["height"]
    assert data["id"] == test_block_data["id"]

@pytest.mark.asyncio
async def test_get_transaction(client: TestClient, db_session: AsyncSession, test_transaction_data):
    """Test GET /api/v1/transactions/{txId} endpoint."""
    # Create test transaction
    transaction = Transaction(**test_transaction_data)
    db_session.add(transaction)
    await db_session.commit()

    response = client.get(f"/api/v1/transactions/{test_transaction_data['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_transaction_data["id"]
    assert data["timestamp"] == test_transaction_data["timestamp"]

@pytest.mark.asyncio
async def test_get_address_balance(client: TestClient, db_session: AsyncSession):
    """Test GET /api/v1/addresses/{address}/balance endpoint."""
    # Create test output with balance
    output_data = {
        "box_id": "test_box",
        "tx_id": "test_tx",
        "index_in_tx": 0,
        "value": 1000000,
        "creation_height": 1000000,
        "address": "test_address",
        "ergo_tree": "test_ergo_tree"
    }
    output = Output(**output_data)
    db_session.add(output)
    await db_session.commit()

    response = client.get("/api/v1/addresses/test_address/balance")
    assert response.status_code == 200
    data = response.json()
    assert data["confirmed"] == output_data["value"]

@pytest.mark.asyncio
async def test_get_asset_info(client: TestClient, db_session: AsyncSession, test_asset_data):
    """Test GET /api/v1/assets/{assetId} endpoint."""
    # Create test output first
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

    # Create test asset
    asset = Asset(**test_asset_data)
    db_session.add(asset)
    await db_session.commit()

    response = client.get(f"/api/v1/assets/{test_asset_data['token_id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_asset_data["token_id"]
    assert data["name"] == test_asset_data["name"]

@pytest.mark.asyncio
async def test_search(client: TestClient, db_session: AsyncSession, test_block_data, test_transaction_data):
    """Test GET /api/v1/search endpoint."""
    # Create test block and transaction
    block = Block(**test_block_data)
    transaction = Transaction(**test_transaction_data)
    db_session.add_all([block, transaction])
    await db_session.commit()

    # Test search by block hash
    response = client.get(f"/api/v1/search?q={test_block_data['id']}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["blocks"]) == 1
    assert data["blocks"][0]["id"] == test_block_data["id"]

    # Test search by transaction hash
    response = client.get(f"/api/v1/search?q={test_transaction_data['id']}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["transactions"]) == 1
    assert data["transactions"][0]["id"] == test_transaction_data["id"]

@pytest.mark.asyncio
async def test_get_status(client: TestClient):
    """Test GET /api/v1/status endpoint."""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert "height" in data
    assert "synced" in data 