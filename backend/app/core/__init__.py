"""Core settings and configuration."""
try:
    from backend.app.core.config import settings
except ImportError:  # pragma: no cover
    from app.core.config import settings

__all__ = ["settings"]
