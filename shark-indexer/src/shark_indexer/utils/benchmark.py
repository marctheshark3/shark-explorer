import asyncio
import os
import json
import sys
import argparse
from datetime import datetime
import structlog
from ..core.node import NodeClient
from ..core.indexer import IndexerService
from ..db.database import init_db
from .performance import benchmark_indexer, performance_tracker

logger = structlog.get_logger()

async def run_benchmark(start_height: int, block_count: int, mode: str = "sequential"):
    """
    Run a benchmark of the indexer on a specific range of blocks.
    
    Args:
        start_height: Starting block height
        block_count: Number of blocks to process
        mode: Benchmark mode (sequential, parallel, etc.)
    """
    # Initialize database
    await init_db()
    
    # Initialize node client
    node_client = NodeClient()
    await node_client.connect()
    
    try:
        # Create indexer service
        indexer = IndexerService(node_client)
        
        # Configure the indexer based on the mode
        if mode == "parallel":
            # Future parallel mode configuration will go here
            pass
            
        logger.info(
            f"Starting benchmark",
            start_height=start_height,
            block_count=block_count,
            mode=mode,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Define custom benchmark function to process a range of blocks
        async def process_range():
            for height in range(start_height, start_height + block_count):
                try:
                    # Use internal method to process a single height
                    await indexer._process_height(height)
                    performance_tracker.increment_counter("blocks_processed")
                except Exception as e:
                    logger.error(f"Error processing height {height}: {str(e)}", exc_info=True)
                    performance_tracker.increment_counter("errors")
        
        # Run the benchmark
        results = await benchmark_indexer(process_range)
        
        # Add benchmark metadata
        results["metadata"] = {
            "start_height": start_height,
            "block_count": block_count,
            "mode": mode,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Write results to file
        output_file = f"benchmark_{mode}_{start_height}_{block_count}_{int(datetime.utcnow().timestamp())}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Benchmark results written to {output_file}")
        
        # Return the results
        return results
        
    finally:
        # Close connections
        await node_client.close()

async def compare_modes(start_height: int, block_count: int, modes: list = ["sequential"]):
    """Compare different indexing modes on the same range of blocks."""
    results = {}
    
    for mode in modes:
        logger.info(f"Running benchmark with mode: {mode}")
        result = await run_benchmark(start_height, block_count, mode)
        results[mode] = result
    
    # Compare results
    if len(results) > 1:
        logger.info("Performance Comparison")
        logger.info("======================")
        
        for mode, result in results.items():
            total_time = result["total_time"]
            blocks_processed = result["counters"].get("blocks_processed", 0)
            errors = result["counters"].get("errors", 0)
            
            blocks_per_second = blocks_processed / total_time if total_time > 0 else 0
            
            logger.info(
                f"Mode: {mode}",
                total_time=f"{total_time:.2f}s",
                blocks_processed=blocks_processed,
                errors=errors,
                blocks_per_second=f"{blocks_per_second:.2f}"
            )
    
    # Write comparison to file
    output_file = f"benchmark_comparison_{start_height}_{block_count}_{int(datetime.utcnow().timestamp())}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Comparison results written to {output_file}")
    
    return results

async def main():
    """Main function to run the benchmark from command line."""
    parser = argparse.ArgumentParser(description="Ergo Shark Indexer Benchmark Tool")
    parser.add_argument("--start", type=int, default=1, help="Starting block height")
    parser.add_argument("--count", type=int, default=10, help="Number of blocks to process")
    parser.add_argument("--mode", type=str, default="sequential", choices=["sequential", "parallel"],
                        help="Benchmark mode (sequential, parallel)")
    parser.add_argument("--compare", action="store_true", help="Compare sequential and parallel modes")
    
    args = parser.parse_args()
    
    if args.compare:
        await compare_modes(args.start, args.count, ["sequential", "parallel"])
    else:
        await run_benchmark(args.start, args.count, args.mode)

if __name__ == "__main__":
    # Configure logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    
    # Run the benchmark
    asyncio.run(main()) 