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

    # Initialize client_id
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

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # Remove server header - use del instead of pop
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