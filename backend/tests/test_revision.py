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


