"""Health check endpoints."""
import logging
from fastapi import APIRouter, HTTPException
from models import HealthResponse
from config import settings
from auth import VALID_API_KEYS
from dependencies import get_http_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with upstream status."""
    http_client = await get_http_client()
    upstream_status = {}
    
    for cell_id, url in settings.nginx_urls.items():
        try:
            response = await http_client.get(f"{url}/health", timeout=5)
            upstream_status[f"nginx-{cell_id}"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            logger.warning(f"Health check failed for nginx-{cell_id}: {str(e)}")
            upstream_status[f"nginx-{cell_id}"] = "unreachable"
    
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        upstreams=upstream_status,
        auth_enabled=settings.api_key_enabled,
        auth_configured=bool(VALID_API_KEYS) if settings.api_key_enabled else True
    )


@router.get("/ready")
async def readiness_check():
    """Readiness probe endpoint."""
    # Check auth configuration
    if settings.api_key_enabled and not VALID_API_KEYS:
        raise HTTPException(
            status_code=503,
            detail="Authentication enabled but no API keys configured"
        )
    
    # Check upstream availability
    http_client = await get_http_client()
    for cell_id, url in settings.nginx_urls.items():
        try:
            response = await http_client.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                return {"status": "ready", "auth_enabled": settings.api_key_enabled}
        except Exception:
            continue
    
    raise HTTPException(status_code=503, detail="No healthy upstreams available")
