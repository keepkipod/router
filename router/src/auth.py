"""Authentication module for API key validation."""
import json
import logging
from typing import Optional, Dict
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from config import settings

logger = logging.getLogger(__name__)

# API Key header configuration
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Load valid API keys
def load_api_keys() -> Dict[str, str]:
    """Load API keys from configuration."""
    api_keys = {}

    if settings.api_keys_json:
        try:
            api_keys = json.loads(settings.api_keys_json)
            logger.info(f"Loaded {len(api_keys)} API keys from configuration")
        except json.JSONDecodeError:
            logger.error("Failed to parse API_KEYS_JSON - ensure it's valid JSON")

    if not api_keys and settings.api_key_enabled:
        logger.warning("API authentication is enabled but no API keys are configured!")

    return api_keys


# Initialize API keys
VALID_API_KEYS = load_api_keys()


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> Optional[str]:
    """Verify API key if authentication is enabled."""
    if not settings.api_key_enabled:
        return "anonymous"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key not in VALID_API_KEYS:
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    return VALID_API_KEYS[api_key]