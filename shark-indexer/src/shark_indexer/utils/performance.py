import time
import asyncio
from typing import List, Dict, Any, Optional, Callable, Awaitable
import structlog
from functools import wraps
import functools
import statistics

logger = structlog.get_logger()

class PerformanceTracker:
    """Track and report performance metrics for indexer operations."""
    
    def __init__(self):
        self.timings = {}
        self.counters = {}
        
    def reset(self):
        """Reset all performance metrics."""
        self.timings = {}
        self.counters = {}
    
    def record_timing(self, operation: str, duration: float):
        """Record timing for an operation."""
        if operation not in self.timings:
            self.timings[operation] = []
        self.timings[operation].append(duration)
    
    def increment_counter(self, counter: str, value: int = 1):
        """Increment a counter."""
        if counter not in self.counters:
            self.counters[counter] = 0
        self.counters[counter] += value
    
    def get_average_timing(self, operation: str) -> Optional[float]:
        """Get average timing for an operation."""
        if operation in self.timings and self.timings[operation]:
            return sum(self.timings[operation]) / len(self.timings[operation])
        return None
    
    def get_counter(self, counter: str) -> int:
        """Get counter value."""
        return self.counters.get(counter, 0)
    
    def get_timing_stats(self, operation: str) -> Dict[str, float]:
        """Get comprehensive stats for an operation timing."""
        if operation not in self.timings or not self.timings[operation]:
            return {}
        
        times = self.timings[operation]
        return {
            'avg': sum(times) / len(times),
            'min': min(times),
            'max': max(times),
            'total': sum(times),
            'count': len(times)
        }
    
    def report(self):
        """Report all performance metrics."""
        logger.info("Performance Report")
        logger.info("===================")
        
        if self.timings:
            logger.info("Timing Statistics:")
            for op, times in self.timings.items():
                stats = self.get_timing_stats(op)
                logger.info(
                    f"  {op}",
                    avg=f"{stats['avg']:.6f}s",
                    min=f"{stats['min']:.6f}s",
                    max=f"{stats['max']:.6f}s",
                    total=f"{stats['total']:.6f}s",
                    count=stats['count']
                )
        
        if self.counters:
            logger.info("Counters:")
            for counter, value in self.counters.items():
                logger.info(f"  {counter}: {value}")
        
        # Calculate derived metrics
        if 'blocks_processed' in self.counters and 'total_processing_time' in self.counters:
            blocks = self.counters['blocks_processed']
            total_time = self.counters['total_processing_time']
            if total_time > 0:
                blocks_per_second = blocks / total_time
                logger.info(f"Blocks per second: {blocks_per_second:.2f}")

# Global performance tracker instance
performance_tracker = PerformanceTracker()

def timed(operation: str):
    """Decorator to time a function and record it in the performance tracker."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                performance_tracker.record_timing(operation, duration)
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                performance_tracker.record_timing(operation, duration)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator

class Timer:
    """Simple timer utility to measure execution time."""
    
    def __init__(self):
        self.start_time = time.time()
        
    def elapsed(self) -> float:
        """Return elapsed time in seconds since timer was created."""
        return time.time() - self.start_time
        
    def reset(self) -> None:
        """Reset the timer."""
        self.start_time = time.time()

async def benchmark_indexer(func: Callable[..., Awaitable], *args, **kwargs) -> Dict[str, Any]:
    """Benchmark a function with the given arguments.
    
    Args:
        func: The async function to benchmark
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Dict containing benchmark results
    """
    performance_tracker.reset()
    
    # Record the start time
    start_time = time.time()
    
    # Execute the function
    result = await func(*args, **kwargs)
    
    # Record the end time
    end_time = time.time()
    total_time = end_time - start_time
    
    # Store total processing time
    performance_tracker.increment_counter('total_processing_time', total_time)
    
    # Generate the report
    performance_tracker.report()
    
    # Return the benchmark results
    return {
        'total_time': total_time,
        'result': result,
        'timings': {op: performance_tracker.get_timing_stats(op) for op in performance_tracker.timings},
        'counters': {counter: performance_tracker.get_counter(counter) for counter in performance_tracker.counters}
    } 