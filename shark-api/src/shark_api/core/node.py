"""Node interaction module."""
import aiohttp
from typing import Optional
from ..schemas.status import NodeStatus
from .config import settings
import logging

async def get_node_status() -> NodeStatus:
    """Get node status from the Ergo node."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{settings.NODE_URL}/info") as response:
            if response.status != 200:
                raise RuntimeError(f"Failed to get node status: {response.status}")
            data = await response.json()
            logging.error(f"Node response data: {data}")  # Debug log
            return NodeStatus(
                version=settings.VERSION,
                network=settings.NETWORK,
                block_height=data["fullHeight"],
                is_mining=data["isMining"],
                peers_count=data["peersCount"],
                unconfirmed_count=data["unconfirmedCount"]
            ) 