"""Automated tests for Milestone 7 weak-topic analysis, topic tagging, and prioritization."""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.schemas import QuestionItem, QuestionReviewItem
from backend.app.services.topic_service import (
    extract_topic_from_question,
    analyze_weak_topics,
)
from backend.app.services.scoring_service import evaluate_test_submission

client = TestClient(app)


# -----------------------------------------------------------------------------
# Topic Extraction Tests
# -----------------------------------------------------------------------------
def test_topic_extraction_with_explicit_topic():
    """Explicit topic tag takes precedence and is cleaned and title-cased."""
    topic = extract_topic_from_question(
        question="What is the function of ribosome?",
        explanation="Ribosomes synthesize proteins.",
        explicit_topic="1. Protein synthesis"
    )
    assert topic == "Protein Synthesis"


def test_topic_extraction_from_chapter_heading_pattern():
    """Extracts topic from Chapter/Topic/Section prefixes."""
    topic = extract_topic_from_question(
        question="According to Chapter 3: Operating System Paging, what happens during page fault?",
        explanation="Page fault triggers an interrupt."
    )
    assert "Operating System Paging" in topic


def test_topic_extraction_from_quoted_material():
    """Extracts topic from quoted study concept strings."""
    topic = extract_topic_from_question(
        question="According to the study material: 'RevAI Study Chapter 1: Memory Management Revision...', which statement is true?",
        explanation="[Fallback Review] Option A is directly quoted."
    )
    assert "Memory Management" in topic


def test_topic_extraction_from_significant_keywords():
    """Fallback extracts significant keywords when no structured pattern is present."""
    topic = extract_topic_from_question(
        question="Which organelle conducts photosynthesis in eukaryotic plant cells?",
        explanation="Chloroplasts contain chlorophyll."
    )
    assert "Photosynthesis" in topic or "Chloroplasts" in topic


def test_topic_extraction_empty_fallback():
    """Completely empty input safely returns General Core Concept."""
    topic = extract_topic_from_question("", "")
    assert topic == "General Core Concept"


# -----------------------------------------------------------------------------
# Weak-Topic Analysis Unit Tests
# -----------------------------------------------------------------------------
def test_analyze_weak_topics_perfect_score():
    """When all questions are correct, weak_topics list is empty."""
    reviews = [
        QuestionReviewItem(
            id=1,
            question="Q1",
            options={"A": "1", "B": "2", "C": "3", "D": "4"},
            user_answer="A",
            correct_answer="A",
            is_correct=True,
            is_answered=True,
            explanation="Exp 1",
            topic="Memory Management"
        ),
        QuestionReviewItem(
            id=2,
            question="Q2",
            options={"A": "1", "B": "2", "C": "3", "D": "4"},
            user_answer="B",
            correct_answer="B",
            is_correct=True,
            is_answered=True,
            explanation="Exp 2",
            topic="Process Scheduling"
        )
    ]
    weak = analyze_weak_topics(reviews)
    assert weak == []


def test_analyze_weak_topics_critical_weakness_prioritization():
    """Critical weaknesses (0% accuracy with multiple questions or missed answers) rank highest."""
    reviews = [
        # Topic 1: Memory Management (2 questions, both wrong -> High Priority / Critical)
        QuestionReviewItem(
            id=1, question="Q1", options={"A": "1", "B": "2", "C": "3", "D": "4"},
            user_answer="A", correct_answer="B", is_correct=False, is_answered=True,
            explanation="Exp", topic="Memory Management"
        ),
        QuestionReviewItem(
            id=2, question="Q2", options={"A": "1", "B": "2", "C": "3", "D": "4"},
            user_answer="A", correct_answer="B", is_correct=False, is_answered=True,
            explanation="Exp", topic="Memory Management"
        ),
        # Topic 2: Process Scheduling (2 questions: 1 correct, 1 incorrect -> Medium Priority / Moderate)
        QuestionReviewItem(
            id=3, question="Q3", options={"A": "1", "B": "2", "C": "3", "D": "4"},
            user_answer="B", correct_answer="B", is_correct=True, is_answered=True,
            explanation="Exp", topic="Process Scheduling"
        ),
        QuestionReviewItem(
            id=4, question="Q4", options={"A": "1", "B": "2", "C": "3", "D": "4"},
            user_answer="A", correct_answer="B", is_correct=False, is_answered=True,
            explanation="Exp", topic="Process Scheduling"
        ),
        # Topic 3: Cache Coherence (3 questions: 2 correct, 1 incorrect -> Low Priority / Needs Attention)
        QuestionReviewItem(
            id=5, question="Q5", options={"A": "1", "B": "2", "C": "3", "D": "4"},
            user_answer="B", correct_answer="B", is_correct=True, is_answered=True,
            explanation="Exp", topic="Cache Coherence"
        ),
        QuestionReviewItem(
            id=6, question="Q6", options={"A": "1", "B": "2", "C": "3", "D": "4"},
            user_answer="B", correct_answer="B", is_correct=True, is_answered=True,
            explanation="Exp", topic="Cache Coherence"
        ),
        QuestionReviewItem(
            id=7, question="Q7", options={"A": "1", "B": "2", "C": "3", "D": "4"},
            user_answer="A", correct_answer="B", is_correct=False, is_answered=True,
            explanation="Exp", topic="Cache Coherence"
        )
    ]

    weak = analyze_weak_topics(reviews)
    assert len(weak) == 3

    # Ranking check: High priority first
    assert weak[0].topic == "Memory Management"
    assert weak[0].priority == "high"
    assert weak[0].weakness_indicator == "Critical Weakness"
    assert weak[0].incorrect_count == 2
    assert weak[0].accuracy_percentage == 0.0

    # Second: Medium priority
    assert weak[1].topic == "Process Scheduling"
    assert weak[1].priority == "medium"
    assert weak[1].weakness_indicator == "Moderate Weakness"
    assert weak[1].accuracy_percentage == 50.0

    # Third: Low priority
    assert weak[2].topic == "Cache Coherence"
    assert weak[2].priority == "low"
    assert weak[2].weakness_indicator == "Needs Attention"
    assert weak[2].accuracy_percentage == 66.7


