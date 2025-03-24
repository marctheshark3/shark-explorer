import asyncio
import pytest
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from shark_api.core.config import settings
from shark_api.db.session import get_db
from shark_api.main import app

# Test database URL
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    settings.DATABASE_NAME, f"{settings.DATABASE_NAME}_test"
)

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
TestingSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db_setup():
    """Set up test database."""
    async with test_engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(test_db_setup) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()
        await session.close()

@pytest.fixture
async def client(db_session: AsyncSession) -> Generator:
    """Create a test client with the test database."""
    async def override_get_db():
        try:
            yield db_session
        finally:
            await db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_block_data():
    """Sample block data for testing."""
    return {
        "id": "test_block_hash",
        "height": 1000000,
        "timestamp": 1234567890,
        "parent_id": "parent_block_hash",
        "difficulty": 1234567,
        "block_size": 1024,
        "extension_hash": "extension_hash",
        "miner_pk": "miner_public_key",
        "w": "w_value",
        "n": "n_value",
        "d": "1.23",
        "votes": "000"
    }

@pytest.fixture
def test_transaction_data():
    """Sample transaction data for testing."""
    return {
        "id": "test_tx_hash",
        "block_id": "test_block_hash",
        "timestamp": 1234567890,
        "index": 0,
        "size": 256,
        "inputs": [],
        "outputs": []
    }

@pytest.fixture
def test_address_data():
    """Sample address data for testing."""
    return {
        "address": "test_address",
        "balance": 1000000,
        "transactions": 10,
        "first_seen": 1234567890,
        "last_seen": 1234567899
    }

@pytest.fixture
def test_asset_data():
    """Sample asset data for testing."""
    return {
        "id": "test_asset_id",
        "box_id": "test_box_id",
        "token_id": "test_token_id",
        "amount": 1000000,
        "name": "Test Asset",
        "decimals": 0
    } 