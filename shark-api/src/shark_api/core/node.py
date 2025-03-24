"""Node interaction module."""
import aiohttp
from typing import Optional
from ..schemas.status import NodeStatus
from .config import settings

async def get_node_status() -> NodeStatus:
    """Get node status from the Ergo node."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{settings.NODE_URL}/info") as response:
            if response.status != 200:
                raise RuntimeError(f"Failed to get node status: {response.status}")
            data = await response.json()
            return NodeStatus(
                height=data["fullHeight"],
                headerId=data["bestHeaderId"],
                lastBlockTime=data["lastBlockTimestamp"],
                isMining=data["isMining"],
                peersCount=data["peersCount"],
                unconfirmedCount=data["unconfirmedCount"]
            ) 