"""
Metrics collectors for the indexer service.
This module provides Prometheus metrics for monitoring the indexer.
"""

import time
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, multiprocess

# Create a registry for multiprocess mode
registry = CollectorRegistry()

# Indexing progress metrics
INDEXED_BLOCKS = Gauge(
    'ergo_indexed_blocks',
    'Number of blocks indexed in the database',
    registry=registry
)

LATEST_BLOCK_HEIGHT = Gauge(
    'ergo_latest_block_height',
    'Height of the latest block in the blockchain',
    registry=registry
)

INDEXING_RATE = Gauge(
    'ergo_indexing_rate',
    'Blocks indexed per minute',
    registry=registry
)

# Transaction metrics
TOTAL_TRANSACTIONS = Gauge(
    'ergo_total_transactions',
    'Total number of transactions indexed',
    registry=registry
)

TRANSACTIONS_PER_BLOCK = Histogram(
    'ergo_transactions_per_block',
    'Histogram of transactions per block',
    buckets=[0, 1, 2, 5, 10, 20, 50, 100, 200],
    registry=registry
)

# Performance metrics
BLOCK_PROCESSING_TIME = Histogram(
    'ergo_block_processing_time_seconds',
    'Time taken to process a block',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0],
    registry=registry
)

# Batch processing metrics
BATCH_PROCESSING_TIME = Histogram(
    'ergo_batch_processing_time_seconds',
    'Time taken to process a batch of blocks',
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=registry
)

BATCH_SIZE = Gauge(
    'ergo_batch_size',
    'Current batch size for block processing',
    registry=registry
)

BLOCKS_PER_SECOND = Gauge(
    'ergo_blocks_per_second',
    'Number of blocks processed per second',
    registry=registry
)

NODE_REQUEST_TIME = Histogram(
    'ergo_node_request_time_seconds',
    'Time taken for requests to the Ergo node',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0],
    registry=registry
)

DB_OPERATION_TIME = Histogram(
    'ergo_db_operation_time_seconds',
    'Time taken for database operations',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    registry=registry
)

# Bulk operation metrics
BULK_INSERT_TIME = Histogram(
    'ergo_bulk_insert_time_seconds',
    'Time taken for bulk database inserts',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    registry=registry
)

ROWS_PER_BULK_INSERT = Histogram(
    'ergo_rows_per_bulk_insert',
    'Number of rows per bulk insert operation',
    buckets=[1, 10, 50, 100, 500, 1000, 5000],
    registry=registry
)

# Error metrics
NODE_CONNECTION_ERRORS = Counter(
    'ergo_node_connection_errors_total',
    'Total number of connection errors to the Ergo node',
    registry=registry
)

DB_CONNECTION_ERRORS = Counter(
    'ergo_db_connection_errors_total',
    'Total number of database connection errors',
    registry=registry
)

CHAIN_REORG_EVENTS = Counter(
    'ergo_chain_reorg_events_total',
    'Total number of blockchain reorganization events',
    registry=registry
)

REORGED_BLOCKS = Counter(
    'ergo_reorged_blocks_total',
    'Total number of blocks that were reorganized',
    registry=registry
)

# Helper timing context managers
class TimerContextManager:
    """Context manager for timing operations and reporting to Prometheus."""
    def __init__(self, metric):
        self.metric = metric
        self.start = 0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.metric.observe(time.time() - self.start)


def block_timer():
    """Context manager for timing block processing."""
    return TimerContextManager(BLOCK_PROCESSING_TIME)


def batch_timer():
    """Context manager for timing batch block processing."""
    return TimerContextManager(BATCH_PROCESSING_TIME)


def node_request_timer():
    """Context manager for timing Ergo node requests."""
    return TimerContextManager(NODE_REQUEST_TIME)


def db_operation_timer():
    """Context manager for timing database operations."""
    return TimerContextManager(DB_OPERATION_TIME)


def bulk_insert_timer():
    """Context manager for timing bulk insert operations."""
    return TimerContextManager(BULK_INSERT_TIME)


def initialize_metrics(current_height, total_tx_count):
    """Initialize metrics with current values from the database."""
    INDEXED_BLOCKS.set(current_height)
    TOTAL_TRANSACTIONS.set(total_tx_count)


def track_indexing_progress(current_height, node_height, tx_count, start_time, end_time):
    """Track indexing progress metrics."""
    INDEXED_BLOCKS.set(current_height)
    LATEST_BLOCK_HEIGHT.set(node_height)
    TOTAL_TRANSACTIONS.set(tx_count)
    
    # Calculate blocks per minute
    duration_minutes = (end_time - start_time) / 60
    if duration_minutes > 0:
        blocks_per_minute = 1 / duration_minutes
        INDEXING_RATE.set(blocks_per_minute)


def track_batch_progress(batch_size, blocks_count, start_time, end_time):
    """Track batch processing progress metrics."""
    BATCH_SIZE.set(batch_size)
    
    duration_seconds = end_time - start_time
    if duration_seconds > 0:
        blocks_per_second = blocks_count / duration_seconds
        BLOCKS_PER_SECOND.set(blocks_per_second)


def track_bulk_insert(rows_count):
    """Track bulk insert statistics."""
    ROWS_PER_BULK_INSERT.observe(rows_count)


def track_block_stats(tx_count):
    """Track statistics for a processed block."""
    TRANSACTIONS_PER_BLOCK.observe(tx_count)


def track_chain_reorg(reorged_blocks_count):
    """Track a chain reorganization event."""
    CHAIN_REORG_EVENTS.inc()
    REORGED_BLOCKS.inc(reorged_blocks_count) 