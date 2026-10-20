"""Automated tests for health check and root endpoints."""
import pytest
from fastapi.testclient import TestClient

try:
    from backend.app.main import app
    from backend.app.core.config import settings
except ImportError:
    from app.main import app
    from app.core.config import settings


@pytest.fixture
def client():
    """Test client fixture."""
    with TestClient(app) as test_client:
        yield test_client


def test_root_endpoint(client):
    """Verify root / returns 200 with HTML when frontend is mounted, or JSON fallback."""
    response = client.get("/")
    assert response.status_code == 200
    if "text/html" in response.headers.get("content-type", ""):
        assert "RevAI" in response.text
        assert "<!DOCTYPE html>" in response.text
    else:
        data = response.json()
        assert data["name"] == settings.APP_NAME
        assert data["status"] == "online"


def test_production_secret_key_enforcement():
    """Verify that in production mode, default secret key raises ValueError."""
    from backend.app.core.config import Settings, DEFAULT_DEV_SECRET_KEY
    prod_settings_default_secret = Settings(
        APP_ENV="production",
        SECRET_KEY=DEFAULT_DEV_SECRET_KEY
    )
    with pytest.raises(ValueError, match="SECRET_KEY must be explicitly set"):
        prod_settings_default_secret.validate_production_security()

    # With a custom secure key, validation passes
    prod_settings_secure = Settings(
        APP_ENV="production",
        SECRET_KEY="super-secret-production-random-token-key-12345"
    )
    prod_settings_secure.validate_production_security()  # Should not raise


def test_health_check_endpoint(client):
    """Verify /api/health returns 200 with valid HealthResponse schema."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == settings.APP_NAME
    assert data["version"] == settings.APP_VERSION
    assert "timestamp" in data
    assert "environment" in data


def test_cors_headers(client):
    """Verify CORS middleware responds with correct headers on preflight."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
