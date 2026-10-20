"""RevAI Application Entry Point."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

try:
    from backend.app.core.config import settings, FRONTEND_DIR
    from backend.app.api.routes import api_router
except ImportError:  # pragma: no cover
    from app.core.config import settings, FRONTEND_DIR
    from app.api.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown routines."""
    # Enforce security validation in production
    settings.validate_production_security()
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

# Register API routes under /api FIRST to guarantee static routes cannot shadow API endpoints
app.include_router(api_router, prefix="/api")

# Serve frontend directory if present (Unified Deployment)
if FRONTEND_DIR.is_dir() and (FRONTEND_DIR / "index.html").is_file():
    # Mount css and js subdirectories
    css_dir = FRONTEND_DIR / "css"
    js_dir = FRONTEND_DIR / "js"
    if css_dir.is_dir():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    if js_dir.is_dir():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")

    @app.get("/", tags=["Frontend"], summary="Serve RevAI Web App")
    async def serve_frontend_index():
        """Serve the RevAI frontend Single Page Application."""
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
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
