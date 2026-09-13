"""Data schemas and models."""
try:
    from backend.app.models.schemas import HealthResponse, APIErrorResponse
except ImportError:  # pragma: no cover
    from app.models.schemas import HealthResponse, APIErrorResponse

__all__ = ["HealthResponse", "APIErrorResponse"]
