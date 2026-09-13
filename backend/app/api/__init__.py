"""API router and endpoint definitions."""
try:
    from backend.app.api.routes import api_router
except ImportError:  # pragma: no cover
    from app.api.routes import api_router

__all__ = ["api_router"]
