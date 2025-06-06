import os
import json
import logging
import time
from typing import Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import httpx
import uvicorn
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry
from starlette.responses import Response

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
registry = CollectorRegistry()
request_count = Counter(
    'router_requests_total', 
    'Total number of requests by cell_id and status',
    ['cell_id', 'status', 'method'],
    registry=registry
)
request_duration = Histogram(
    'router_request_duration_seconds',
    'Request duration in seconds',
    ['cell_id', 'method'],
    registry=registry
)
upstream_errors = Counter(
    'router_upstream_errors_total',
    'Total number of upstream errors by cell_id',
    ['cell_id', 'upstream'],
    registry=registry
)

# Configuration
NGINX_SERVICES = {
    "1": os.getenv("NGINX_1_URL", "http://nginx-1.nginx.svc.cluster.local"),
    "2": os.getenv("NGINX_2_URL", "http://nginx-2.nginx.svc.cluster.local"),
    "3": os.getenv("NGINX_3_URL", "http://nginx-3.nginx.svc.cluster.local"),
}

# Request timeout
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))

# Pydantic models
class CellRequest(BaseModel):
    cellID: str = Field(..., min_length=1, max_length=10)
    
    @validator('cellID')
    def validate_cell_id(cls, v):
        if v not in NGINX_SERVICES:
            raise ValueError(f'cellID must be one of: {", ".join(NGINX_SERVICES.keys())}')
        return v

class HealthResponse(BaseModel):
    status: str
    version: str
    upstreams: Dict[str, str]

# Async context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting router application")
    logger.info(f"Configured upstreams: {NGINX_SERVICES}")
    
    # Create httpx client
    app.state.http_client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
    
    yield
    
    # Shutdown
    logger.info("Shutting down router application")
    await app.state.http_client.aclose()

# Create FastAPI app
app = FastAPI(
    title="Cell Router API",
    description="Routes requests to appropriate NGINX instances based on cell ID",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Combined middleware for request tracking and security headers
@app.middleware("http")
async def track_requests_and_add_security_headers(request: Request, call_next):
    start_time = time.time()
    
    # Skip metrics endpoint
    if request.url.path == "/metrics":
        response = await call_next(request)
        return response
    
    response = await call_next(request)
    
    # Track metrics for API calls
    if request.url.path.startswith("/api/"):
        duration = time.time() - start_time
        cell_id = getattr(request.state, "cell_id", "unknown")
        request_duration.labels(cell_id=cell_id, method=request.method).observe(duration)
        request_count.labels(
            cell_id=cell_id,
            status=response.status_code,
            method=request.method
        ).inc()
    
    # Add security headers to all responses (except metrics)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    # Remove server header if present
    if "server" in response.headers:
        del response.headers["server"]
    
    return response

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with upstream status"""
    upstream_status = {}
    
    for cell_id, url in NGINX_SERVICES.items():
        try:
            response = await app.state.http_client.get(f"{url}/health", timeout=5)
            upstream_status[f"nginx-{cell_id}"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            logger.warning(f"Health check failed for nginx-{cell_id}: {str(e)}")
            upstream_status[f"nginx-{cell_id}"] = "unreachable"
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        upstreams=upstream_status
    )

# Readiness check
@app.get("/ready")
async def readiness_check():
    """Readiness probe endpoint"""
    # Check if at least one upstream is available
    for cell_id, url in NGINX_SERVICES.items():
        try:
            response = await app.state.http_client.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                return {"status": "ready"}
        except Exception:
            continue
    
    raise HTTPException(status_code=503, detail="No healthy upstreams available")

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

# Main routing endpoint
@app.post("/api/route")
async def route_request(cell_request: CellRequest, request: Request):
    """Route request to appropriate NGINX instance based on cell ID"""
    cell_id = cell_request.cellID
    nginx_url = NGINX_SERVICES[cell_id]
    
    # Store cell_id in request state for metrics
    request.state.cell_id = cell_id
    
    # Route to the /api endpoint on NGINX
    target_url = f"{nginx_url}/api"
    
    logger.info(f"Routing request for cell_id={cell_id} to {target_url}")
    
    try:
        # Forward the request to the appropriate NGINX instance
        response = await app.state.http_client.post(
            target_url,
            json={"cellID": cell_id, "timestamp": time.time()},
            headers={
                "X-Cell-ID": cell_id,
                "X-Forwarded-For": request.client.host if request.client else "unknown",
                "X-Original-URI": str(request.url),
            }
        )
        
        # Return the response from NGINX
        return {
            "cellID": cell_id,
            "upstream": f"nginx-{cell_id}",
            "status": response.status_code,
            "response": response.json() if response.headers.get("content-type") == "application/json" else response.text
        }
        
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

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Cell Router",
        "version": "1.0.0",
        "endpoints": {
            "route": "/api/route",
            "health": "/health",
            "ready": "/ready",
            "metrics": "/metrics",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )