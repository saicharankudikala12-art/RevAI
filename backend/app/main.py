"""RevAI Application Entry Point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from backend.app.core.config import settings
    from backend.app.api.routes import api_router
except ImportError:  # pragma: no cover
    from app.core.config import settings
    from app.api.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown routines."""
    # Startup: logging and environment confirmation
    print(f"[{settings.APP_NAME}] Initialized in {settings.APP_ENV} mode.")
    yield
    # Shutdown: clean up any resources
    print(f"[{settings.APP_NAME}] Shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="RevAI - AI-powered last-minute exam revision backend service.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS for decoupled frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.cors_origins_list else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes under /api
app.include_router(api_router, prefix="/api")


@app.get("/", tags=["Root"], summary="API Root")
async def root():
    """Root endpoint welcoming developers and pointing to documentation."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "documentation": "/docs",
        "health": "/api/health",
    }


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Global exception handler returning structured error response."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected server error occurred.",
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )
