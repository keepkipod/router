"""Shared dependencies for the application."""
import httpx
from functools import lru_cache
from config import settings

# Global HTTP client instance
_http_client = None


async def get_http_client() -> httpx.AsyncClient:
    """Get or create the global HTTP client."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=settings.request_timeout)
    return _http_client


async def close_http_client():
    """Close the global HTTP client."""
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None
