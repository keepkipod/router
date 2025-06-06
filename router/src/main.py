import os
import json
import logging
import time
from typing import Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
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

# API Key Configuration
API_KEY_ENABLED = os.getenv("API_KEY_ENABLED", "false").lower() == "true"
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Load API keys from environment
# No hardcode API keys in source code
# Keys should be provided via:
# 1. Kubernetes Secrets (production)
# 2. Environment variables (development)
# 3. External secret management systems (HashiCorp Vault, AWS Secrets Manager, etc.)
VALID_API_KEYS = {}

# Try to load from JSON environment variable
# Expected format: {"api-key-1": "client-name-1", "api-key-2": "client-name-2"}
api_keys_json = os.getenv("API_KEYS_JSON")
if api_keys_json:
    try:
        VALID_API_KEYS = json.loads(api_keys_json)
        logger.info(f"Loaded {len(VALID_API_KEYS)} API keys from environment")
    except json.JSONDecodeError:
        logger.error("Failed to parse API_KEYS_JSON - ensure it's valid JSON")

# Fallback to single API_KEY environment variable if JSON not provided
if not VALID_API_KEYS and os.getenv("API_KEY"):
    VALID_API_KEYS[os.getenv("API_KEY")] = os.getenv("API_KEY_CLIENT", "default-client")
    logger.info("Loaded single API key from API_KEY environment variable")

# Log warning if auth is enabled but no keys are configured
if API_KEY_ENABLED and not VALID_API_KEYS:
    logger.warning("API authentication is enabled but no API keys are configured!")
    logger.warning("Set API_KEYS_JSON or API_KEY environment variables")

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> Optional[str]:
    """Verify API key if authentication is enabled"""
    if not API_KEY_ENABLED:
        return "anonymous"
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if api_key not in VALID_API_KEYS:
        # Log failed authentication attempts for security monitoring
        logger.warning(f"Invalid API key attempt from {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return VALID_API_KEYS[api_key]

# Prometheus metrics
registry = CollectorRegistry()
request_count = Counter(
    'router_requests_total', 
    'Total number of requests by cell_id and status',
    ['cell_id', 'status', 'method', 'client'],
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
auth_failures = Counter(
    'router_auth_failures_total',
    'Total number of authentication failures',
    ['reason'],
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
    auth_enabled: bool
    auth_configured: bool  # Indicates if keys are loaded

# Async context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting router application")
    logger.info(f"Configured upstreams: {NGINX_SERVICES}")
    logger.info(f"API Key authentication: {'ENABLED' if API_KEY_ENABLED else 'DISABLED'}")
    if API_KEY_ENABLED:
        logger.info(f"API keys configured: {'YES' if VALID_API_KEYS else 'NO'}")
    
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
    
    # Store client info in request state for tracking
    request.state.client_id = "unknown"
    
    response = await call_next(request)
    
    # Track metrics for API calls
    if request.url.path.startswith("/api/"):
        duration = time.time() - start_time
        cell_id = getattr(request.state, "cell_id", "unknown")
        client_id = getattr(request.state, "client_id", "unknown")
        request_duration.labels(cell_id=cell_id, method=request.method).observe(duration)
        request_count.labels(
            cell_id=cell_id,
            status=response.status_code,
            method=request.method,
            client=client_id
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

# Exception handler for auth failures
@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        auth_failures.labels(reason="missing_key").inc()
    elif exc.status_code == 403:
        auth_failures.labels(reason="invalid_key").inc()
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers if hasattr(exc, "headers") else None
    )

# Health check endpoint (no auth required)
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
        upstreams=upstream_status,
        auth_enabled=API_KEY_ENABLED,
        auth_configured=bool(VALID_API_KEYS) if API_KEY_ENABLED else True
    )

# Readiness check (no auth required)
@app.get("/ready")
async def readiness_check():
    """Readiness probe endpoint"""
    # If auth is enabled but no keys configured, service is not ready
    if API_KEY_ENABLED and not VALID_API_KEYS:
        raise HTTPException(
            status_code=503, 
            detail="Authentication enabled but no API keys configured"
        )
    
    # Check if at least one upstream is available
    for cell_id, url in NGINX_SERVICES.items():
        try:
            response = await app.state.http_client.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                return {"status": "ready", "auth_enabled": API_KEY_ENABLED}
        except Exception:
            continue
    
    raise HTTPException(status_code=503, detail="No healthy upstreams available")

# Metrics endpoint (no auth required)
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

# Main routing endpoint (with optional auth)
@app.post("/api/route")
async def route_request(
    cell_request: CellRequest, 
    request: Request,
    client_id: str = Depends(verify_api_key)
):
    """Route request to appropriate NGINX instance based on cell ID"""
    cell_id = cell_request.cellID
    nginx_url = NGINX_SERVICES[cell_id]
    
    # Store cell_id and client_id in request state for metrics
    request.state.cell_id = cell_id
    request.state.client_id = client_id
    
    # Route to the /api endpoint on NGINX
    target_url = f"{nginx_url}/api"
    
    logger.info(f"Routing request from client '{client_id}' for cell_id={cell_id} to {target_url}")
    
    try:
        # Forward the request to the appropriate NGINX instance
        response = await app.state.http_client.post(
            target_url,
            json={"cellID": cell_id, "timestamp": time.time()},
            headers={
                "X-Cell-ID": cell_id,
                "X-Client-ID": client_id,
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

# Root endpoint (no auth required)
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Cell Router",
        "version": "1.0.0",
        "auth_enabled": API_KEY_ENABLED,
        "auth_configured": bool(VALID_API_KEYS) if API_KEY_ENABLED else True,
        "endpoints": {
            "route": "/api/route (requires auth)" if API_KEY_ENABLED else "/api/route",
            "health": "/health",
            "ready": "/ready",
            "metrics": "/metrics",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    # SECURITY REMINDER: Configure API keys via environment variables!
    # Example:
    # export API_KEY_ENABLED=true
    # export API_KEYS_JSON='{"secure-key-1": "client1", "secure-key-2": "client2"}'
    # Or use Kubernetes secrets as shown in the deployment
    
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