import asyncio
import logging
import structlog
import os
from dotenv import load_dotenv
from sqlalchemy.orm import registry

from .core.node import NodeClient
from .core.indexer import IndexerService
from .db.database import init_db
from .db.models import mapper_registry

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

        # Get reset_db flag from environment
        reset_db = os.getenv('RESET_DB', 'false').lower() == 'true'

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