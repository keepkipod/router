"""Tests for routing endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from main import app
from config import settings

client = TestClient(app)


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


def test_route_missing_cell_id():
    """Test routing with missing cell ID."""
    response = client.post("/api/route", json={})
    assert response.status_code == 422


def test_route_with_auth_enabled():
    """Test routing with authentication enabled."""
    with patch('config.settings.api_key_enabled', True):
        with patch('auth.VALID_API_KEYS', {"test-key": "test-client"}):
            # Without API key
            response = client.post("/api/route", json={"cellID": "1"})
            assert response.status_code == 401

            # With valid API key
            with patch('dependencies.get_http_client') as mock_get_client:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"test": "response"}
                mock_response.headers = {"content-type": "application/json"}
                mock_client.post.return_value = mock_response
                mock_get_client.return_value = mock_client

                response = client.post(
                    "/api/route", 
                    json={"cellID": "1"},
                    headers={"X-API-Key": "test-key"}
                )
                assert response.status_code == 200