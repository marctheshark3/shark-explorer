from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging

from .core.config import settings
from .core.database import get_db
from .core.monitoring import setup_monitoring, metrics_updater, REFRESH_INTERVAL
from .api.node import Node
from .api.v1.api import api_router

# CORS middleware configuration
cors_config = {
    "allow_origins": settings.BACKEND_CORS_ORIGINS,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

def create_app() -> FastAPI:
    """
    Application factory
    """
    # Create and configure the app
    app = FastAPI(
        title=settings.PROJECT_NAME, 
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION
    )

    # Configure monitoring
    setup_monitoring(app)

    # Setup middleware
    app.add_middleware(CORSMiddleware, **cors_config)

    # Include routes
    app.include_router(api_router, prefix="/api/v1")
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}

    @app.middleware("http")
    async def db_session_middleware(request: Request, call_next):
        response = Response("Internal server error", status_code=500)
        async with get_db() as session:
            request.state.db = session
            response = await call_next(request)
        return response
        
    @app.on_event("startup")
    async def startup_event():
        # Set up root logger to capture all logs
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        # Add a handler if needed
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(handler)
        
        # Log startup
        root_logger.info("Starting metrics updater task...")
        
        # Schedule the metrics updater task
        try:
            task = asyncio.create_task(run_metrics_updater())
            root_logger.info("Metrics updater task scheduled successfully")
        except Exception as e:
            root_logger.error(f"Failed to schedule metrics updater task: {str(e)}")
        
    async def run_metrics_updater():
        """
        Background task that updates metrics at regular intervals
        """
        logger = logging.getLogger("metrics_scheduler")
        logger.setLevel(logging.INFO)
        logger.info(f"Starting metrics updater task with refresh interval of {REFRESH_INTERVAL} seconds")
        
        while True:
            try:
                logger.info("Running metrics update cycle...")
                # Get a new session for each update
                async with get_db() as session:
                    # Create a node instance
                    logger.info("Creating Node instance...")
                    node = Node()
                    logger.info("Node instance created")
                    
                    # Update metrics
                    logger.info("Calling metrics_updater...")
                    await metrics_updater(session, node)
                    logger.info("Metrics update completed successfully")
                    
            except Exception as e:
                logger.error(f"Error in metrics updater task: {str(e)}", exc_info=True)
                
            # Wait before the next update
            logger.info(f"Waiting {REFRESH_INTERVAL} seconds until next update...")
            await asyncio.sleep(REFRESH_INTERVAL)

    return app 