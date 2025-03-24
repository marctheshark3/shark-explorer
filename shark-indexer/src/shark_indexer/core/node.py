import os
import asyncio
from typing import Any, Dict, Optional
import aiohttp
from aiohttp import ClientTimeout
import structlog
from dotenv import load_dotenv
import requests

load_dotenv()
logger = structlog.get_logger()

class NodeClient:
    def __init__(self):
        self.base_url = os.getenv('NODE_URL', 'http://127.0.0.1:9053')
        self.api_key = os.getenv('NODE_API_KEY')
        self.timeout = ClientTimeout(total=30)
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if self.api_key:
            self.headers['api_key'] = self.api_key

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Create aiohttp session."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self.headers
            )

    async def close(self):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request to node with retries."""
        if not self.session or self.session.closed:
            await self.connect()

        retries = 3
        backoff = 1

        while retries > 0:
            try:
                logger.debug(
                    "Making request to node",
                    method=method,
                    endpoint=endpoint,
                    url=f"{self.base_url}{endpoint}",
                    kwargs=kwargs
                )
                
                async with self.session.request(
                    method,
                    f"{self.base_url}{endpoint}",
                    **kwargs
                ) as response:
                    response.raise_for_status()
                    data = await response.text()  # Get raw text first
                    logger.debug(
                        "Received raw response",
                        endpoint=endpoint,
                        status=response.status,
                        data=data[:1000]  # Log first 1000 chars
                    )
                    
                    # Try to parse as JSON
                    try:
                        if data:
                            import json
                            return json.loads(data)
                        return {}
                    except json.JSONDecodeError as e:
                        logger.error(
                            "Failed to parse JSON response",
                            endpoint=endpoint,
                            error=str(e),
                            data=data[:1000],
                            exc_info=True
                        )
                        raise ValueError(f"Invalid JSON response: {str(e)}")

            except aiohttp.ClientError as e:
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
                    raise

    async def get_info(self) -> Dict[str, Any]:
        """Get node information."""
        return await self._request('GET', '/info')

    async def get_block_by_height(self, height: int) -> Dict[str, Any]:
        """Get block data by height."""
        try:
            # First get the block ID at the given height
            block_ids = await self._request('GET', f'/blocks/at/{height}')
            
            if not block_ids or not isinstance(block_ids, list):
                raise ValueError(f"Invalid response format for block at height {height}")
                
            block_id = block_ids[0]  # Get the first (and should be only) block ID
            
            # Now get the full block data using the ID
            block_data = await self._request('GET', f'/blocks/{block_id}')
            
            if not isinstance(block_data, dict):
                raise ValueError(f"Invalid block data format for block {block_id}")
                
            # Add height to block data since it's not included
            block_data['height'] = height
                
            return block_data
            
        except Exception as e:
            logger.error(f"Error getting block at height {height}: {str(e)}", exc_info=True)
            raise

    async def get_block_by_id(self, block_id: str) -> Dict[str, Any]:
        """Get block by id."""
        return await self._request('GET', f'/blocks/{block_id}')

    async def get_block_header_by_id(self, block_id: str) -> Dict[str, Any]:
        """Get block header by id."""
        return await self._request('GET', f'/blocks/{block_id}/header')

    async def get_block_transactions(
        self,
        block_id: str,
        offset: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get block transactions."""
        return await self._request(
            'GET',
            f'/blocks/{block_id}/transactions',
            params={'offset': offset, 'limit': limit}
        )

    async def get_transaction_by_id(self, tx_id: str) -> Dict[str, Any]:
        """Get transaction by id."""
        return await self._request('GET', f'/transactions/{tx_id}')

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

    async def get_current_height(self) -> int:
        """Get current blockchain height."""
        info = await self.get_info()
        return info['fullHeight']

    async def is_synced(self) -> bool:
        """Check if node is synced."""
        info = await self.get_info()
        return info['headersHeight'] == info['fullHeight'] 