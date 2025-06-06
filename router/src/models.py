"""Pydantic models for request/response validation."""
from typing import Dict, Union
from pydantic import BaseModel, Field, field_validator
from config import settings


class CellRequest(BaseModel):
    """Request model for routing to a specific cell."""
    cellID: str = Field(..., min_length=1, max_length=10, description="Target cell ID")

    @field_validator('cellID')
    @classmethod
    def validate_cell_id(cls, v):
        """Ensure cell ID exists in configured services."""
        valid_cells = list(settings.nginx_urls.keys())
        if v not in valid_cells:
            raise ValueError(f'cellID must be one of: {", ".join(valid_cells)}')
        return v


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str
    version: str
    upstreams: Dict[str, str]
    auth_enabled: bool
    auth_configured: bool


class RouteResponse(BaseModel):
    """Response model for route endpoint."""
    cellID: str
    upstream: str
    status: int
    response: Union[Dict, str]