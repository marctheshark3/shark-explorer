"""Database dependencies."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

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

async def get_db_without_middleware() -> AsyncGenerator:
    """
    Get a database session for background tasks without middleware.
    
    Yields:
        AsyncSession: An async SQLAlchemy session object.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def get_db_session() -> AsyncSession:
    """
    Get a database session directly, not as an async generator.
    
    Returns:
        AsyncSession: An async SQLAlchemy session object.
    """
    # Make sure we're creating an AsyncSession, not a regular Session
    from sqlalchemy.ext.asyncio import AsyncSession
    session = AsyncSessionLocal()
    
    # Verify that we're returning an AsyncSession
    if not isinstance(session, AsyncSession):
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Session is not an AsyncSession! Type: {type(session)}")
        # Try to create an AsyncSession directly
        from sqlalchemy.ext.asyncio import create_async_session
        from shark_api.db.database import engine
        session = create_async_session(engine, expire_on_commit=False)
    
    return session 