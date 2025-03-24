"""API middleware."""
import time
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from ..core.config import settings

class RateLimiter:
    """Rate limiting middleware."""

    def __init__(self):
        """Initialize rate limiter."""
        self.requests = {}
        self.window = 60  # 1 minute window

    def is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited."""
        now = time.time()
        client_requests = self.requests.get(client_id, [])
        
        # Remove old requests
        client_requests = [ts for ts in client_requests if now - ts < self.window]
        
        # Check rate limit
        if len(client_requests) >= settings.RATE_LIMIT_PER_MINUTE:
            return True
            
        # Add new request
        client_requests.append(now)
        self.requests[client_id] = client_requests
        return False

rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """Rate limiting middleware."""
    client_id = request.client.host
    
    if rate_limiter.is_rate_limited(client_id):
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too many requests",
                "code": "RATE_LIMIT_EXCEEDED",
                "details": {
                    "limit": settings.RATE_LIMIT_PER_MINUTE,
                    "window": "60 seconds"
                }
            }
        )
    
    return await call_next(request)

def add_middleware(app: FastAPI) -> None:
    """Add middleware to FastAPI application."""
    app.middleware("http")(rate_limit_middleware) 