def test_single_unanswered_question_does_not_overclaim_weakness():
    """A single unanswered question on a topic notes limited evidence and assigns low priority."""
    reviews = [
        QuestionReviewItem(
            id=1,
            question="What is deadlock avoidance?",
            options={"A": "1", "B": "2", "C": "3", "D": "4"},
            user_answer=None,
            correct_answer="A",
            is_correct=False,
            is_answered=False,
            explanation="Banker algorithm avoids deadlock.",
            topic="Deadlock Avoidance"
        )
    ]
    weak = analyze_weak_topics(reviews)
    assert len(weak) == 1
    item = weak[0]
    assert item.topic == "Deadlock Avoidance"
    assert item.priority == "low"
    assert item.weakness_indicator == "Needs Attention"
    assert "limited" in item.reason.lower()


def test_missing_topic_metadata_on_reviews_is_auto_tagged():
    """If review items have topic=None, analyze_weak_topics automatically tags and groups them."""
    reviews = [
        QuestionReviewItem(
            id=1,
            question="What is the role of mitochondria in cellular energy?",
            options={"A": "1", "B": "2", "C": "3", "D": "4"},
            user_answer="A",
            correct_answer="B",
            is_correct=False,
            is_answered=True,
            explanation="Mitochondria produce ATP through respiration.",
            topic=None
        )
    ]
    weak = analyze_weak_topics(reviews)
    assert len(weak) == 1
    assert weak[0].topic is not None
    assert len(weak[0].topic) > 3


# -----------------------------------------------------------------------------
# End-to-End API Integration Tests for Weak Topics
# -----------------------------------------------------------------------------
def test_api_submit_returns_weak_topics_structure():
    """POST /api/revision/submit returns structured weak_topics with topics, priorities, and recommendations."""
    questions = [
        {
            "id": 1,
            "question": "What is virtual memory?",
            "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "correct_answer": "B",
            "explanation": "Virtual memory maps logical to physical addresses.",
            "topic": "Virtual Memory"
        },
        {
            "id": 2,
            "question": "What is demand paging?",
            "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "correct_answer": "A",
            "explanation": "Demand paging loads pages only when needed.",
            "topic": "Virtual Memory"
        },
        {
            "id": 3,
            "question": "What is round-robin scheduling?",
            "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "correct_answer": "C",
            "explanation": "Round-robin assigns fixed time quantum.",
            "topic": "CPU Scheduling"
        }
    ]

    # Q1 incorrect, Q2 incorrect, Q3 correct
    payload = {
        "questions": questions,
        "user_answers": {"1": "A", "2": "C", "3": "C"},
        "time_spent_seconds": 90
    }

    response = client.post("/api/revision/submit", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "weak_topics" in data
    weak_topics = data["weak_topics"]
    assert len(weak_topics) == 1

    wt = weak_topics[0]
    assert wt["topic"] == "Virtual Memory"
    assert wt["total_questions"] == 2
    assert wt["incorrect_count"] == 2
    assert wt["accuracy_percentage"] == 0.0
    assert wt["priority"] == "high"
    assert wt["weakness_indicator"] == "Critical Weakness"
    assert "Virtual Memory" in wt["recommendation"]
    assert len(wt["reason"]) > 10


def test_api_submit_all_correct_empty_weak_topics():
    """When a student achieves 100%, weak_topics is an empty list."""
    questions = [
        {
            "id": 1,
            "question": "What is DNS?",
            "options": {"A": "Domain Name System", "B": "2", "C": "3", "D": "4"},
            "correct_answer": "A",
            "explanation": "DNS resolves domain names.",
            "topic": "Networking"
        }
    ]
    payload = {
        "questions": questions,
        "user_answers": {"1": "A"}
    }
    response = client.post("/api/revision/submit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["score_percentage"] == 100.0
    assert data["weak_topics"] == []
