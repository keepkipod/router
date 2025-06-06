"""Tests for Pydantic models."""
import pytest
from pydantic import ValidationError
from models import CellRequest, HealthResponse, RouteResponse


def test_cell_request_valid():
    """Test valid cell request."""
    request = CellRequest(cellID="1")
    assert request.cellID == "1"


def test_cell_request_invalid():
    """Test invalid cell request."""
    with pytest.raises(ValidationError):
        CellRequest(cellID="999")
    
    with pytest.raises(ValidationError):
        CellRequest(cellID="")


def test_health_response():
    """Test health response model."""
    response = HealthResponse(
        status="healthy",
        version="1.0.0",
        upstreams={"nginx-1": "healthy"},
        auth_enabled=False,
        auth_configured=True
    )
    assert response.status == "healthy"
    assert response.upstreams["nginx-1"] == "healthy"
