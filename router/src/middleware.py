"""Custom middleware for the router application."""
import time
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from metrics import request_count, request_duration, auth_failures

logger = logging.getLogger(__name__)


async def track_requests_middleware(request: Request, call_next):
    """Track request metrics and add security headers."""
    start_time = time.time()

    # Skip metrics endpoint
    if request.url.path == "/metrics":
        return await call_next(request)

    # Initialize default values
    request.state.client_id = "unknown"
    request.state.cell_id = ""  # Empty string for "no cell ID"

    response = await call_next(request)

    # Track metrics for all requests (not just API calls)
    duration = time.time() - start_time
    
    # Get cell_id from request state, default to empty string if not set
    cell_id = getattr(request.state, "cell_id", "")
    
    # Handle different cases of cell_id
    if cell_id == "":
        # This is for health checks, root endpoint, etc.
        metric_cell_id = ""  # Will show as "No Cell ID" in dashboard
    elif cell_id not in ["1", "2", "3"]:
        # Invalid cell IDs
        metric_cell_id = "unknown"  # Will show as "Invalid Cell ID" in dashboard
    else:
        # Valid cell IDs
        metric_cell_id = cell_id
    
    client_id = getattr(request.state, "client_id", "unknown")

    request_duration.labels(cell_id=metric_cell_id, method=request.method).observe(duration)
    request_count.labels(
        cell_id=metric_cell_id,
        status=response.status_code,
        method=request.method,
        client=client_id
    ).inc()

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # Remove server header
    if "server" in response.headers:
        del response.headers["server"]

    return response


async def auth_exception_handler(request: Request, exc: HTTPException):
    """Handle authentication exceptions and track metrics."""
    if exc.status_code == 401:
        auth_failures.labels(reason="missing_key").inc()
    elif exc.status_code == 403:
        auth_failures.labels(reason="invalid_key").inc()

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None)
    )