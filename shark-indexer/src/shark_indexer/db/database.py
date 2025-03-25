import os
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Any, Dict, Optional
import structlog

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.orm import registry

from dotenv import load_dotenv

load_dotenv()

# Create logger
logger = structlog.get_logger()

# Get environment variables with defaults
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'changeme')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'shark_explorer')
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '20'))  # Default to 20 connections
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '30'))  # Default to 30 overflow connections
DB_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))  # Default to 30 seconds
DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '1800'))  # Default to 30 minutes

# Construct database URL with proper error handling
DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Log the connection attempt (without credentials)
logger.info(f"Connecting to database", host=DB_HOST, port=DB_PORT, name=DB_NAME, 
           pool_size=DB_POOL_SIZE, max_overflow=DB_MAX_OVERFLOW)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=DB_POOL_SIZE,  # Increased from default 5
    max_overflow=DB_MAX_OVERFLOW,  # Increased from default 10
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Add connection health check
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_session_ctx() -> AsyncSession:
    """Get a session without context manager.
    
    Use this when you need to manage the session lifecycle manually.
    Remember to commit/rollback and close the session.
    """
    session = async_session()
    return session

async def init_db(max_retries: int = 5, retry_delay: int = 5, reset_db: bool = False):
    """Initialize database tables with retry mechanism."""
    from .models import Base, mapper_registry
    
    # Note: mapper_registry.configure() is called in __main__.py
    
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                if reset_db:
                    logger.warning("Dropping all tables for database reset")
                    await conn.run_sync(Base.metadata.drop_all)
                
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Successfully initialized database")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                logger.error(f"Failed to initialize database", 
                            attempt=attempt+1, max_retries=max_retries, error=str(e))
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to initialize database after multiple attempts", 
                            max_retries=max_retries, error=str(e))
                raise

async def close_db():
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")

# Bulk insert helper method
async def bulk_insert_mappings(session: AsyncSession, model_class: Any, mappings: List[Dict[str, Any]]):
    """Insert multiple records at once using bulk_insert_mappings."""
    if not mappings:
        return
    
    try:
        await session.bulk_insert_mappings(model_class, mappings)
    except Exception as e:
        logger.error("Bulk insert failed", model=model_class.__name__, 
                    record_count=len(mappings), error=str(e))
        raise 