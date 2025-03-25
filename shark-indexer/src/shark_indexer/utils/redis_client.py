import os
import json
import asyncio
from typing import Dict, Any, Optional, List, Union
import structlog
import aioredis
from dotenv import load_dotenv
from ..utils.performance import timed, performance_tracker

load_dotenv()
logger = structlog.get_logger()

class RedisClient:
    """Redis client for caching and other shared data storage needs."""
    
    def __init__(self):
        self.host = os.getenv('REDIS_HOST', 'localhost')
        self.port = int(os.getenv('REDIS_PORT', '6379'))
        self.db = int(os.getenv('REDIS_DB', '0'))
        self.password = os.getenv('REDIS_PASSWORD')
        self.client: Optional[aioredis.Redis] = None
        self.is_connected = False
        self.connection_retries = 0
        self.operations_count = 0
        self.errors_count = 0
        
    @timed("redis_connect")
    async def connect(self, max_retries: int = 5, retry_delay: int = 2) -> bool:
        """Connect to Redis server with retries."""
        if self.is_connected and self.client:
            return True
            
        for attempt in range(max_retries):
            try:
                connection_url = f"redis://{self.host}:{self.port}/{self.db}"
                if self.password:
                    connection_url = f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
                    
                self.client = aioredis.from_url(
                    connection_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                
                # Verify connection with a ping
                await self.client.ping()
                self.is_connected = True
                logger.info(f"Successfully connected to Redis at {self.host}:{self.port}")
                return True
                
            except Exception as e:
                self.connection_retries += 1
                logger.error(f"Failed to connect to Redis (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
        
        logger.error(f"Failed to connect to Redis after {max_retries} attempts")
        return False
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            self.is_connected = False
            logger.info("Redis connection closed")
    
    @timed("redis_get")
    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis."""
        if not self.is_connected:
            if not await self.connect():
                return None
        
        self.operations_count += 1
        try:
            return await self.client.get(key)
        except Exception as e:
            self.errors_count += 1
            logger.error(f"Error getting key '{key}' from Redis: {str(e)}")
            return None
    
    @timed("redis_set")
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set a value in Redis with optional expiration."""
        if not self.is_connected:
            if not await self.connect():
                return False
        
        self.operations_count += 1
        try:
            if expire is not None:
                await self.client.set(key, value, ex=expire)
            else:
                await self.client.set(key, value)
            return True
        except Exception as e:
            self.errors_count += 1
            logger.error(f"Error setting key '{key}' in Redis: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        if not self.is_connected:
            if not await self.connect():
                return False
        
        self.operations_count += 1
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            self.errors_count += 1
            logger.error(f"Error deleting key '{key}' from Redis: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        if not self.is_connected:
            if not await self.connect():
                return False
        
        self.operations_count += 1
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            self.errors_count += 1
            logger.error(f"Error checking existence of key '{key}' in Redis: {str(e)}")
            return False
    
    async def set_json(self, key: str, data: Dict[str, Any], expire: Optional[int] = None) -> bool:
        """Set JSON data in Redis."""
        try:
            json_data = json.dumps(data)
            return await self.set(key, json_data, expire)
        except Exception as e:
            logger.error(f"Error serializing JSON for key '{key}': {str(e)}")
            return False
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON data from Redis."""
        data = await self.get(key)
        if not data:
            return None
        
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from Redis key '{key}': {str(e)}")
            return None
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter in Redis."""
        if not self.is_connected:
            if not await self.connect():
                return None
        
        self.operations_count += 1
        try:
            return await self.client.incrby(key, amount)
        except Exception as e:
            self.errors_count += 1
            logger.error(f"Error incrementing key '{key}' in Redis: {str(e)}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Redis client statistics."""
        return {
            "is_connected": self.is_connected,
            "operations_count": self.operations_count,
            "errors_count": self.errors_count,
            "connection_retries": self.connection_retries,
            "error_rate": self.errors_count / max(1, self.operations_count)
        }

# Global Redis client instance
redis_client = RedisClient() 