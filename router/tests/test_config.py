"""Tests for configuration module."""
import os
import pytest
from config import Settings


def test_default_settings():
    """Test default settings values."""
    settings = Settings()
    assert settings.api_key_enabled is False
    assert settings.request_timeout == 30.0
    assert settings.app_name == "Cell Router API"
    assert len(settings.nginx_urls) == 3


def test_env_override():
    """Test environment variable override."""
    os.environ["API_KEY_ENABLED"] = "true"
    os.environ["REQUEST_TIMEOUT"] = "60"
    
    settings = Settings()
    assert settings.api_key_enabled is True
    assert settings.request_timeout == 60.0
    
    # Cleanup
    del os.environ["API_KEY_ENABLED"]
    del os.environ["REQUEST_TIMEOUT"]
