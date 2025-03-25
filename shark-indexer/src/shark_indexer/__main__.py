import asyncio
import logging
import structlog
import os
import argparse
import time
from dotenv import load_dotenv
from sqlalchemy.orm import registry
import psutil

from .core.node import NodeClient
from .core.indexer import IndexerService
from .db.database import init_db, check_db_health
from .db.models import mapper_registry
from .utils.redis_client import redis_client
from .utils.performance import performance_tracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

def parse_args():
    """
    Parse command line arguments for the Ergo Shark Indexer.
    
    Returns:
        argparse.Namespace: The parsed command line arguments
    
    Options:
        --reset-db: Reset the database before starting the indexer
        --batch-size: Number of blocks to process in parallel (default: 20)
        --workers: Number of parallel workers for processing blocks (default: 5)
        --fetcher-workers: Number of worker tasks for fetching blocks (default: 5)
        --processor-workers: Number of worker tasks for processing blocks (default: 10) 
        --fetch-batch-size: Number of blocks to fetch at once from the node (default: 50)
        --db-batch-size: Number of blocks to process in a single database transaction (default: 10)
        --no-parallel: Disable parallel processing and use sequential mode
        --no-bulk: Disable bulk inserts and use individual database operations
        --no-cache: Disable Redis caching for API responses
        --optimize-memory: Optimize for lower memory usage at the cost of some performance
        --optimize-speed: Optimize for maximum speed at the cost of higher memory usage
        --sequential-steps: Number of blocks to process sequentially when needed
    """
    parser = argparse.ArgumentParser(description="Ergo Shark Indexer")
    parser.add_argument("--reset-db", action="store_true", help="Reset the database")
    parser.add_argument("--batch-size", type=int, default=20, help="Number of blocks to process in parallel")
    parser.add_argument("--workers", type=int, default=5, help="Number of parallel workers")
    parser.add_argument("--fetcher-workers", type=int, default=5, help="Number of worker tasks for fetching blocks")
    parser.add_argument("--processor-workers", type=int, default=10, help="Number of worker tasks for processing blocks")
    parser.add_argument("--fetch-batch-size", type=int, default=50, help="Number of blocks to fetch at once")
    parser.add_argument("--db-batch-size", type=int, default=10, help="Number of blocks per database transaction")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel processing")
    parser.add_argument("--no-bulk", action="store_true", help="Disable bulk inserts")
    parser.add_argument("--no-cache", action="store_true", help="Disable Redis caching")
    parser.add_argument("--optimize-memory", action="store_true", help="Optimize for lower memory usage")
    parser.add_argument("--optimize-speed", action="store_true", help="Optimize for maximum speed")
    parser.add_argument("--sequential-steps", type=int, default=20, help="Number of blocks to process sequentially when needed")
    
    return parser.parse_args()

