"""Node API client for interacting with the Ergo blockchain node."""
import logging
from typing import Dict, Any, Optional

import aiohttp
from fastapi import Depends

from ..core.config import settings

logger = logging.getLogger(__name__)

class Node:
    """Client for interacting with Ergo node."""
    
    def __init__(self):
        """Initialize node client with configurations."""
        self.base_url = settings.NODE_URL
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        logger.info(f"Initialized Node client with URL: {self.base_url}")
    
    async def get_info(self) -> Dict[str, Any]:
        """
        Get node information.
        
        Returns:
            Dict containing node information
        """
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(f"{self.base_url}/info") as response:
                    if response.status != 200:
                        logger.error(f"Failed to get node info: {response.status}")
                        return {"error": f"Failed to get node info: {response.status}", "data": {}}
                    
                    data = await response.json()
                    return {"data": data}
        except Exception as e:
            logger.error(f"Error getting node info: {str(e)}")
            return {"error": str(e), "data": {}}
    
    async def get_block_by_height(self, height: int) -> Dict[str, Any]:
        """
        Get block at specified height.
        
        Args:
            height: Block height
            
        Returns:
            Dict containing block data
        """
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                # First get block ID at height
                async with session.get(f"{self.base_url}/blocks/at/{height}") as response:
                    if response.status != 200:
                        logger.error(f"Failed to get block at height {height}: {response.status}")
                        return {"error": f"Failed to get block at height {height}", "data": {}}
                    
                    block_ids = await response.json()
                    if not block_ids or not isinstance(block_ids, list):
                        logger.error(f"Invalid block IDs format at height {height}")
                        return {"error": "Invalid block IDs format", "data": {}}
                    
                    block_id = block_ids[0]
                    
                # Now get full block by ID
                async with session.get(f"{self.base_url}/blocks/{block_id}") as response:
                    if response.status != 200:
                        logger.error(f"Failed to get block {block_id}: {response.status}")
                        return {"error": f"Failed to get block {block_id}", "data": {}}
                    
                    block_data = await response.json()
                    block_data["height"] = height  # Add height to response
                    return {"data": block_data}
        except Exception as e:
            logger.error(f"Error getting block at height {height}: {str(e)}")
            return {"error": str(e), "data": {}}
    
    async def get_transaction(self, tx_id: str) -> Dict[str, Any]:
        """
        Get transaction by ID.
        
        Args:
            tx_id: Transaction ID
            
        Returns:
            Dict containing transaction data
        """
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(f"{self.base_url}/transactions/{tx_id}") as response:
                    if response.status != 200:
                        logger.error(f"Failed to get transaction {tx_id}: {response.status}")
                        return {"error": f"Failed to get transaction {tx_id}", "data": {}}
                    
                    tx_data = await response.json()
                    return {"data": tx_data}
        except Exception as e:
            logger.error(f"Error getting transaction {tx_id}: {str(e)}")
            return {"error": str(e), "data": {}} 