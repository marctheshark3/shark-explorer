"""Database dependencies."""
from typing import AsyncGenerator

from .database import AsyncSessionLocal

async def get_db() -> AsyncGenerator:
    """
    Get a database session.
    
    Yields:
        AsyncSession: An async SQLAlchemy session object.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close() 