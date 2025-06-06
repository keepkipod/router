"""Configuration management for the router application."""
import os
from typing import Dict, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings with validation."""

    # API Authentication
    api_key_enabled: bool = Field(default=False, env="API_KEY_ENABLED")
    api_keys_json: str = Field(default="", env="API_KEYS_JSON")

    # Upstream services
    nginx_urls: Dict[str, str] = {
        "1": os.getenv("NGINX_1_URL", "http://nginx-1-nginx-cell.nginx.svc.cluster.local"),
        "2": os.getenv("NGINX_2_URL", "http://nginx-2-nginx-cell.nginx.svc.cluster.local"),
        "3": os.getenv("NGINX_3_URL", "http://nginx-3-nginx-cell.nginx.svc.cluster.local"),
    }

    # Request configuration
    request_timeout: float = Field(default=30.0, env="REQUEST_TIMEOUT")

    # Application metadata
    app_name: str = "Cell Router API"
    app_version: str = "1.0.0"
    app_description: str = "Routes requests to appropriate NGINX instances based on cell ID"

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    @field_validator("api_key_enabled", mode='before')
    @classmethod
    def parse_bool(cls, v):
        """Parse boolean from string."""
        if isinstance(v, str):
            return v.lower() == "true"
        return v

    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()