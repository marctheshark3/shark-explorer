# Shark Indexer

Shark Indexer is a high-performance blockchain indexer for the Ergo platform. It synchronizes with an Ergo node and indexes blockchain data in PostgreSQL for efficient querying and analysis.

## Performance Optimizations

The Shark Indexer includes several performance optimizations to significantly speed up the indexing process:

### Parallel Processing

The indexer can process multiple blocks in parallel, significantly improving throughput. This is controlled by the following parameters:

- `--batch-size`: Number of blocks to process in each batch (default: 20)
- `--workers`: Maximum number of concurrent workers (default: 5)
- `--no-parallel`: Disable parallel processing and use sequential mode

### Bulk Database Operations

Database operations are optimized with bulk inserts and batched operations, reducing the overhead of individual SQL statements and transactions.

- `--no-bulk`: Disable bulk operations and use individual inserts

### Caching with Redis

API responses from the Ergo node can be cached in Redis to reduce network overhead and improve performance for repeated requests.

- `--no-cache`: Disable Redis caching

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/shark-explorer.git
cd shark-explorer
```

2. Configure environment variables:
```bash
cp shark-indexer/.env.example shark-indexer/.env
```
   Edit the `.env` file with your configuration settings.

3. Install the package:
```bash
pip install -e ./shark-indexer
```

## Usage

Run the indexer with default settings:
```bash
shark-indexer
```

Run with custom settings:
```bash
shark-indexer --batch-size 30 --workers 8 --no-cache
```

Reset the database before starting:
```bash
shark-indexer --reset-db
```

## Benchmarking

A benchmark script is provided to measure and compare the performance of different modes:

```bash
# Compare sequential vs parallel modes
python shark-indexer/benchmark_indexer.py --start 100000 --count 100 --compare

# Run only sequential benchmark
python shark-indexer/benchmark_indexer.py --start 100000 --count 100 --sequential

# Run only parallel benchmark with custom parameters
python shark-indexer/benchmark_indexer.py --start 100000 --count 100 --parallel --batch-size 30 --workers 8
```

Benchmark results are written to a JSON file for analysis.

## Architecture

The indexer is built with a modular architecture:

- **Core**: Contains the main indexer logic and node client
- **DB**: Database models and connection management
- **Utils**: Utility modules for performance tracking, caching, and benchmarking

## Performance Metrics

The indexer tracks various performance metrics during operation:

- Block processing time (average, min, max)
- Database operations (inserts, updates, selects)
- API requests and cache hit rates
- CPU and memory usage

These metrics can be viewed in real-time through Prometheus and Grafana dashboards.

## Dependencies

- Python 3.9+
- PostgreSQL
- Redis (optional, for caching)
- Ergo Node API access 