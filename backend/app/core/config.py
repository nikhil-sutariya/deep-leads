"""
Application configuration management
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    google_api_key: str
    perplexity_api_key: Optional[str] = None
    
    # Provider Configuration
    ai_provider: str = "gemini"  # Options: "gemini" or "perplexity"
    
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/leadfinder"

    secret_key: str
    oauth_algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    client_origin: List[str] = ["http://localhost:3000"]
    
    # Email Configuration
    smtp_host: Optional[str] = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None

    api_base_url: str = "http://localhost:8000"
    
    # Application Settings
    environment: str = "development"
    log_level: str = "INFO"
    max_leads_per_search: int = 50
    rate_limit_per_minute: int = 30
    
    # Lead Discovery Settings
    min_company_size: int = 10
    max_company_size: int = 100
    min_funding_millions: float = 0.5
    max_funding_millions: float = 10.0
    
    # Search Configuration
    search_timeout_seconds: int = 30
    max_retries: int = 3

    default_admin_email: str = "admin@example.com"
    default_admin_password: str = "Admin@1234"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",  # This permits extra keys from .env
        case_sensitive = False
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
