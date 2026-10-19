"""Tests for the revision question generation endpoint."""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings

client = TestClient(app)


def test_revision_generate_missing_api_key(monkeypatch):
    """When AI_API_KEY is empty, endpoint returns 503 with configuration message."""
    monkeypatch.setattr(settings, "AI_API_KEY", "")

    payload = {
        "extracted_text": "Photosynthesis is the process by which green plants use sunlight to synthesize nutrients.",
        "time_remaining": 60,
        "question_count": 5
    }

    response = client.post("/api/revision/generate", json=payload)
    assert response.status_code == 503
    data = response.json()
    assert "AI generation is not configured yet" in data["detail"]


def test_revision_generate_empty_text():
    """Empty extracted_text returns 400 bad request."""
    payload = {
        "extracted_text": "   ",
        "time_remaining": 60,
        "question_count": 5
    }
    response = client.post("/api/revision/generate", json=payload)
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"].lower()


def test_revision_generate_invalid_time():
    """Negative or zero time returns 400 or 422."""
    payload = {
        "extracted_text": "Valid study text.",
        "time_remaining": 0,
        "question_count": 5
    }
    response = client.post("/api/revision/generate", json=payload)
    assert response.status_code in [400, 422]


def test_revision_generate_invalid_question_count():
    """Question count above 50 returns 400 or 422."""
    payload = {
        "extracted_text": "Valid study text.",
        "time_remaining": 60,
        "question_count": 55
    }
    response = client.post("/api/revision/generate", json=payload)
    assert response.status_code in [400, 422]


