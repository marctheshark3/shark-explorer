"""Monitoring middleware and metrics."""
import time
from typing import Callable
from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from prometheus_client.multiprocess import MultiProcessCollector

# Create registry
registry = CollectorRegistry()
MultiProcessCollector(registry)

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

async def monitoring_middleware(request: Request, call_next: Callable) -> Response:
    """Monitor requests and collect metrics."""
    active_requests.inc()
    start_time = time.time()
    
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        raise e
    finally:
        duration = time.time() - start_time
        active_requests.dec()
        
        # Record metrics
        path = request.url.path
        method = request.method
        
        http_requests_total.labels(
            method=method,
            path=path,
            status=status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            path=path
        ).observe(duration)
    
    return response

async def metrics_endpoint() -> Response:
    """Expose Prometheus metrics."""
    return Response(
        generate_latest(registry),
        media_type="text/plain"
    )

def setup_monitoring(app: FastAPI) -> None:
    """Set up monitoring for the application."""
    app.middleware("http")(monitoring_middleware)
    app.add_route("/metrics", metrics_endpoint) 