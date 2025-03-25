"""
Metrics collectors for the API service.
This module provides Prometheus metrics for monitoring API performance.
"""

import time
from prometheus_client import Counter, Gauge, Histogram, Summary

# Request metrics
REQUEST_COUNT = Counter(
    'api_requests_total',
    'Total count of API requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'api_request_latency_seconds',
    'Histogram of API request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Database query metrics
DB_QUERY_COUNT = Counter(
    'api_db_queries_total',
    'Total count of database queries',
    ['query_type']
)

DB_QUERY_LATENCY = Histogram(
    'api_db_query_latency_seconds',
    'Histogram of database query latency',
    ['query_type'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.5]
)

# Error metrics
ERROR_COUNT = Counter(
    'api_errors_total',
    'Total count of API errors',
    ['method', 'endpoint', 'error_type']
)

# Cache metrics
CACHE_HIT_COUNT = Counter(
    'api_cache_hits_total',
    'Total count of cache hits',
    ['cache_type']
)

CACHE_MISS_COUNT = Counter(
    'api_cache_misses_total',
    'Total count of cache misses',
    ['cache_type']
)

# Connection pool metrics
DB_CONNECTIONS_IN_USE = Gauge(
    'api_db_connections_in_use',
    'Number of database connections currently in use'
)

DB_CONNECTIONS_WAITING = Gauge(
    'api_db_connections_waiting',
    'Number of database connections waiting'
)

# Rate limit metrics
RATE_LIMIT_HIT_COUNT = Counter(
    'api_rate_limit_hits_total',
    'Total count of rate limit hits',
    ['client_ip']
)

# Helper timing context managers
class RequestLatencyTimer:
    """Context manager for timing API requests and reporting to Prometheus."""
    def __init__(self, method, endpoint):
        self.method = method
        self.endpoint = endpoint
        self.start = 0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        REQUEST_LATENCY.labels(
            method=self.method,
            endpoint=self.endpoint
        ).observe(time.time() - self.start)


class DatabaseQueryTimer:
    """Context manager for timing database queries and reporting to Prometheus."""
    def __init__(self, query_type):
        self.query_type = query_type
        self.start = 0

    def __enter__(self):
        self.start = time.time()
        DB_QUERY_COUNT.labels(query_type=self.query_type).inc()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        DB_QUERY_LATENCY.labels(
            query_type=self.query_type
        ).observe(time.time() - self.start)


def track_request(method, endpoint, status_code):
    """Track an API request."""
    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code
    ).inc()


def track_error(method, endpoint, error_type):
    """Track an API error."""
    ERROR_COUNT.labels(
        method=method,
        endpoint=endpoint,
        error_type=error_type
    ).inc()


def track_cache_hit(cache_type):
    """Track a cache hit."""
    CACHE_HIT_COUNT.labels(cache_type=cache_type).inc()


def track_cache_miss(cache_type):
    """Track a cache miss."""
    CACHE_MISS_COUNT.labels(cache_type=cache_type).inc()


def track_db_connection_stats(in_use, waiting):
    """Track database connection stats."""
    DB_CONNECTIONS_IN_USE.set(in_use)
    DB_CONNECTIONS_WAITING.set(waiting)


def track_rate_limit_hit(client_ip):
    """Track a rate limit hit."""
    RATE_LIMIT_HIT_COUNT.labels(client_ip=client_ip).inc()


def request_timer(method, endpoint):
    """Context manager for timing API requests."""
    return RequestLatencyTimer(method, endpoint)


def db_query_timer(query_type):
    """Context manager for timing database queries."""
    return DatabaseQueryTimer(query_type) 