def test_revision_generate_successful_mocked(monkeypatch):
    """Valid request returns 200 and structured questions."""
    monkeypatch.setattr(settings, "AI_API_KEY", "test-key-mocked")

    mock_questions = [
        {
            "id": 1,
            "question": "What is the primary byproduct of photosynthesis?",
            "options": {
                "A": "Carbon dioxide",
                "B": "Oxygen",
                "C": "Nitrogen",
                "D": "Hydrogen"
            },
            "correct_answer": "B",
            "explanation": "Plants release oxygen during the light-dependent reactions."
        },
        {
            "id": 2,
            "question": "Which organelle conducts photosynthesis in plant cells?",
            "options": {
                "A": "Mitochondria",
                "B": "Nucleus",
                "C": "Chloroplast",
                "D": "Ribosome"
            },
            "correct_answer": "C",
            "explanation": "Chloroplasts contain chlorophyll and carry out photosynthesis."
        }
    ]

    with patch("backend.app.api.routes.generate_revision_questions", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_questions

        payload = {
            "extracted_text": "Photosynthesis occurs in chloroplasts. It produces oxygen.",
            "time_remaining": 30,
            "question_count": 2
        }

        response = client.post("/api/revision/generate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["provider"] == "gemini"
        assert data["model"] is not None
        assert data["time_remaining"] == 30
        assert data["question_count"] == 2
        assert len(data["questions"]) == 2
        assert data["questions"][0]["question"] == "What is the primary byproduct of photosynthesis?"
        assert data["questions"][0]["correct_answer"] == "B"
        assert data["questions"][0]["options"]["B"] == "Oxygen"


def test_revision_generate_gemini_failure_handling(monkeypatch):
    """When Gemini fails, endpoint returns friendly 502 error."""
    monkeypatch.setattr(settings, "AI_API_KEY", "test-key-mocked")

    from backend.app.services.ai_service import AIServiceError

    with patch("backend.app.api.routes.generate_revision_questions", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = AIServiceError("We couldn't generate your revision test right now. Please try again.", status_code=502)

        payload = {
            "extracted_text": "Valid content.",
            "time_remaining": 45,
            "question_count": 5
        }

        response = client.post("/api/revision/generate", json=payload)
        assert response.status_code == 502
        assert "We couldn't generate your revision test right now" in response.json()["detail"]


def test_ai_service_prompt_builder():
    """Prompt builder contains study text and time/question requirements."""
    from backend.app.services.ai_service import build_revision_prompt

    prompt = build_revision_prompt("Mitochondria is the powerhouse of the cell.", 45, 10)
    assert "Mitochondria is the powerhouse" in prompt
    assert "45 minutes" in prompt
    assert "10" in prompt
    assert "CRITICAL RULES" in prompt


def test_ai_service_parse_markdown_json():
    """Parser cleanly strips ```json code fences and normalizes questions."""
    from backend.app.services.ai_service import parse_and_validate_questions

    raw_output = """```json
    {
      "questions": [
        {
          "id": 1,
          "question": "What is the cell's energy currency?",
          "options": {
            "A": "DNA",
            "B": "RNA",
            "C": "ATP",
            "D": "Glucose"
          },
          "correct_answer": "Option C",
          "explanation": "ATP stores chemical energy."
        }
      ]
    }
    ```"""

    questions = parse_and_validate_questions(raw_output, expected_count=1)
    assert len(questions) == 1
    assert questions[0]["id"] == 1
    assert questions[0]["correct_answer"] == "C"
    assert questions[0]["options"]["C"] == "ATP"
    assert "ATP stores" in questions[0]["explanation"]


def test_ai_service_parse_list_options():
    """Parser converts array-based options to A/B/C/D dict."""
    from backend.app.services.ai_service import parse_and_validate_questions

    raw_output = """[
      {
        "question": "What organelle produces ATP?",
        "options": ["Ribosome", "Mitochondria", "Golgi", "Nucleus"],
        "correct_answer": "B",
        "explanation": "Mitochondria generates ATP."
      }
    ]"""

    questions = parse_and_validate_questions(raw_output, expected_count=1)
    assert len(questions) == 1
    assert questions[0]["options"]["A"] == "Ribosome"
    assert questions[0]["options"]["B"] == "Mitochondria"
    assert questions[0]["correct_answer"] == "B"


def test_ai_service_insufficient_content():
    """Text with fewer than 5 words or 30 characters raises InsufficientContentError."""
    import pytest
    from backend.app.services.ai_service import InsufficientContentError, generate_revision_questions

    with pytest.raises(InsufficientContentError):
        import asyncio
        asyncio.run(generate_revision_questions(
            extracted_text="Too short",
            time_remaining=30,
            question_count=5
        ))


def test_ai_service_heuristic_fallback():
    """Fallback generator creates grounded questions derived strictly from the study text and distinct explanation."""
    from backend.app.services.ai_service import generate_heuristic_fallback_questions

    sample_text = (
        "Cellular respiration is a metabolic pathway that breaks down glucose. "
        "Glycolysis takes place in the cytoplasm of cells. "
        "The Krebs cycle occurs inside the mitochondrial matrix. "
        "Oxidative phosphorylation produces the majority of ATP."
    )
    questions = generate_heuristic_fallback_questions(sample_text, question_count=3)
    assert len(questions) == 3
    for q in questions:
        assert q["id"] >= 1
        assert len(q["options"]) == 4
        assert q["correct_answer"] == "A"
        assert "[Fallback Review]" in q["explanation"]


@pytest.mark.anyio
async def test_ai_service_gemini_success_mocked(monkeypatch):
    """Direct generate_revision_questions call with mocked httpx client returns structured Gemini questions."""
    from unittest.mock import MagicMock
    import httpx
    from backend.app.services.ai_service import generate_revision_questions

    monkeypatch.setattr(settings, "AI_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    sample_text = (
        "The mitochondria is known as the powerhouse of the cell. "
        "It generates most of the chemical energy needed to power biochemical reactions."
    )

    fake_gemini_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": """{
                                "questions": [
                                    {
                                        "id": 1,
                                        "question": "What is the primary function of mitochondria?",
                                        "options": {
                                            "A": "Produces chemical energy",
                                            "B": "Synthesizes DNA only",
                                            "C": "Degrades proteins",
                                            "D": "Provides cell motility"
                                        },
                                        "correct_answer": "A",
                                        "explanation": "Mitochondria produce cellular ATP energy."
                                    }
                                ]
                            }"""
                        }
                    ]
                }
            }
        ]
    }

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = fake_gemini_json

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response

    result = await generate_revision_questions(
        extracted_text=sample_text,
        time_remaining=30,
        question_count=1,
        client=mock_client
    )

    assert result["provider"] == "gemini"
    assert len(result["questions"]) == 1
    assert result["questions"][0]["question"] == "What is the primary function of mitochondria?"
    assert result["questions"][0]["options"]["A"] == "Produces chemical energy"


@pytest.mark.anyio
async def test_ai_service_gemini_rate_limit_429(monkeypatch):
    """When Gemini returns 429, AIServiceError with status_code 429 is raised."""
    from unittest.mock import MagicMock
    import httpx
    from backend.app.services.ai_service import generate_revision_questions, AIServiceError

    monkeypatch.setattr(settings, "AI_API_KEY", "test-api-key")

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 429
    mock_response.text = "RESOURCE_EXHAUSTED: Rate limit exceeded"

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response

    sample_text = "Photosynthesis converts solar light energy into chemical energy."
    with pytest.raises(AIServiceError) as exc_info:
        await generate_revision_questions(
            extracted_text=sample_text,
            time_remaining=30,
            question_count=2,
            client=mock_client,
            allow_fallback=False
        )
    assert exc_info.value.status_code == 429


@pytest.mark.anyio
async def test_ai_service_gemini_timeout_with_fallback(monkeypatch):
    """When Gemini times out and fallback is enabled, heuristic fallback questions are returned with provider 'heuristic-fallback'."""
    import httpx
    from backend.app.services.ai_service import generate_revision_questions

    monkeypatch.setattr(settings, "AI_API_KEY", "test-api-key")

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.TimeoutException("Connection timed out")

    sample_text = (
        "Enzymes are biological catalysts that speed up chemical reactions. "
        "Substrates bind to the enzyme active site to form products."
    )
    result = await generate_revision_questions(
        extracted_text=sample_text,
        time_remaining=20,
        question_count=2,
        client=mock_client,
        allow_fallback=True
    )

    assert result["provider"] == "heuristic-fallback"
    assert result["model"] is None
    assert len(result["questions"]) == 2
    assert "[Fallback Review]" in result["questions"][0]["explanation"]