async def main():
    """Main application entry point."""
    start_time = time.time()
    try:
        # Load environment variables
        load_dotenv()
        
        # Parse command line arguments
        args = parse_args()

        # Get reset_db flag from environment or command line
        reset_db = args.reset_db or os.getenv('RESET_DB', 'false').lower() == 'true'
        
        # Set up optimization profiles
        if args.optimize_memory and args.optimize_speed:
            logger.warning("Both --optimize-memory and --optimize-speed specified; using balanced settings")
        
        # Memory optimization profile reduces batch sizes and worker counts
        if args.optimize_memory and not args.optimize_speed:
            logger.info("Using memory-optimized profile")
            if not args.batch_size:
                args.batch_size = 10
            if not args.workers:
                args.workers = 3
            if not args.fetcher_workers:
                args.fetcher_workers = 2
            if not args.processor_workers:
                args.processor_workers = 5
            if not args.fetch_batch_size:
                args.fetch_batch_size = 20
            if not args.db_batch_size:
                args.db_batch_size = 5
        
        # Speed optimization profile increases batch sizes and worker counts
        elif args.optimize_speed and not args.optimize_memory:
            logger.info("Using speed-optimized profile")
            if not args.batch_size:
                args.batch_size = 50
            if not args.workers:
                args.workers = 10
            if not args.fetcher_workers:
                args.fetcher_workers = 10
            if not args.processor_workers:
                args.processor_workers = 20
            if not args.fetch_batch_size:
                args.fetch_batch_size = 100
            if not args.db_batch_size:
                args.db_batch_size = 20
                
        # Configure indexer options from args
        indexer_config = {
            'batch_size': args.batch_size,
            'max_workers': args.workers,
            'fetcher_workers': args.fetcher_workers,
            'processor_workers': args.processor_workers,
            'fetch_batch_size': args.fetch_batch_size,
            'db_batch_size': args.db_batch_size,
            'parallel_mode': not args.no_parallel,
            'bulk_insert': not args.no_bulk,
            'use_redis_cache': not args.no_cache,
            'sequential_steps': args.sequential_steps
        }

        # Configure SQLAlchemy registry - this is the only place in the codebase this should be called
        logger.info("Configuring SQLAlchemy registry...")
        mapper_registry.configure()

        # Manually add the metadata property to TokenInfo to satisfy API requirements
        logger.info("Adding metadata property to TokenInfo...")
        from .db.models import TokenInfo
        
        # Instead of using register_attribute, use a simple property
        @property
        def get_metadata(self):
            return self.asset_metadata
            
        # Add the property to the TokenInfo class
        TokenInfo.metadata = get_metadata
        logger.info("Metadata property added successfully")

        # Initialize database
        logger.info("Initializing database...")
        if reset_db:
            logger.warning("Database reset requested. All existing data will be deleted.")
        await init_db(reset_db=reset_db)
        
        # Check database health
        db_health = await check_db_health()
        logger.info("Database health check", status=db_health['status'], pool=db_health['pool'])
        
        # Initialize Redis connection if caching is enabled
        redis_enabled = indexer_config['use_redis_cache']
        if redis_enabled:
            logger.info("Connecting to Redis...")
            await redis_client.connect()
            redis_connected = redis_client.is_connected
            logger.info("Redis connection", status="connected" if redis_connected else "failed")
        else:
            logger.info("Redis caching disabled")
            redis_connected = False

        # Create node client with Redis for caching if available
        logger.info("Creating node client...")
        node_client = NodeClient(redis_client if redis_enabled and redis_connected else None)
        await node_client.connect()
        
        try:
            # Check node connection
            info = await node_client.get_info()
            logger.info(
                "Connected to node",
                height=info['fullHeight'],
                version=info.get('version', 'unknown')
            )

            # Log configuration
            logger.info(
                "Indexer configuration",
                parallel=indexer_config['parallel_mode'],
                batch_size=indexer_config['batch_size'],
                workers=indexer_config['max_workers'],
                fetcher_workers=indexer_config['fetcher_workers'],
                processor_workers=indexer_config['processor_workers'],
                fetch_batch_size=indexer_config['fetch_batch_size'],
                db_batch_size=indexer_config['db_batch_size'],
                bulk_insert=indexer_config['bulk_insert'],
                cache=indexer_config['use_redis_cache'] and redis_connected,
                sequential_steps=indexer_config['sequential_steps']
            )

            # Create and start indexer
            logger.info("Starting indexer service...")
            indexer = IndexerService(node_client, indexer_config)
            await indexer.start()
            
        finally:
            # Cleanup
            await node_client.close()
            if redis_connected:
                await redis_client.close()
                
            # Print performance report
            logger.info("Performance summary")
            performance_tracker.report()

    except Exception as e:
        logger.error("Application error", error=str(e), exc_info=True)
        raise
    finally:
        total_runtime = time.time() - start_time
        logger.info(f"Total runtime: {total_runtime:.2f} seconds")

if __name__ == '__main__':
    asyncio.run(main())
else:
    # This is needed for the entry point to work correctly
    def run_main():
        return asyncio.run(main()) 