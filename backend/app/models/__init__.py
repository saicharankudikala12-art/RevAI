"""Data schemas and models."""
try:
    from backend.app.models.schemas import HealthResponse, PDFUploadResponse, APIErrorResponse
except ImportError:  # pragma: no cover
    from app.models.schemas import HealthResponse, PDFUploadResponse, APIErrorResponse

__all__ = ["HealthResponse", "PDFUploadResponse", "APIErrorResponse"]
