"""Simple metrics and monitoring."""
import logging
import asyncio
import time
import random
from typing import Optional, Dict, Any, List, Tuple
import aiohttp
from fastapi import APIRouter, FastAPI, Request, Response
from starlette.responses import PlainTextResponse
import structlog
import threading

from ..core.config import settings

# Initialize structured logger
logger = structlog.get_logger("metrics_updater")

# Custom simple metrics implementation
class SimpleGauge:
    """Simple gauge metric implementation."""
    
    def __init__(self, name: str, description: str):
        """Initialize gauge."""
        self.name = name
        self.description = description
        self._value = 0.0
        self._lock = threading.Lock()
    
    def set(self, value: float) -> None:
        """Set gauge value."""
        with self._lock:
            self._value = float(value)
    
    def get(self) -> float:
        """Get gauge value."""
        with self._lock:
            return self._value
    
    def inc(self, amount: float = 1.0) -> None:
        """Increment gauge value."""
        with self._lock:
            self._value += amount
    
    def dec(self, amount: float = 1.0) -> None:
        """Decrement gauge value."""
        with self._lock:
            self._value -= amount
    
    def to_prometheus_format(self) -> str:
        """Convert to Prometheus format."""
        return f"# HELP {self.name} {self.description}\n# TYPE {self.name} gauge\n{self.name} {self.get()}\n"

class SimpleCounter:
    """Simple counter metric implementation."""
    
    def __init__(self, name: str, description: str):
        """Initialize counter."""
        self.name = name
        self.description = description
        self._value = 0.0
        self._lock = threading.Lock()
    
    def inc(self, amount: float = 1.0) -> None:
        """Increment counter value."""
        with self._lock:
            self._value += amount
    
    def get(self) -> float:
        """Get counter value."""
        with self._lock:
            return self._value
    
    def to_prometheus_format(self) -> str:
        """Convert to Prometheus format."""
        return f"# HELP {self.name} {self.description}\n# TYPE {self.name} counter\n{self.name} {self.get()}\n"

class SimpleRegistry:
    """Simple registry for metrics."""
    
    def __init__(self):
        """Initialize registry."""
        self._metrics: List[object] = []
    
    def register(self, metric: object) -> None:
        """Register metric."""
        self._metrics.append(metric)
    
    def generate_latest(self) -> str:
        """Generate latest metrics."""
        result = ""
        for metric in self._metrics:
            result += metric.to_prometheus_format()
        return result

# Create registry
registry = SimpleRegistry()

# Define metrics
node_height = SimpleGauge('node_height', 'Current height of the Ergo node')
indexer_height = SimpleGauge('indexer_height', 'Current height indexed')
sync_percentage = SimpleGauge('sync_percentage', 'Percentage of blockchain indexed')
indexing_rate = SimpleGauge('indexing_rate', 'Rate of blocks indexed per second')
total_transactions = SimpleGauge('total_transactions', 'Total number of transactions indexed')
active_requests = SimpleGauge('active_requests', 'Number of active requests')
request_latency = SimpleCounter('request_latency_seconds_total', 'Request latency in seconds total')

# Register all metrics
registry.register(node_height)
registry.register(indexer_height)
registry.register(sync_percentage)
registry.register(indexing_rate)
registry.register(total_transactions)
registry.register(active_requests)
registry.register(request_latency)

# API request middleware
async def metrics_middleware(request: Request, call_next):
    """Middleware to record request metrics."""
    active_requests.inc()
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    active_requests.dec()
    request_latency.inc(duration)
    
    return response

# Metrics endpoint
def setup_monitoring(app: FastAPI) -> None:
    """Setup monitoring for application."""
    metrics_router = APIRouter()
    
    @metrics_router.get("/metrics", response_class=PlainTextResponse)
    async def metrics():
        """Prometheus metrics endpoint."""
        return PlainTextResponse(registry.generate_latest())
    
    # Add router to app
    app.include_router(metrics_router)
    
    # Add middleware
    app.middleware("http")(metrics_middleware)

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
                            logger.info(f"Node height: {current_node_height}")
                            
                            # Set node height
                            if current_node_height > 0:
                                node_height.set(current_node_height)
                        else:
                            logger.warning(f"Failed to get node info: {response.status}")
                except Exception as e:
                    logger.error(f"Error getting node info: {str(e)}")
            
            # Get transaction count from database
            try:
                # Use a direct PostgreSQL connection
                import psycopg
                
                # Get database connection details from settings
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
                            logger.info(f"Indexing rate: {current_indexing_rate:.2f} blocks/s")
                        
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