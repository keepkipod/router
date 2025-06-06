"""Main application entry point."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response, PlainTextResponse

from config import settings
from logging_config import setup_logging
from middleware import track_requests_middleware, auth_exception_handler
from metrics import registry
from dependencies import get_http_client, close_http_client
import health
import routing
import auth

# Setup logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Configured upstreams: {settings.nginx_urls}")
    logger.info(f"API Key authentication: {'ENABLED' if settings.api_key_enabled else 'DISABLED'}")

    # Initialize HTTP client
    await get_http_client()

    yield

    # Shutdown
    logger.info("Shutting down router application")
    await close_http_client()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.middleware("http")(track_requests_middleware)

# Add exception handlers
app.add_exception_handler(HTTPException, auth_exception_handler)

# Include routers
app.include_router(health.router)
app.include_router(routing.router)


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "auth_enabled": settings.api_key_enabled,
        "auth_configured": bool(auth.VALID_API_KEYS) if settings.api_key_enabled else True,
        "endpoints": {
            "route": "/api/route" + (" (requires auth)" if settings.api_key_enabled else ""),
            "health": "/health",
            "ready": "/ready",
            "metrics": "/metrics",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
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
                "level": settings.log_level.upper(),
                "handlers": ["default"],
            },
        }
    )