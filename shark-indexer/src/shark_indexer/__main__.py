import asyncio
import logging
import structlog
from dotenv import load_dotenv

from .core.node import NodeClient
from .core.indexer import IndexerService
from .db.database import init_db

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

async def main():
    """Main application entry point."""
    try:
        # Load environment variables
        load_dotenv()

        # Initialize database
        logger.info("Initializing database...")
        await init_db()

        # Create node client
        logger.info("Creating node client...")
        async with NodeClient() as node:
            # Check node connection
            info = await node.get_info()
            logger.info(
                "Connected to node",
                height=info['fullHeight'],
                version=info.get('version', 'unknown')
            )

            # Create and start indexer
            logger.info("Starting indexer service...")
            indexer = IndexerService(node)
            await indexer.start()

    except Exception as e:
        logger.error("Application error", error=str(e))
        raise

if __name__ == '__main__':
    asyncio.run(main()) 