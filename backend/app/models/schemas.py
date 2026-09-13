"""Pydantic schemas for request and response validation."""
from datetime import datetime, timezone
from typing import Optional, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response schema for the system health check."""
    status: str = Field(default="healthy", description="Current health status of the service")
    app_name: str = Field(description="Name of the application")
    version: str = Field(description="Semantic version of the application")
    environment: str = Field(description="Current deployment environment")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the health check"
    )


class APIErrorResponse(BaseModel):
    """Standard error response payload."""
    detail: str = Field(description="Error message detailing the failure")
    error_code: Optional[str] = Field(default=None, description="Optional machine-readable error code")
    context: Optional[dict[str, Any]] = Field(default=None, description="Additional context or validation details")
