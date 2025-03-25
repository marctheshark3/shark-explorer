"""API service configuration."""
import os
from typing import Optional, List
from pydantic import PostgresDsn, BaseSettings

class Settings(BaseSettings):
    """API service settings."""
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Shark Explorer API"
    PROJECT_DESCRIPTION: str = "API for accessing Ergo blockchain data"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Database Settings
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "changeme")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "ergo_explorer")
    
    # Node Settings
    NODE_URL: str = os.getenv("NODE_URL", "http://192.168.1.195:9053")
    NETWORK: str = os.getenv("NETWORK", "mainnet")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Get database URI."""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings() 