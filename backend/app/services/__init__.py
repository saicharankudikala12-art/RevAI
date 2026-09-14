"""Service layer modules for PDF processing, AI generation, and scoring."""
try:
    from backend.app.services.pdf_service import (
        extract_pdf_data,
        validate_pdf_content,
        PDFProcessingError,
    )
except ImportError:  # pragma: no cover
    from app.services.pdf_service import (
        extract_pdf_data,
        validate_pdf_content,
        PDFProcessingError,
    )

__all__ = [
    "extract_pdf_data",
    "validate_pdf_content",
    "PDFProcessingError",
]
