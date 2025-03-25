#!/usr/bin/env python3
"""
Benchmark script for Ergo Shark Indexer.
This script compares the performance of sequential vs parallel indexing.
"""

import asyncio
import argparse
import json
import time
import os
from datetime import datetime
import structlog
from dotenv import load_dotenv

from src.shark_indexer.core.node import NodeClient
from src.shark_indexer.core.indexer import IndexerService
from src.shark_indexer.db.database import init_db
from src.shark_indexer.utils.redis_client import redis_client
from src.shark_indexer.utils.performance import performance_tracker

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

async def run_benchmark(start_height: int, block_count: int, config: dict):
    """
    Run a benchmark with specific configuration.
    
    Args:
        start_height: Starting block height
        block_count: Number of blocks to process
        config: Indexer configuration
    
    Returns:
        dict: Benchmark results
    """
    # Record start time
    start_time = time.time()
    
    # Connect to Redis if caching is enabled
    redis_connected = False
    if config.get('use_redis_cache', False):
        await redis_client.connect()
        redis_connected = redis_client.is_connected
    
    # Create node client
    node_client = NodeClient(redis_client if redis_connected else None)
    await node_client.connect()
    
    try:
        # Create indexer service
        indexer = IndexerService(node_client, config)
        
        # Get current node height
        node_height = await node_client.get_current_height()
        if start_height + block_count > node_height:
            logger.warning(
                "Requested range exceeds current node height",
                node_height=node_height,
                requested_end=start_height + block_count
            )
            block_count = max(1, node_height - start_height)
            logger.info("Adjusted block count", block_count=block_count)
        
        # Configure indexer for the test range
        indexer.current_height = start_height - 1
        indexer.target_height = start_height + block_count - 1
        
        # Run the indexer
        await indexer.start()
        
        # Record end time
        end_time = time.time()
        duration = end_time - start_time
        
        # Collect results
        results = {
            "config": config,
            "start_height": start_height,
            "block_count": block_count,
            "duration": duration,
            "blocks_per_second": block_count / duration if duration > 0 else 0,
            "stats": indexer.stats,
            "performance": {
                op: performance_tracker.get_timing_stats(op) 
                for op in performance_tracker.timings
            },
            "counters": {
                counter: performance_tracker.get_counter(counter)
                for counter in performance_tracker.counters
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return results
        
    finally:
        # Cleanup
        await node_client.close()
        if redis_connected:
            await redis_client.close()

async def compare_modes(start_height: int, block_count: int):
    """
    Compare sequential vs parallel indexing performance.
    
    Args:
        start_height: Starting block height
        block_count: Number of blocks to process
    """
    # Reset performance tracker between runs
    performance_tracker.reset()
    
    # Sequential configuration
    sequential_config = {
        'batch_size': 1,
        'max_workers': 1,
        'parallel_mode': False,
        'bulk_insert': True,
        'use_redis_cache': True,
    }
    
    # Parallel configuration
    parallel_config = {
        'batch_size': 20,
        'max_workers': 5,
        'parallel_mode': True,
        'bulk_insert': True,
        'use_redis_cache': True,
    }
    
    # Run sequential benchmark
    logger.info("Running sequential benchmark...")
    sequential_results = await run_benchmark(start_height, block_count, sequential_config)
    
    # Reset performance tracker between runs
    performance_tracker.reset()
    
    # Run parallel benchmark
    logger.info("Running parallel benchmark...")
    parallel_results = await run_benchmark(start_height, block_count, parallel_config)
    
    # Compare results
    speedup = sequential_results["duration"] / parallel_results["duration"] if parallel_results["duration"] > 0 else 0
    
    logger.info(
        "Benchmark comparison",
        sequential_time=f"{sequential_results['duration']:.2f}s",
        parallel_time=f"{parallel_results['duration']:.2f}s",
        speedup=f"{speedup:.2f}x"
    )
    
    # Write results to file
    timestamp = int(time.time())
    results = {
        "sequential": sequential_results,
        "parallel": parallel_results,
        "speedup": speedup,
        "metadata": {
            "start_height": start_height,
            "block_count": block_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    with open(f"benchmark_comparison_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results written to benchmark_comparison_{timestamp}.json")
    
    return results

async def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Ergo Shark Indexer Benchmark")
    parser.add_argument("--start", type=int, default=1, help="Starting block height")
    parser.add_argument("--count", type=int, default=100, help="Number of blocks to process")
    parser.add_argument("--compare", action="store_true", help="Compare sequential vs parallel modes")
    parser.add_argument("--sequential", action="store_true", help="Run only sequential benchmark")
    parser.add_argument("--parallel", action="store_true", help="Run only parallel benchmark")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for parallel mode")
    parser.add_argument("--workers", type=int, default=5, help="Number of workers for parallel mode")
    
    args = parser.parse_args()
    
    try:
        # Initialize database (don't reset)
        await init_db(reset_db=False)
        
        if args.compare:
            # Compare sequential vs parallel modes
            await compare_modes(args.start, args.count)
        elif args.sequential:
            # Run only sequential benchmark
            config = {
                'batch_size': 1,
                'max_workers': 1,
                'parallel_mode': False,
                'bulk_insert': True,
                'use_redis_cache': True,
            }
            results = await run_benchmark(args.start, args.count, config)
            logger.info(
                "Sequential benchmark results",
                duration=f"{results['duration']:.2f}s",
                blocks_per_second=f"{results['blocks_per_second']:.2f}"
            )
        elif args.parallel:
            # Run only parallel benchmark
            config = {
                'batch_size': args.batch_size,
                'max_workers': args.workers,
                'parallel_mode': True,
                'bulk_insert': True,
                'use_redis_cache': True,
            }
            results = await run_benchmark(args.start, args.count, config)
            logger.info(
                "Parallel benchmark results",
                duration=f"{results['duration']:.2f}s",
                blocks_per_second=f"{results['blocks_per_second']:.2f}",
                batch_size=args.batch_size,
                workers=args.workers
            )
        else:
            # Default to comparison
            await compare_modes(args.start, args.count)
        
    except Exception as e:
        logger.error("Benchmark error", error=str(e), exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main()) 