"""Tests for main application endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "upstreams" in data


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Cell Router API"


def test_route_valid_cell():
    """Test routing with valid cell ID."""
    with patch('dependencies.get_http_client') as mock_get_client:
        # Create async mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "response"}
        mock_response.headers = {"content-type": "application/json"}
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        # Disable auth for testing
        with patch('config.settings.api_key_enabled', False):
            response = client.post("/api/route", json={"cellID": "1"})
            assert response.status_code == 200
            data = response.json()
            assert data["cellID"] == "1"
            assert data["upstream"] == "nginx-1"


def test_route_invalid_cell():
    """Test routing with invalid cell ID."""
    response = client.post("/api/route", json={"cellID": "999"})
    assert response.status_code == 422


def test_metrics_endpoint():
    """Test metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "router_requests_total" in response.text