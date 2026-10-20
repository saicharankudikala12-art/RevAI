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
    from backend.app.services.topic_service import (
        extract_topic_from_question,
        analyze_weak_topics,
    )
    from backend.app.services.flashcard_service import (
        generate_revision_flashcards,
        generate_heuristic_fallback_flashcards,
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
    from app.services.topic_service import (
        extract_topic_from_question,
        analyze_weak_topics,
    )
    from app.services.flashcard_service import (
        generate_revision_flashcards,
        generate_heuristic_fallback_flashcards,
    )

__all__ = [
    "extract_pdf_data",
    "validate_pdf_content",
    "PDFProcessingError",
    "create_test_token",
    "verify_test_token",
    "evaluate_test_submission",
    "ScoringError",
    "extract_topic_from_question",
    "analyze_weak_topics",
    "generate_revision_flashcards",
    "generate_heuristic_fallback_flashcards",
]

