"""Central API routing for RevAI."""
from fastapi import APIRouter

try:
    from backend.app.core.config import settings
    from backend.app.models.schemas import HealthResponse
except ImportError:  # pragma: no cover
    from app.core.config import settings
    from app.models.schemas import HealthResponse

api_router = APIRouter()


@api_router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="System Health Check",
    description="Returns the operational status, application version, and environment metadata."
)
async def health_check() -> HealthResponse:
    """Return system operational status and metadata."""
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV
    )
