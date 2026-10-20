"""Central API routing for RevAI."""
from fastapi import APIRouter, File, UploadFile, HTTPException, status

try:
    from backend.app.core.config import settings
    from backend.app.models.schemas import (
        HealthResponse,
        PDFUploadResponse,
        RevisionGenerateRequest,
        RevisionGenerateResponse,
        QuestionItem,
        TestSubmissionRequest,
        TestSubmissionResponse,
        FlashcardGenerateRequest,
        FlashcardGenerateResponse,
    )
    from backend.app.services.pdf_service import extract_pdf_data, PDFProcessingError
    from backend.app.services.ai_service import (
        generate_revision_questions,
        AIServiceError,
        AIServiceConfigurationError
    )
    from backend.app.services.scoring_service import (
        create_test_token,
        verify_test_token,
        evaluate_test_submission,
        ScoringError
    )
    from backend.app.services.flashcard_service import generate_revision_flashcards
except ImportError:  # pragma: no cover
    from app.core.config import settings
    from app.models.schemas import (
        HealthResponse,
        PDFUploadResponse,
        RevisionGenerateRequest,
        RevisionGenerateResponse,
        QuestionItem,
        TestSubmissionRequest,
        TestSubmissionResponse,
        FlashcardGenerateRequest,
        FlashcardGenerateResponse,
    )
    from app.services.pdf_service import extract_pdf_data, PDFProcessingError
    from app.services.ai_service import (
        generate_revision_questions,
        AIServiceError,
        AIServiceConfigurationError
    )
    from app.services.scoring_service import (
        create_test_token,
        verify_test_token,
        evaluate_test_submission,
        ScoringError
    )
    from app.services.flashcard_service import generate_revision_flashcards


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


@api_router.post(
    "/revision/generate",
    response_model=RevisionGenerateResponse,
    tags=["Revision Generation"],
    summary="Generate AI Revision Test",
    description="Generates high-yield multiple-choice questions from extracted study content using Gemini AI."
)
async def generate_revision_test(request: RevisionGenerateRequest) -> RevisionGenerateResponse:
    """Generate structured revision questions based on extracted PDF text and time available."""
    clean_text = request.extracted_text.strip()
    if not clean_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extracted study material text cannot be empty."
        )

    if request.time_remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Time remaining must be greater than 0 minutes."
        )

    if request.question_count <= 0 or request.question_count > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question count must be between 1 and 50 questions."
        )

    try:
        gen_result = await generate_revision_questions(
            extracted_text=clean_text,
            time_remaining=request.time_remaining,
            question_count=request.question_count
        )
        if isinstance(gen_result, dict):
            raw_questions = gen_result.get("questions", [])
            provider = gen_result.get("provider", "gemini")
            model = gen_result.get("model", settings.AI_MODEL)
        else:
            raw_questions = gen_result
            provider = "gemini"
            model = settings.AI_MODEL

        questions = [QuestionItem(**q) for q in raw_questions]
        test_token = create_test_token(questions)

        return RevisionGenerateResponse(
            success=True,
            provider=provider,
            model=model,
            time_remaining=request.time_remaining,
            question_count=len(questions),
            questions=questions,
            test_token=test_token
        )
    except AIServiceConfigurationError as cfg_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=cfg_err.message
        ) from cfg_err
    except AIServiceError as ai_err:
        raise HTTPException(
            status_code=ai_err.status_code,
            detail=ai_err.message
        ) from ai_err
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="We couldn't generate your revision test right now. Please try again."
        ) from exc


@api_router.post(
    "/revision/submit",
    response_model=TestSubmissionResponse,
    tags=["Test Evaluation"],
    summary="Submit and Score Revision Test",
    description="Submits user answers for objective grading against signed session token or authoritative questions."
)
async def submit_revision_test(submission: TestSubmissionRequest) -> TestSubmissionResponse:
    """Grade submitted test answers deterministically and return score analysis and explanations."""
    authoritative_questions = []

    # Priority 1: Verify and decode from signed test token
    if submission.test_token:
        try:
            authoritative_questions = verify_test_token(submission.test_token)
        except ScoringError as s_err:
            raise HTTPException(
                status_code=s_err.status_code,
                detail=s_err.message
            ) from s_err
    # Priority 2: Use explicitly provided questions list (with correct answers & explanations)
    elif submission.questions:
        authoritative_questions = [q.model_dump() for q in submission.questions]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission must include a valid test_token or questions list."
        )

    try:
        response = evaluate_test_submission(
            authoritative_questions=authoritative_questions,
            user_answers=submission.user_answers,
            time_spent_seconds=submission.time_spent_seconds
        )
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while scoring your test."
        ) from exc


@api_router.post(
    "/revision/flashcards",
    response_model=FlashcardGenerateResponse,
    tags=["Smart Flashcards"],
    summary="Generate Targeted Revision Flashcards",
    description="Generates smart revision flashcards focused on weak topics and missed questions from the revision test, grounded in source PDF content."
)
async def create_flashcards(request: FlashcardGenerateRequest) -> FlashcardGenerateResponse:
    """Generate revision flashcards prioritizing weak topics and missed questions."""
    source_content = request.extracted_text.strip()
    if not source_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source content cannot be empty. Please provide study material."
        )

    if len(source_content) < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source content is too short to generate meaningful revision flashcards (minimum 30 characters)."
        )

    try:
        result = await generate_revision_flashcards(
            extracted_text=source_content,
            weak_topics=request.weak_topics,
            incorrect_questions=request.incorrect_questions,
            max_cards=request.max_cards or 10,
        )
        cards = result.get("cards", [])
        return FlashcardGenerateResponse(
            success=True,
            provider=result.get("provider", "gemini"),
            model=result.get("model"),
            total_cards=len(cards),
            cards=cards,
        )
    except AIServiceConfigurationError as cfg_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(cfg_err)
        ) from cfg_err
    except AIServiceError as ai_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(ai_err)
        ) from ai_err
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate revision flashcards: {str(exc)}"
        ) from exc


