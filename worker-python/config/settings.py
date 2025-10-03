"""
Configuration for Python AI Worker
Loads from environment variables with .env file support
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/article_extraction"
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    
    # Queue
    queue_name: str = "default"
    worker_concurrency: int = 5
    
    # AI
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash-latest"
    
    # Browser
    browser_headless: bool = True
    browser_timeout: int = 30000
    
    # Storage
    storage_path: str = "storage"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = "config/.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()



