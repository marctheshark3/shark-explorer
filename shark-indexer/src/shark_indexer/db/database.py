import os
import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Any, Dict, Optional, TypeVar, Type, Union
import structlog

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.orm import registry
from sqlalchemy import text

from dotenv import load_dotenv
from ..utils.performance import performance_tracker, timed

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
DB_ECHO = os.getenv('DB_ECHO', 'False').lower() == 'true'  # SQL query logging

# Construct database URL with proper error handling
DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Log the connection attempt (without credentials)
logger.info(f"Connecting to database", host=DB_HOST, port=DB_PORT, name=DB_NAME, 
           pool_size=DB_POOL_SIZE, max_overflow=DB_MAX_OVERFLOW)

# Configure engine with optimized settings
engine = create_async_engine(
    DATABASE_URL,
    echo=DB_ECHO,
    pool_size=DB_POOL_SIZE,  # Increased from default 5
    max_overflow=DB_MAX_OVERFLOW,  # Increased from default 10
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Add connection health check
    execution_options={"isolation_level": "READ COMMITTED"},  # Optimize for read performance
)

# Configure session factory with optimized settings
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True
)

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    start_time = time.time()
    session = async_session()
    try:
        yield session
        await session.commit()
        performance_tracker.record_timing("db_session", time.time() - start_time)
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

@timed("db_session_creation")
async def get_session_ctx() -> AsyncSession:
    """Get a session without context manager.
    
    Use this when you need to manage the session lifecycle manually.
    Remember to commit/rollback and close the session.
    """
    session = async_session()
    return session

@timed("db_init")
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

ModelType = TypeVar('ModelType')

@timed("db_bulk_insert")
async def bulk_insert_mappings(session: AsyncSession, model_class: Type[ModelType], mappings: List[Dict[str, Any]]):
    """Insert multiple records at once using bulk_insert_mappings."""
    if not mappings:
        return
    
    start_time = time.time()
    try:
        batch_size = 500  # Optimal batch size to avoid memory issues
        record_count = len(mappings)
        performance_tracker.increment_counter(f"bulk_insert_{model_class.__name__}", record_count)
        
        # Check if the session supports bulk_insert_mappings
        if hasattr(session, 'bulk_insert_mappings'):
            # Insert in batches to avoid memory issues with very large datasets
            for i in range(0, record_count, batch_size):
                batch = mappings[i:i+batch_size]
                try:
                    await session.bulk_insert_mappings(model_class, batch)
                except Exception as e:
                    # If we get a foreign key constraint error, fall back to individual inserts
                    if "ForeignKeyViolation" in str(e) or "foreign key constraint" in str(e):
                        logger.warning(f"Foreign key constraint violation in bulk insert, falling back to individual inserts",
                                      model=model_class.__name__, batch_size=len(batch), error=str(e))
                        # Fall back to individual inserts for this batch
                        for mapping in batch:
                            try:
                                instance = model_class(**mapping)
                                session.add(instance)
                                # Flush after each record to ensure dependencies are created
                                await session.flush()
                            except Exception as inner_e:
                                logger.error(f"Error in individual insert fallback",
                                           model=model_class.__name__, error=str(inner_e))
                                raise
                    else:
                        # Re-raise other exceptions
                        raise
        else:
            # Fallback to individual inserts if bulk_insert_mappings is not available
            logger.warning(f"Bulk insert not available, falling back to individual inserts", 
                          model=model_class.__name__, count=record_count)
            for mapping in mappings:
                # Create instance of the model with the mapping data
                instance = model_class(**mapping)
                session.add(instance)
            # Flush to ensure all objects are created in the database
            await session.flush()
        
        logger.debug(f"Bulk inserted records", 
                   model=model_class.__name__, 
                   count=record_count, 
                   duration=time.time() - start_time)
    except Exception as e:
        logger.error("Bulk insert failed", model=model_class.__name__, 
                    record_count=len(mappings), error=str(e))
        raise

@timed("db_execute_batch")
async def execute_batch(session: AsyncSession, query: str, params_list: List[Dict[str, Any]]):
    """Execute the same query with different parameters in batch."""
    if not params_list:
        return
    
    try:
        # Execute in a single transaction
        for params in params_list:
            await session.execute(text(query), params)
        
        logger.debug("Executed batch query", 
                   query_type=query.split()[0],  # First word of query (e.g., "INSERT")
                   batches=len(params_list))
    except Exception as e:
        logger.error("Batch query execution failed", 
                    query_type=query.split()[0],
                    batches=len(params_list), 
                    error=str(e))
        raise

@timed("db_health_check")
async def check_db_health() -> Dict[str, Any]:
    """Check database health and pool statistics."""
    try:
        # Get pool statistics
        pool_stats = {
            "size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "checkedin": engine.pool.checkedin(),
        }
        
        # Test database connectivity
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "pool": pool_stats,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

# Context manager for batch operations
@asynccontextmanager
async def batch_operation_context(session: Optional[AsyncSession] = None, isolation_level: str = "READ COMMITTED"):
    """Context manager for batch operations.
    
    Args:
        session: Optional existing session to use. If None, a new session is created.
        isolation_level: Transaction isolation level.
    """
    start_time = time.time()
    close_session = session is None
    if close_session:
        session = async_session()
    try:
        await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level.upper()}"))
        yield session
        await session.commit()
        duration = time.time() - start_time
        performance_tracker.record_timing("db_batch_operation", duration)
        logger.debug("Batch operation completed", duration=f"{duration:.2f}s")
    except Exception as e:
        await session.rollback()
        logger.error("Batch operation failed, transaction rolled back", error=str(e))
        raise
    finally:
        if close_session:
            await session.close()

@asynccontextmanager
async def multi_block_transaction(block_count: int = 1):
    """Optimized context manager for processing multiple blocks in a single transaction.
    
    This context manager is designed for handling multiple blocks in a single
    transaction with optimized settings based on the number of blocks.
    
    Args:
        block_count: Number of blocks to be processed in this transaction
    """
    start_time = time.time()
    session = async_session()
    
    try:
        # For larger batch sizes, adjust the isolation level and prefetch settings
        if block_count > 10:
            # For many blocks, use READ COMMITTED for better concurrency
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            # Increase work_mem for complex queries
            await session.execute(text("SET LOCAL work_mem = '32MB'"))
        elif block_count > 1:
            # For a few blocks, still use READ COMMITTED
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        else:
            # For single block processing, use default isolation
            pass
            
        # Note isolation level in logs
        logger.debug("Starting multi-block transaction", block_count=block_count)
            
        yield session
        
        await session.commit()
        duration = time.time() - start_time
        performance_tracker.record_timing("multi_block_transaction", duration)
        blocks_per_second = block_count / max(0.1, duration)
        logger.info(
            "Multi-block transaction completed", 
            block_count=block_count, 
            duration=f"{duration:.2f}s",
            blocks_per_second=f"{blocks_per_second:.2f}"
        )
    except Exception as e:
        await session.rollback()
        logger.error(
            "Multi-block transaction failed", 
            block_count=block_count, 
            error=str(e)
        )
        raise
    finally:
        await session.close() 