"""Main application module."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging

from .api.v1.api import api_router
from .core.config import settings
from .core.middleware import add_middleware
from .core.simple_monitoring import setup_monitoring, metrics_updater
from .db.dependencies import get_db

def create_application() -> FastAPI:
    """Create FastAPI application."""
    # Set up logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add rate limiting middleware
    add_middleware(app)
    
    # Set up monitoring
    setup_monitoring(app)
    
    # Include API router
    app.include_router(api_router, prefix="/api/v1")
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}
    
    # Set up metrics updater
    @app.on_event("startup")
    async def startup_event():
        # Schedule the metrics updater task
        logger.info("Starting metrics updater task...")
        # Launch the metrics updater with the node URL and network
        asyncio.create_task(metrics_updater(settings.NODE_URL, settings.NETWORK))
        logger.info("Metrics updater task scheduled")
    
    return app

app = create_application() 