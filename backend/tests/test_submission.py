"""Automated tests for Milestone 5 test submission, objective scoring, and answer review."""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.models.schemas import QuestionItem
from backend.app.services.scoring_service import (
    create_test_token,
    verify_test_token,
    evaluate_test_submission,
    calculate_performance_summary,
    ScoringError,
)

client = TestClient(app)

SAMPLE_QUESTIONS = [
    {
        "id": 1,
        "question": "What is the primary organelle responsible for ATP production?",
        "options": {
            "A": "Ribosome",
            "B": "Mitochondria",
            "C": "Golgi apparatus",
            "D": "Endoplasmic reticulum"
        },
        "correct_answer": "B",
        "explanation": "Mitochondria generate cellular energy through oxidative phosphorylation."
    },
    {
        "id": 2,
        "question": "Which molecule carries genetic information from DNA to the ribosome?",
        "options": {
            "A": "tRNA",
            "B": "rRNA",
            "C": "mRNA",
            "D": "miRNA"
        },
        "correct_answer": "C",
        "explanation": "mRNA transcribes the genetic code and conveys it to ribosomes for translation."
    },
    {
        "id": 3,
        "question": "During which phase of cell division do sister chromatids separate?",
        "options": {
            "A": "Prophase",
            "B": "Metaphase",
            "C": "Anaphase",
            "D": "Telophase"
        },
        "correct_answer": "C",
        "explanation": "In anaphase, the sister chromatids are pulled apart toward opposite poles."
    },
    {
        "id": 4,
        "question": "What is the main byproduct of oxygenic photosynthesis?",
        "options": {
            "A": "Carbon dioxide",
            "B": "Oxygen",
            "C": "Methane",
            "D": "Nitrogen"
        },
        "correct_answer": "B",
        "explanation": "Water splitting during the light reactions releases molecular oxygen."
    }
]


# -----------------------------------------------------------------------------
# Scoring Service Unit Tests
# -----------------------------------------------------------------------------
def test_scoring_all_correct():
    """All answers correct scores 100.0%, 4 correct, 0 incorrect, 0 unanswered."""
    user_answers = {"1": "B", "2": "C", "3": "C", "4": "B"}
    res = evaluate_test_submission(SAMPLE_QUESTIONS, user_answers)

    assert res.total_questions == 4
    assert res.correct_count == 4
    assert res.incorrect_count == 0
    assert res.unanswered_count == 0
    assert res.score_percentage == 100.0
    assert res.performance_rating == "Excellent"
    assert len(res.questions_review) == 4
    assert all(q.is_correct for q in res.questions_review)
    assert all(q.is_answered for q in res.questions_review)


def test_scoring_all_incorrect():
    """All answers incorrect scores 0.0%, 0 correct, 4 incorrect, 0 unanswered."""
    user_answers = {"1": "A", "2": "A", "3": "A", "4": "A"}
    res = evaluate_test_submission(SAMPLE_QUESTIONS, user_answers)

    assert res.total_questions == 4
    assert res.correct_count == 0
    assert res.incorrect_count == 4
    assert res.unanswered_count == 0
    assert res.score_percentage == 0.0
    assert res.performance_rating == "Needs Review"
    assert not any(q.is_correct for q in res.questions_review)
    assert all(q.is_answered for q in res.questions_review)


def test_scoring_partially_answered():
    """Partially answered test: 2 answered (1 correct, 1 incorrect), 2 unanswered."""
    user_answers = {"1": "B", "2": "A"}  # Q1 correct (B), Q2 incorrect (A), Q3 & Q4 omitted
    res = evaluate_test_submission(SAMPLE_QUESTIONS, user_answers)

    assert res.total_questions == 4
    assert res.correct_count == 1
    assert res.incorrect_count == 1
    assert res.unanswered_count == 2
    assert res.score_percentage == 25.0
    assert res.performance_rating == "Needs Review"

    review_map = {q.id: q for q in res.questions_review}
    assert review_map[1].is_correct is True
    assert review_map[1].is_answered is True
    assert review_map[1].user_answer == "B"

    assert review_map[2].is_correct is False
    assert review_map[2].is_answered is True
    assert review_map[2].user_answer == "A"

    assert review_map[3].is_correct is False
    assert review_map[3].is_answered is False
    assert review_map[3].user_answer is None

    assert review_map[4].is_correct is False
    assert review_map[4].is_answered is False
    assert review_map[4].user_answer is None


def test_scoring_entirely_unanswered():
    """Entirely unanswered test scores 0.0%, 0 correct, 0 incorrect, 4 unanswered."""
    user_answers = {}
    res = evaluate_test_submission(SAMPLE_QUESTIONS, user_answers)

    assert res.total_questions == 4
    assert res.correct_count == 0
    assert res.incorrect_count == 0
    assert res.unanswered_count == 4
    assert res.score_percentage == 0.0
    assert "4 question(s) were left unanswered" in res.performance_summary
    assert all(not q.is_answered for q in res.questions_review)
    assert all(not q.is_correct for q in res.questions_review)


