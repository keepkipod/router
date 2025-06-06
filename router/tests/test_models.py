"""Tests for Pydantic models."""
import pytest
from pydantic import ValidationError

from models import CellRequest, HealthResponse, RouteResponse


def test_cell_request_valid():
    """Test valid cell request."""
    request = CellRequest(cellID="1")
    assert request.cellID == "1"

    request = CellRequest(cellID="2")
    assert request.cellID == "2"

    request = CellRequest(cellID="3")
    assert request.cellID == "3"


def test_cell_request_invalid():
    """Test invalid cell request."""
    # Invalid cell ID
    with pytest.raises(ValidationError) as exc_info:
        CellRequest(cellID="999")
    assert "cellID must be one of" in str(exc_info.value)

    # Empty cell ID
    with pytest.raises(ValidationError):
        CellRequest(cellID="")

    # Missing cell ID
    with pytest.raises(ValidationError):
        CellRequest()


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


def test_route_response():
    """Test route response model."""
    # With dict response
    response = RouteResponse(
        cellID="1",
        upstream="nginx-1",
        status=200,
        response={"test": "data"}
    )
    assert response.cellID == "1"
    assert response.upstream == "nginx-1"
    assert response.status == 200
    assert response.response["test"] == "data"

    # With string response
    response = RouteResponse(
        cellID="2",
        upstream="nginx-2",
        status=200,
        response="Plain text response"
    )
    assert response.response == "Plain text response"