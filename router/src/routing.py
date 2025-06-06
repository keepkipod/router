"""Main routing logic for cell-based request routing."""
import time
import logging
from fastapi import APIRouter, Request, Depends, HTTPException, status
import httpx
from models import CellRequest, RouteResponse
from config import settings
from auth import verify_api_key
from metrics import upstream_errors
from dependencies import get_http_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["routing"])


@router.post("/route", response_model=RouteResponse)
async def route_request(
    cell_request: CellRequest,
    request: Request,
    client_id: str = Depends(verify_api_key)
):
    """Route request to appropriate NGINX instance based on cell ID."""
    cell_id = cell_request.cellID
    nginx_url = settings.nginx_urls[cell_id]
    
    # Store state for metrics
    request.state.cell_id = cell_id
    request.state.client_id = client_id
    
    target_url = f"{nginx_url}/api"
    logger.info(f"Routing request from client '{client_id}' for cell_id={cell_id} to {target_url}")
    
    http_client = await get_http_client()
    
    try:
        response = await http_client.post(
            target_url,
            json={"cellID": cell_id, "timestamp": time.time()},
            headers={
                "X-Cell-ID": cell_id,
                "X-Client-ID": client_id,
                "X-Forwarded-For": request.client.host if request.client else "unknown",
                "X-Original-URI": str(request.url),
            }
        )
        
        return RouteResponse(
            cellID=cell_id,
            upstream=f"nginx-{cell_id}",
            status=response.status_code,
            response=response.json() if response.headers.get("content-type") == "application/json" else response.text
        )
        
    except httpx.TimeoutException:
        upstream_errors.labels(cell_id=cell_id, upstream=f"nginx-{cell_id}").inc()
        logger.error(f"Timeout connecting to nginx-{cell_id}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Timeout connecting to nginx-{cell_id}"
        )
    except httpx.RequestError as e:
        upstream_errors.labels(cell_id=cell_id, upstream=f"nginx-{cell_id}").inc()
        logger.error(f"Error connecting to nginx-{cell_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error connecting to nginx-{cell_id}"
        )
    except Exception as e:
        logger.error(f"Unexpected error routing to nginx-{cell_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
