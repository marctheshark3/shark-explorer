"""Metrics and monitoring."""
import logging
import asyncio
import time
import os
import random
from typing import Optional, Dict, Any, Callable, AsyncGenerator
import aiohttp
from prometheus_client import Counter, Gauge, Info, Histogram, REGISTRY, CollectorRegistry, generate_latest
from fastapi import APIRouter, FastAPI, Request, Response
from starlette.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..api.node import Node
from ..db.repositories.blocks import BlockRepository
from ..db.repositories.transactions import TransactionRepository
from ..db.dependencies import get_db_session
from ..core.config import settings

# Initialize structured logger
logger = structlog.get_logger("metrics_updater")

# Create registry
registry = CollectorRegistry()

# Create router
router = APIRouter()

# Define metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total count of HTTP requests by method and path",
    ["method", "path", "status"],
    registry=registry
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds by method and path",
    ["method", "path"],
    registry=registry
)

active_requests = Gauge(
    "active_requests",
    "Number of active requests",
    registry=registry
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    registry=registry
)

indexer_height = Gauge(
    "indexer_height",
    "Current height of the indexer",
    registry=registry
)

node_height = Gauge(
    "node_height",
    "Current height of the Ergo node",
    registry=registry
)

sync_percentage = Gauge(
    "sync_percentage",
    "Sync percentage of the indexer",
    registry=registry
)

total_transactions = Gauge(
    "total_transactions",
    "Total number of indexed transactions",
    registry=registry
)

indexing_rate = Gauge(
    "indexing_rate",
    "Rate of blocks indexed per second",
    registry=registry
)

node_info = Info(
    "node_info",
    "Information about the connected Ergo node",
    registry=registry
)

REFRESH_INTERVAL = int(os.getenv("METRICS_REFRESH_INTERVAL_SECONDS", "5"))

async def monitoring_middleware(request: Request, call_next: Callable) -> Response:
    """Monitor request duration and count."""
    active_requests.inc()
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        http_requests_total.labels(
            method=request.method,
            path=request.url.path,
            status=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            path=request.url.path
        ).observe(duration)
        
        return response
    except Exception as e:
        http_requests_total.labels(
            method=request.method,
            path=request.url.path,
            status=500
        ).inc()
        raise e
    finally:
        active_requests.dec()

@router.get("/metrics")
async def metrics_endpoint(request: Request) -> Response:
    """Expose Prometheus metrics."""
    metrics = generate_latest(registry)
    return PlainTextResponse(metrics)

async def metrics_updater(node_url: str, network: str):
    """Update metrics from the node and database."""
    logger.info("Starting metrics updater")
    last_node_height = 0
    last_indexer_height = 0
    last_update_time = time.time()
    
    while True:
        try:
            # Get node height
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f"{node_url}/info") as response:
                        if response.status == 200:
                            data = await response.json()
                            current_node_height = data.get("fullHeight", 0)
                            
                            # Set node info
                            node_data = {
                                "network": network,
                                "version": data.get("appVersion", "unknown"),
                                "address": node_url
                            }
                            node_info.info(node_data)
                            
                            # Set node height
                            node_height.set(current_node_height)
                            logger.debug(f"Node height: {current_node_height}")
                        else:
                            logger.warning(f"Failed to get node info: {response.status}")
                except Exception as e:
                    logger.error(f"Error getting node info: {str(e)}")
            
            # Get transaction count from database
            try:
                # Use a direct PostgreSQL connection instead of SQLAlchemy
                import psycopg
                # Get database connection details
                dsn = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
                
                # Connect and query
                with psycopg.connect(dsn) as conn:
                    # Add a timestamp to avoid any query caching
                    timestamp = int(time.time())
                    random_num = random.randint(1, 1000)
                    
                    # Simple direct count
                    with conn.cursor() as cur:
                        cur.execute(f"SELECT COUNT(*) FROM transactions WHERE 1=1 AND random() < 1.0 AND {timestamp} > 0 AND {random_num} > 0")
                        tx_count = cur.fetchone()[0]
                        logger.info(f"Transaction count query result: {tx_count}")
                    
                    if tx_count > 0:
                        total_transactions.set(tx_count)
                        logger.info(f"Setting total_transactions metric: {tx_count}")
                    else:
                        # Fall back to another query method if count returns 0
                        with conn.cursor() as cur:
                            cur.execute("SELECT MAX(id) FROM transactions")
                            max_id = cur.fetchone()[0]
                            if max_id:
                                logger.info(f"Max transaction ID: {max_id}")
                                total_transactions.set(max_id)
                            else:
                                logger.warning("No transactions found in database.")
                    
                    # Get current indexer height from blocks table
                    with conn.cursor() as cur:
                        cur.execute("SELECT MAX(height) FROM blocks")
                        current_indexer_height = cur.fetchone()[0] or 0
                        logger.info(f"Current indexer height: {current_indexer_height}")
                    
                    if current_indexer_height > 0:
                        # Set indexer height
                        indexer_height.set(current_indexer_height)
                        
                        # Calculate sync percentage
                        if current_node_height > 0:
                            current_sync_percentage = (current_indexer_height / current_node_height) * 100
                            sync_percentage.set(current_sync_percentage)
                            logger.info(f"Sync percentage: {current_sync_percentage:.2f}%")
                        
                        # Calculate indexing rate
                        current_time = time.time()
                        time_diff = current_time - last_update_time
                        if time_diff > 0 and last_indexer_height > 0:
                            height_diff = current_indexer_height - last_indexer_height
                            current_indexing_rate = height_diff / time_diff
                            indexing_rate.set(current_indexing_rate)
                            logger.debug(f"Indexing rate: {current_indexing_rate:.2f} blocks/s")
                        
                        last_indexer_height = current_indexer_height
                        last_update_time = current_time
            
            except Exception as e:
                logger.error(f"Error updating metrics from database: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        except Exception as e:
            logger.error(f"Error in metrics updater: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Sleep for 5 seconds
        await asyncio.sleep(5)

def setup_monitoring(app: FastAPI) -> None:
    """
    Setup monitoring for application.
    """
    metrics_endpoint = APIRouter()
    
    @metrics_endpoint.get("/metrics", response_class=PlainTextResponse)
    async def get_metrics():
        """
        Endpoint that serves Prometheus metrics.
        """
        # Use our registry instead of MultiProcessCollector
        metrics = generate_latest(registry)
        
        return PlainTextResponse(metrics)
    
    app.include_router(metrics_endpoint)
    
    # We don't need to start metrics_updater here, it's handled in app.py now
    # The metrics_updater function is not meant to be called directly here