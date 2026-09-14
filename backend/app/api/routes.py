"""Central API routing for RevAI."""
from fastapi import APIRouter, File, UploadFile, HTTPException, status

try:
    from backend.app.core.config import settings
    from backend.app.models.schemas import HealthResponse, PDFUploadResponse
    from backend.app.services.pdf_service import extract_pdf_data, PDFProcessingError
except ImportError:  # pragma: no cover
    from app.core.config import settings
    from app.models.schemas import HealthResponse, PDFUploadResponse
    from app.services.pdf_service import extract_pdf_data, PDFProcessingError

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


@api_router.post(
    "/pdf/upload",
    response_model=PDFUploadResponse,
    tags=["PDF Processing"],
    summary="Upload and Process Study PDF",
    description="Accepts a PDF document via multipart/form-data, automatically detects page count, extracts full text, and returns document metrics."
)
async def upload_pdf(file: UploadFile = File(...)) -> PDFUploadResponse:
    """Process uploaded PDF, validate authenticity, count pages, and extract text."""
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file was uploaded."
        )

    clean_filename = file.filename.strip()
    if not clean_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF files are supported."
        )

    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read the uploaded file stream."
        ) from exc

    try:
        result = extract_pdf_data(
            content=content,
            filename=clean_filename,
            max_size_mb=settings.MAX_UPLOAD_SIZE_MB
        )
        return PDFUploadResponse(**result)
    except PDFProcessingError as p_err:
        raise HTTPException(
            status_code=p_err.status_code,
            detail=p_err.message
        ) from p_err
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the PDF document."
        ) from exc
    finally:
        await file.close()
