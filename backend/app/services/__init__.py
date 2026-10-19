try:
    from backend.app.services.pdf_service import (
        extract_pdf_data,
        validate_pdf_content,
        PDFProcessingError,
    )
    from backend.app.services.scoring_service import (
        create_test_token,
        verify_test_token,
        evaluate_test_submission,
        ScoringError,
    )
except ImportError:  # pragma: no cover
    from app.services.pdf_service import (
        extract_pdf_data,
        validate_pdf_content,
        PDFProcessingError,
    )
    from app.services.scoring_service import (
        create_test_token,
        verify_test_token,
        evaluate_test_submission,
        ScoringError,
    )

__all__ = [
    "extract_pdf_data",
    "validate_pdf_content",
    "PDFProcessingError",
    "create_test_token",
    "verify_test_token",
    "evaluate_test_submission",
    "ScoringError",
]

