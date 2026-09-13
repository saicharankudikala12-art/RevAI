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
    """Verify root / returns 200 with online status and links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == settings.APP_NAME
    assert data["status"] == "online"
    assert data["documentation"] == "/docs"
    assert data["health"] == "/api/health"


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
