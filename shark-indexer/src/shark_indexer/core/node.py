import os
import asyncio
import time
import json
from typing import Any, Dict, Optional, List, Union, Tuple
import aiohttp
from aiohttp import ClientTimeout, TCPConnector, ClientResponse
import structlog
from dotenv import load_dotenv
import requests
from ..utils.performance import timed, performance_tracker

load_dotenv()
logger = structlog.get_logger()

class NodeClient:
    def __init__(self, redis_client=None):
        self.base_url = os.getenv('NODE_URL', 'http://127.0.0.1:9053')
        self.api_key = os.getenv('NODE_API_KEY')
        # Increased timeout for reliable operation
        self.timeout = ClientTimeout(total=int(os.getenv('NODE_TIMEOUT', '60')))
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if self.api_key:
            self.headers['api_key'] = self.api_key
            
        # Connection pooling configuration
        self.max_connections = int(os.getenv('NODE_MAX_CONNECTIONS', '20'))
        self.use_connection_pool = True
        
        # Cache configuration
        self.redis_client = redis_client
        self.use_cache = redis_client is not None
        self.cache_ttl = int(os.getenv('NODE_CACHE_TTL', '600'))  # 10 minutes default
        
        # Performance tracking
        self.requests_count = 0
        self.cache_hits = 0
        self.errors_count = 0

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @timed("node_connect")
    async def connect(self):
        """Create aiohttp session with connection pooling."""
        if not self.session or self.session.closed:
            connector = TCPConnector(
                limit=self.max_connections,
                ttl_dns_cache=300,
                use_dns_cache=True,
                ssl=False  # Most Ergo nodes don't use SSL
            )
            
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self.headers,
                connector=connector
            )
            logger.info(
                "Node client connected", 
                url=self.base_url, 
                max_connections=self.max_connections
            )

    async def close(self):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Node client session closed")

    @timed("node_request")
    async def _request(
        self,
        method: str,
        endpoint: str,
        cache_key: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request to node with retries, caching and instrumentation."""
        if not self.session or self.session.closed:
            await self.connect()
            
        self.requests_count += 1
        performance_tracker.increment_counter("node_requests")
            
        # Check cache if enabled and it's a GET request
        if self.use_cache and method.upper() == "GET" and cache_key:
            cache_data = await self._get_from_cache(cache_key)
            if cache_data:
                self.cache_hits += 1
                performance_tracker.increment_counter("node_cache_hits")
                return cache_data

        retries = int(os.getenv('NODE_RETRIES', '3'))
        backoff = 1
        last_error = None

        while retries > 0:
            try:
                start_time = time.time()
                logger.debug(
                    "Making request to node",
                    method=method,
                    endpoint=endpoint,
                    url=f"{self.base_url}{endpoint}"
                )
                
                async with self.session.request(
                    method,
                    f"{self.base_url}{endpoint}",
                    **kwargs
                ) as response:
                    response.raise_for_status()
                    data = await response.text()  # Get raw text first
                    request_time = time.time() - start_time
                    performance_tracker.record_timing(f"node_{method.lower()}_{endpoint.split('/')[1]}", request_time)
                    
                    # Try to parse as JSON
                    try:
                        if data:
                            result = json.loads(data)
                            
                            # Store in cache if it's a GET request
                            if self.use_cache and method.upper() == "GET" and cache_key:
                                await self._store_in_cache(cache_key, result)
                                
                            return result
                        return {}
                    except json.JSONDecodeError as e:
                        logger.error(
                            "Failed to parse JSON response",
                            endpoint=endpoint,
                            error=str(e),
                            data=data[:500],  # Log first 500 chars
                            exc_info=True
                        )
                        raise ValueError(f"Invalid JSON response: {str(e)}")

            except (aiohttp.ClientError, ValueError) as e:
                self.errors_count += 1
                performance_tracker.increment_counter("node_errors")
                last_error = e
                logger.error(
                    "Node request failed",
                    endpoint=endpoint,
                    error=str(e),
                    retries_left=retries,
                    exc_info=True
                )
                retries -= 1
                if retries > 0:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    raise last_error

    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from Redis cache."""
        if not self.redis_client:
            return None
            
        try:
            cached_data = await self.redis_client.get(f"node:{key}")
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Error getting from cache: {str(e)}")
            
        return None

    async def _store_in_cache(self, key: str, data: Dict[str, Any]) -> bool:
        """Store data in Redis cache."""
        if not self.redis_client:
            return False
            
        try:
            await self.redis_client.set(
                f"node:{key}", 
                json.dumps(data),
                expire=self.cache_ttl
            )
            return True
        except Exception as e:
            logger.error(f"Error storing in cache: {str(e)}")
            
        return False

    @timed("node_get_info")
    async def get_info(self) -> Dict[str, Any]:
        """Get node information."""
        return await self._request('GET', '/info', cache_key='info')

    @timed("node_get_block_by_height")
    async def get_block_by_height(self, height: int) -> Dict[str, Any]:
        """Get block data by height with optimized fetching."""
        try:
            # First get the block ID at the given height
            block_ids = await self._request(
                'GET', 
                f'/blocks/at/{height}',
                cache_key=f'blocks_at_{height}'
            )
            
            if not block_ids or not isinstance(block_ids, list):
                raise ValueError(f"Invalid response format for block at height {height}")
                
            block_id = block_ids[0]  # Get the first (and should be only) block ID
            
            # Now get the full block data using the ID
            block_data = await self._request(
                'GET', 
                f'/blocks/{block_id}',
                cache_key=f'block_{block_id}'
            )
            
            if not isinstance(block_data, dict):
                raise ValueError(f"Invalid block data format for block {block_id}")
                
            # Add height to block data since it's not included
            block_data['height'] = height
                
            performance_tracker.increment_counter("blocks_fetched")
            return block_data
            
        except Exception as e:
            logger.error(f"Error getting block at height {height}: {str(e)}", exc_info=True)
            raise

    @timed("node_get_block_range")
    async def get_blocks_in_range(self, start_height: int, end_height: int) -> List[Dict[str, Any]]:
        """Get multiple blocks in a range efficiently with improved concurrency and fault tolerance."""
        if start_height > end_height:
            raise ValueError(f"Start height ({start_height}) must be <= end height ({end_height})")
        
        total_blocks = end_height - start_height + 1
        logger.info(f"Fetching {total_blocks} blocks from height {start_height} to {end_height}")
        
        # Use a semaphore to control concurrency and prevent overloading the node
        # This creates a sliding window of concurrent requests
        max_concurrent = min(20, total_blocks)  # Cap at 20 concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_block_with_retry(height, max_retries=3):
            """Fetch a single block with retry logic and semaphore control."""
            retry_count = 0
            backoff = 1.0
            
            while retry_count <= max_retries:
                try:
                    async with semaphore:
                        return await self.get_block_by_height(height)
                except Exception as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.error(f"Failed to fetch block at height {height} after {max_retries} retries: {str(e)}")
                        return Exception(f"Failed to fetch block at height {height}: {str(e)}")
                    
                    # Exponential backoff
                    logger.warning(f"Retrying block fetch for height {height} (attempt {retry_count}/{max_retries})")
                    await asyncio.sleep(backoff)
                    backoff *= 2  # Exponential backoff
        
        # Create tasks for each block in the range
        tasks = [fetch_block_with_retry(height) for height in range(start_height, end_height + 1)]
        
        # Execute tasks concurrently and gather results
        # Use gather instead of wait to get results in order
        blocks = await asyncio.gather(*tasks)
        
        # Filter out exceptions
        valid_blocks = []
        error_count = 0
        
        for i, result in enumerate(blocks):
            height = start_height + i
            if isinstance(result, Exception):
                error_count += 1
                logger.error(f"Failed to fetch block at height {height}: {str(result)}")
                performance_tracker.increment_counter("blocks_fetch_errors")
            else:
                valid_blocks.append(result)
        
        success_rate = len(valid_blocks) / total_blocks if total_blocks > 0 else 0
        logger.info(
            f"Fetched {len(valid_blocks)}/{total_blocks} blocks successfully", 
            success_rate=f"{success_rate:.1%}",
            errors=error_count
        )
        
        # Sort by height to ensure proper order
        valid_blocks.sort(key=lambda block: block.get('height', 0))
        
        return valid_blocks

    async def get_block_by_id(self, block_id: str) -> Dict[str, Any]:
        """Get block by id."""
        return await self._request('GET', f'/blocks/{block_id}', cache_key=f'block_{block_id}')

    async def get_block_header_by_id(self, block_id: str) -> Dict[str, Any]:
        """Get block header by id."""
        return await self._request('GET', f'/blocks/{block_id}/header', cache_key=f'header_{block_id}')

    async def get_block_transactions(
        self,
        block_id: str,
        offset: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get block transactions."""
        cache_key = f'txs_{block_id}_{offset}_{limit}'
        return await self._request(
            'GET',
            f'/blocks/{block_id}/transactions',
            params={'offset': offset, 'limit': limit},
            cache_key=cache_key
        )

    async def get_transaction_by_id(self, tx_id: str) -> Dict[str, Any]:
        """Get transaction by id."""
        return await self._request('GET', f'/transactions/{tx_id}', cache_key=f'tx_{tx_id}')

    async def get_unconfirmed_transactions(
        self,
        offset: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get unconfirmed transactions."""
        return await self._request(
            'GET',
            '/transactions/unconfirmed',
            params={'offset': offset, 'limit': limit}
        )

    @timed("node_get_height")
    async def get_current_height(self) -> int:
        """Get current blockchain height."""
        info = await self.get_info()
        return info['fullHeight']

    async def is_synced(self) -> bool:
        """Check if node is synced."""
        info = await self.get_info()
        return info['headersHeight'] == info['fullHeight']
        
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the node client."""
        return {
            "requests_count": self.requests_count,
            "cache_hits": self.cache_hits,
            "errors_count": self.errors_count,
            "cache_hit_ratio": self.cache_hits / self.requests_count if self.requests_count > 0 else 0
        } 