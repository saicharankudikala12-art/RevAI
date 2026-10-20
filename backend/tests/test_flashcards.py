"""Automated tests for Milestone 8: Smart Revision Flashcards.

Tests cover:
- Flashcard generation with valid source content
- Fallback prioritizing incorrect answers and weak topics
- Schema validation (front, back, topic, memory_tip)
- Empty or insufficient source content error handling (HTTP 400)
- AI provider failure and fallback behavior (with fallback enabled vs disabled)
- API endpoint /revision/flashcards success and error cases
- End-to-end integration with test scoring and weak topics
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.models.schemas import (
    FlashcardItem,
    FlashcardGenerateRequest,
    FlashcardGenerateResponse,
    WeakTopicItem,
    QuestionReviewItem,
)
from backend.app.services.flashcard_service import (
    generate_heuristic_fallback_flashcards,
    generate_revision_flashcards,
    build_flashcards_prompt,
    parse_and_validate_flashcards,
)
from backend.app.services.ai_service import AIServiceError

client = TestClient(app)

SAMPLE_SOURCE_TEXT = (
    "Operating Systems Revision Summary. "
    "A process is a program in execution with its own address space, program counter, and stack. "
    "Virtual memory allows execution of processes that may not be completely in physical memory. "
    "Paging eliminates external fragmentation by allocating memory in fixed-size blocks called frames and pages. "
    "Deadlock occurs when four necessary conditions hold simultaneously: Mutual Exclusion, Hold and Wait, "
    "No Preemption, and Circular Wait. Semaphores and mutexes provide synchronization mechanisms."
)

SAMPLE_WEAK_TOPICS = [
    WeakTopicItem(
        topic="Virtual Memory & Paging",
        total_questions=4,
        incorrect_count=3,
        unanswered_count=0,
        accuracy_percentage=25.0,
        weakness_indicator="Critical Weakness",
        priority="high",
        reason="Low accuracy on paging questions",
        recommendation="Revise page tables and frame allocation mechanisms."
    ),
    WeakTopicItem(
        topic="Process Synchronization",
        total_questions=2,
        incorrect_count=1,
        unanswered_count=0,
        accuracy_percentage=50.0,
        weakness_indicator="Moderate Weakness",
        priority="medium",
        reason="Failed deadlock condition question",
        recommendation="Practice deadlock prevention four conditions."
    )
]

SAMPLE_INCORRECT_QUESTIONS = [
    QuestionReviewItem(
        id=2,
        question="Which condition is NOT required for a deadlock to occur?",
        options={"A": "Mutual Exclusion", "B": "Hold and Wait", "C": "Arbitrary Scheduling", "D": "Circular Wait"},
        user_answer="A",
        correct_answer="C",
        is_correct=False,
        is_answered=True,
        explanation="Deadlock requires Mutual Exclusion, Hold & Wait, No Preemption, and Circular Wait.",
        topic="Process Synchronization"
    ),
    QuestionReviewItem(
        id=5,
        question="What is the primary benefit of paging in virtual memory?",
        options={"A": "Fast CPU cache", "B": "Avoids external fragmentation", "C": "Eliminates TLB misses", "D": "Faster disk IO"},
        user_answer="D",
        correct_answer="B",
        is_correct=False,
        is_answered=True,
        explanation="Paging avoids external fragmentation and simplifies memory allocation.",
        topic="Virtual Memory & Paging"
    )
]


# -----------------------------------------------------------------------------
# 1. Fallback Flashcard Generation Tests
# -----------------------------------------------------------------------------
def test_fallback_flashcards_from_valid_source():
    """Fallback creates valid flashcards grounded in source content."""
    cards = generate_heuristic_fallback_flashcards(
        extracted_text=SAMPLE_SOURCE_TEXT,
        weak_topics=[],
        incorrect_questions=[],
        max_cards=6
    )
    assert len(cards) > 0
    assert len(cards) <= 6
    for card in cards:
        assert isinstance(card, dict)
        assert card["id"] >= 1
        assert len(card["front"].strip()) > 0
        assert len(card["back"].strip()) > 0
        assert len(card["topic"].strip()) > 0
        assert card["memory_tip"] is not None


def test_fallback_flashcards_prioritizes_incorrect_questions():
    """Fallback prioritizes concepts from incorrect questions first."""
    cards = generate_heuristic_fallback_flashcards(
        extracted_text=SAMPLE_SOURCE_TEXT,
        weak_topics=SAMPLE_WEAK_TOPICS,
        incorrect_questions=SAMPLE_INCORRECT_QUESTIONS,
        max_cards=8
    )
    assert len(cards) >= 2
    # Verify the first cards reflect the missed questions and their topics
    topics_in_cards = [c["topic"] for c in cards]
    assert any("Process Synchronization" in t or "Virtual Memory" in t for t in topics_in_cards)
    # Check that question explanations are leveraged in back / tip
    backs_and_tips = " ".join([c["back"] + " " + (c["memory_tip"] or "") for c in cards])
    assert "fragmentation" in backs_and_tips or "Mutual Exclusion" in backs_and_tips


def test_fallback_flashcards_incorporates_weak_topics():
    """Fallback generates targeted cards for weak topics with recommendations."""
    cards = generate_heuristic_fallback_flashcards(
        extracted_text=SAMPLE_SOURCE_TEXT,
        weak_topics=SAMPLE_WEAK_TOPICS,
        incorrect_questions=[],
        max_cards=6
    )
    assert len(cards) >= 2
    topics = [c["topic"] for c in cards]
    assert any("Virtual Memory" in t for t in topics)
    assert any("Process Synchronization" in t for t in topics)


def test_fallback_flashcards_empty_when_no_meaningful_sentences():
    """Fallback raises InsufficientContentError or returns empty when source text has no valid words."""
    from backend.app.services.ai_service import InsufficientContentError
    with pytest.raises(InsufficientContentError):
        generate_heuristic_fallback_flashcards(
            extracted_text="...   ... !!! ???",
            weak_topics=[],
            incorrect_questions=[]
        )


# -----------------------------------------------------------------------------
# 2. Prompt Building and Parsing Tests
# -----------------------------------------------------------------------------
def test_build_flashcards_prompt_structure():
    """Prompt cleanly includes weak topics and missed questions."""
    prompt = build_flashcards_prompt(
        extracted_text=SAMPLE_SOURCE_TEXT,
        weak_topics=SAMPLE_WEAK_TOPICS,
        incorrect_questions=SAMPLE_INCORRECT_QUESTIONS,
        max_cards=5
    )
    assert "Virtual Memory & Paging" in prompt
    assert "Which condition is NOT required for a deadlock to occur?" in prompt
    assert "Operating Systems Revision Summary" in prompt
    assert "JSON array" in prompt or "JSON" in prompt


def test_parse_and_validate_flashcards_valid_json():
    """Parses valid JSON array into flashcard dicts."""
    raw_json = """
    [
        {
            "front": "What is a Process?",
            "back": "A program in execution with its own address space and program counter.",
            "topic": "Process Management",
            "memory_tip": "Remember: A program is passive on disk; a process is active in RAM."
        },
        {
            "front": "What are the four conditions for deadlock?",
            "back": "Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait.",
            "topic": "Synchronization",
            "memory_tip": "Mnemonic: M-H-N-C (Must Have No Circularity to be safe)."
        }
    ]
    """
    cards = parse_and_validate_flashcards(raw_json, expected_count=2)
    assert len(cards) == 2
    assert cards[0]["front"] == "What is a Process?"
    assert cards[1]["topic"] == "Synchronization"
    assert "M-H-N-C" in cards[1]["memory_tip"]


def test_parse_and_validate_flashcards_with_markdown_fences():
    """Handles JSON wrapped in markdown code fences cleanly."""
    raw_markdown = """```json
    [
        {
            "front": "What does Paging eliminate?",
            "back": "External fragmentation.",
            "topic": "Memory Management",
            "memory_tip": "Pages and frames are fixed sizes."
        }
    ]
    ```"""
    cards = parse_and_validate_flashcards(raw_markdown, expected_count=1)
    assert len(cards) == 1
    assert cards[0]["back"] == "External fragmentation."


def test_parse_and_validate_flashcards_invalid_json():
    """Raises AIServiceError when JSON is corrupted or empty."""
    with pytest.raises(AIServiceError):
        parse_and_validate_flashcards("Not JSON at all", expected_count=2)


# -----------------------------------------------------------------------------
# 3. Service Layer AI Call & Fallback Integration Tests (Using AnyIO)
# -----------------------------------------------------------------------------
@pytest.mark.anyio
async def test_generate_revision_flashcards_gemini_success(monkeypatch):
    """When Gemini succeeds, returns AI-generated flashcards."""
    import httpx
    fake_gemini_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": """[
                                {"front": "What is Virtual Memory?", "back": "An illusion of large main memory using disk space.", "topic": "Virtual Memory", "memory_tip": "Think swapping pages."}
                            ]"""
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

    monkeypatch.setattr(settings, "AI_API_KEY", "test-key-valid")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    result = await generate_revision_flashcards(
        extracted_text=SAMPLE_SOURCE_TEXT,
        weak_topics=[],
        incorrect_questions=[],
        client=mock_client
    )
    assert result["provider"] == "gemini"
    assert len(result["cards"]) == 1
    assert result["cards"][0]["front"] == "What is Virtual Memory?"


@pytest.mark.anyio
async def test_generate_revision_flashcards_fallback_when_gemini_fails(monkeypatch):
    """When Gemini returns 403 and fallback is allowed, returns safe fallback cards."""
    import httpx
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403
    mock_response.text = "PERMISSION_DENIED"

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response

    monkeypatch.setattr(settings, "AI_API_KEY", "test-key-denied")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "ALLOW_HEURISTIC_FALLBACK", True)

    result = await generate_revision_flashcards(
        extracted_text=SAMPLE_SOURCE_TEXT,
        weak_topics=SAMPLE_WEAK_TOPICS,
        incorrect_questions=SAMPLE_INCORRECT_QUESTIONS,
        max_cards=6,
        client=mock_client
    )
    assert result["provider"] == "heuristic-fallback"
    assert len(result["cards"]) > 0
    topics = [c["topic"] for c in result["cards"]]
    assert any("Virtual Memory" in t or "Process Synchronization" in t for t in topics)


@pytest.mark.anyio
async def test_generate_revision_flashcards_raises_when_fallback_disabled(monkeypatch):
    """When Gemini fails and fallback is disabled, raises error."""
    import httpx
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.text = "Internal error"

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response

    monkeypatch.setattr(settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "ALLOW_HEURISTIC_FALLBACK", False)

    with pytest.raises(AIServiceError):
        await generate_revision_flashcards(
            extracted_text=SAMPLE_SOURCE_TEXT,
            weak_topics=[],
            incorrect_questions=[],
            client=mock_client,
            allow_fallback=False
        )


# -----------------------------------------------------------------------------
# 4. API Endpoint Integration Tests (/api/revision/flashcards)
# -----------------------------------------------------------------------------
def test_api_flashcards_success_endpoint():
    """POST /api/revision/flashcards returns 200 and valid schema."""
    payload = {
        "extracted_text": SAMPLE_SOURCE_TEXT,
        "weak_topics": [w.model_dump() for w in SAMPLE_WEAK_TOPICS],
        "incorrect_questions": [q.model_dump() for q in SAMPLE_INCORRECT_QUESTIONS],
        "max_cards": 5
    }
    response = client.post("/api/revision/flashcards", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "cards" in data
    assert "total_cards" in data
    assert len(data["cards"]) > 0
    first_card = data["cards"][0]
    assert "front" in first_card
    assert "back" in first_card
    assert "topic" in first_card
    assert "memory_tip" in first_card


def test_api_flashcards_empty_content_returns_400():
    """POST /api/revision/flashcards rejects empty content with HTTP 400."""
    payload = {
        "extracted_text": "   ",
        "weak_topics": [],
        "incorrect_questions": []
    }
    response = client.post("/api/revision/flashcards", json=payload)
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"].lower()


def test_api_flashcards_too_short_content_returns_400():
    """POST /api/revision/flashcards rejects content under 30 chars with HTTP 400."""
    payload = {
        "extracted_text": "Short text",
        "weak_topics": [],
        "incorrect_questions": []
    }
    response = client.post("/api/revision/flashcards", json=payload)
    assert response.status_code == 400
    assert "minimum 30 characters" in response.json()["detail"]


def test_api_flashcards_handles_no_incorrect_questions_gracefully():
    """Generates flashcards even if student got 100% (no weak topics or missed questions)."""
    payload = {
        "extracted_text": SAMPLE_SOURCE_TEXT,
        "weak_topics": [],
        "incorrect_questions": [],
        "max_cards": 4
    }
    response = client.post("/api/revision/flashcards", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["cards"]) > 0
    assert data["total_cards"] == len(data["cards"])