def test_scoring_zero_questions_edge_case():
    """Zero questions input does not throw division-by-zero and yields safe 0.0%."""
    res = evaluate_test_submission([], {})
    assert res.total_questions == 0
    assert res.correct_count == 0
    assert res.score_percentage == 0.0
    assert res.performance_rating == "N/A"
    assert res.questions_review == []


def test_scoring_case_insensitivity_and_whitespace():
    """Answers submitted with lowercase or surrounding whitespace are normalized."""
    user_answers = {" 1 ": " b ", "2": "c", "3": " c "}
    res = evaluate_test_submission(SAMPLE_QUESTIONS, user_answers)
    assert res.correct_count == 3
    assert res.unanswered_count == 1


# -----------------------------------------------------------------------------
# Token Security & Verification Unit Tests
# -----------------------------------------------------------------------------
def test_token_creation_and_verification():
    """Test token round-trip verifies questions, correct answers, and explanations."""
    token = create_test_token(SAMPLE_QUESTIONS)
    assert isinstance(token, str)
    assert "." in token

    decoded = verify_test_token(token)
    assert len(decoded) == len(SAMPLE_QUESTIONS)
    assert decoded[0]["question"] == SAMPLE_QUESTIONS[0]["question"]
    assert decoded[0]["correct_answer"] == SAMPLE_QUESTIONS[0]["correct_answer"]


def test_token_tampering_rejected():
    """Tampering with token payload or signature raises ScoringError with status 400."""
    token = create_test_token(SAMPLE_QUESTIONS)
    payload_b64, signature = token.split(".")

    # Tamper with signature
    tampered_sig = signature[:-4] + "abcd"
    with pytest.raises(ScoringError) as exc:
        verify_test_token(f"{payload_b64}.{tampered_sig}")
    assert exc.value.status_code == 400
    assert "Tampered or invalid" in str(exc.value.message)


def test_token_malformed_rejected():
    """Malformed token strings raise ScoringError."""
    with pytest.raises(ScoringError):
        verify_test_token("not-a-valid-token")
    with pytest.raises(ScoringError):
        verify_test_token("")


# -----------------------------------------------------------------------------
# API Endpoint Integration Tests: POST /api/revision/submit
# -----------------------------------------------------------------------------
def test_api_submit_with_token_success():
    """API successfully grades answers using valid test_token."""
    token = create_test_token(SAMPLE_QUESTIONS)

    payload = {
        "test_token": token,
        "user_answers": {"1": "B", "2": "C", "3": "A", "4": "B"},
        "time_spent_seconds": 145
    }

    response = client.post("/api/revision/submit", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["total_questions"] == 4
    assert data["correct_count"] == 3  # Q1 (B), Q2 (C), Q4 (B) correct; Q3 incorrect (A vs C)
    assert data["incorrect_count"] == 1
    assert data["unanswered_count"] == 0
    assert data["score_percentage"] == 75.0
    assert data["time_spent_seconds"] == 145
    assert len(data["questions_review"]) == 4

    # Check that correct answers and explanations are returned in the review
    assert data["questions_review"][0]["correct_answer"] == "B"
    assert data["questions_review"][0]["is_correct"] is True
    assert "oxidative phosphorylation" in data["questions_review"][0]["explanation"]


def test_api_submit_with_explicit_questions():
    """API successfully grades when questions are submitted directly."""
    payload = {
        "questions": SAMPLE_QUESTIONS,
        "user_answers": {"1": "B", "2": "C"},
        "time_spent_seconds": 60
    }

    response = client.post("/api/revision/submit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_questions"] == 4
    assert data["correct_count"] == 2
    assert data["unanswered_count"] == 2


def test_api_submit_missing_token_and_questions():
    """Submitting neither test_token nor questions returns 400 Bad Request."""
    payload = {
        "user_answers": {"1": "A"}
    }
    response = client.post("/api/revision/submit", json=payload)
    assert response.status_code == 400
    assert "must include a valid test_token or questions" in response.json()["detail"]


def test_api_submit_tampered_token():
    """Submitting tampered token returns 400 Bad Request."""
    payload = {
        "test_token": "tampered_payload.fake_signature",
        "user_answers": {"1": "A"}
    }
    response = client.post("/api/revision/submit", json=payload)
    assert response.status_code == 400
    assert "Tampered or invalid" in response.json()["detail"]


def test_api_generate_includes_test_token(monkeypatch):
    """POST /api/revision/generate returns test_token alongside questions."""
    monkeypatch.setattr(settings, "AI_API_KEY", "mock-test-key")

    with patch("backend.app.api.routes.generate_revision_questions", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = SAMPLE_QUESTIONS

        payload = {
            "extracted_text": "Sample text for test token generation testing.",
            "time_remaining": 60,
            "question_count": 4
        }

        response = client.post("/api/revision/generate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "test_token" in data
        assert data["test_token"] is not None
        assert len(data["test_token"]) > 20

        # Validate that the token can be decoded by verify_test_token
        decoded = verify_test_token(data["test_token"])
        assert len(decoded) == 4
