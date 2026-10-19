"""Service layer for secure test scoring, token issuance, and performance evaluation."""
import base64
import hashlib
import hmac
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    from backend.app.core.config import settings
    from backend.app.models.schemas import (
        QuestionItem,
        QuestionReviewItem,
        TestSubmissionResponse,
    )
except ImportError:  # pragma: no cover
    from app.core.config import settings
    from app.models.schemas import (
        QuestionItem,
        QuestionReviewItem,
        TestSubmissionResponse,
    )

logger = logging.getLogger(__name__)


class ScoringError(Exception):
    """Exception raised when test scoring or token verification fails."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def create_test_token(questions: List[Dict[str, Any]] | List[QuestionItem]) -> str:
    """
    Generate a tamper-proof HMAC-signed token encapsulating the questions,
    correct answers, and explanations.

    Format: <base64url_payload>.<hex_hmac_signature>
    """
    secret = settings.SECRET_KEY.encode("utf-8")
    
    # Normalize question dicts
    clean_questions = []
    for q in questions:
        if isinstance(q, QuestionItem):
            clean_questions.append(q.model_dump())
        elif isinstance(q, dict):
            clean_questions.append(q)

    payload_json = json.dumps(clean_questions, separators=(",", ":"), ensure_ascii=False)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")
    
    signature = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_test_token(token: str) -> List[Dict[str, Any]]:
    """
    Verify the HMAC signature of a test token and decode the authoritative questions.
    Raises ScoringError if signature is invalid or token is malformed.
    """
    if not token or "." not in token:
        raise ScoringError("Invalid or missing test token format.", status_code=400)

    parts = token.split(".")
    if len(parts) != 2:
        raise ScoringError("Malformed test token.", status_code=400)

    payload_b64, signature = parts[0], parts[1]
    secret = settings.SECRET_KEY.encode("utf-8")
    
    expected_signature = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        logger.warning("Test token signature verification failed.")
        raise ScoringError("Tampered or invalid test session token.", status_code=400)

    # Pad base64 string
    padding_needed = (4 - len(payload_b64) % 4) % 4
    padded_b64 = payload_b64 + ("=" * padding_needed)

    try:
        decoded_bytes = base64.urlsafe_b64decode(padded_b64)
        questions_data = json.loads(decoded_bytes.decode("utf-8"))
        if not isinstance(questions_data, list):
            raise ValueError("Decoded payload is not a question list.")
        return questions_data
    except Exception as exc:
        logger.error("Failed to decode token payload: %s", str(exc))
        raise ScoringError("Could not parse test session questions from token.", status_code=400) from exc


def calculate_performance_summary(
    score_percentage: float,
    correct: int,
    total: int,
    unanswered: int
) -> Tuple[str, str]:
    """
    Generate an insightful, encouraging performance rating and actionable summary.
    """
    if total == 0:
        return "N/A", "No questions were evaluated in this test."

    if score_percentage >= 90.0:
        rating = "Excellent"
        summary = (
            f"Outstanding mastery! You answered {correct} of {total} questions correctly "
            f"({score_percentage:.1f}%). You are thoroughly prepared on these study concepts."
        )
    elif score_percentage >= 75.0:
        rating = "Good"
        summary = (
            f"Strong performance! You scored {score_percentage:.1f}% with {correct} correct. "
            f"Review the {total - correct} missed concept(s) below to reach exam readiness."
        )
    elif score_percentage >= 50.0:
        rating = "Fair"
        summary = (
            f"Solid foundation! You scored {score_percentage:.1f}%. "
            f"Focus on the detailed explanations in the answer review below to reinforce your weaker areas."
        )
    else:
        rating = "Needs Review"
        summary = (
            f"Needs attention. You scored {score_percentage:.1f}%. "
            f"Take time to read each question's explanation below and re-study the key principles from your PDF notes."
        )

    if unanswered > 0:
        summary += f" Note: {unanswered} question(s) were left unanswered."

    return rating, summary


def evaluate_test_submission(
    authoritative_questions: List[Dict[str, Any]] | List[QuestionItem],
    user_answers: Dict[str, Optional[str]],
    time_spent_seconds: Optional[int] = None
) -> TestSubmissionResponse:
    """
    Deterministically score a submitted test against authoritative questions.

    Args:
        authoritative_questions: Questions containing question, options, correct_answer, explanation.
        user_answers: Map of question id (int or str) to chosen option letter ('A', 'B', 'C', 'D' or None).
        time_spent_seconds: Optional test duration.

    Returns:
        TestSubmissionResponse with score metrics and detailed QuestionReviewItem list.
    """
    if not authoritative_questions:
        return TestSubmissionResponse(
            success=True,
            total_questions=0,
            correct_count=0,
            incorrect_count=0,
            unanswered_count=0,
            score_percentage=0.0,
            performance_rating="N/A",
            performance_summary="The test contained 0 questions.",
            time_spent_seconds=time_spent_seconds,
            questions_review=[]
        )

    total_questions = len(authoritative_questions)
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0
    reviews: List[QuestionReviewItem] = []

    # Normalize user answers map (ensure string keys and uppercase values)
    raw_normalized: Dict[str, str] = {}
    for k, v in (user_answers or {}).items():
        if v is not None and str(v).strip():
            clean_val = str(v).strip().upper()
            if clean_val in ["A", "B", "C", "D"]:
                raw_normalized[str(k).strip()] = clean_val

    # Detect whether the keys are question IDs or 0-based indexes
    # If "0" is present, the client is submitting 0-based indices { "0": ..., "1": ... }
    is_zero_indexed_dict = "0" in raw_normalized

    normalized_answers: Dict[str, str] = {}
    if is_zero_indexed_dict:
        for idx_str, ans in raw_normalized.items():
            try:
                # Map 0 -> 1, 1 -> 2, etc.
                mapped_q_id = str(int(idx_str) + 1)
                normalized_answers[mapped_q_id] = ans
            except ValueError:
                normalized_answers[idx_str] = ans
    else:
        normalized_answers = raw_normalized

    for idx, raw_q in enumerate(authoritative_questions, start=1):
        if isinstance(raw_q, QuestionItem):
            q_id = raw_q.id
            q_text = raw_q.question
            options = raw_q.options
            correct_ans = str(raw_q.correct_answer).strip().upper()
            explanation = raw_q.explanation
        else:
            q_id = int(raw_q.get("id", idx))
            q_text = str(raw_q.get("question", "")).strip()
            options = raw_q.get("options", {})
            correct_ans = str(raw_q.get("correct_answer", "A")).strip().upper()
            explanation = str(raw_q.get("explanation", ""))

        user_choice = normalized_answers.get(str(q_id))

        is_answered = user_choice is not None
        is_correct = False



        if not is_answered:
            unanswered_count += 1
        elif user_choice == correct_ans:
            correct_count += 1
            is_correct = True
        else:
            incorrect_count += 1

        reviews.append(
            QuestionReviewItem(
                id=q_id,
                question=q_text,
                options=options,
                user_answer=user_choice,
                correct_answer=correct_ans,
                is_correct=is_correct,
                is_answered=is_answered,
                explanation=explanation
            )
        )

    score_percentage = round((correct_count / total_questions) * 100.0, 1) if total_questions > 0 else 0.0
    rating, summary = calculate_performance_summary(
        score_percentage=score_percentage,
        correct=correct_count,
        total=total_questions,
        unanswered=unanswered_count
    )

    return TestSubmissionResponse(
        success=True,
        total_questions=total_questions,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        unanswered_count=unanswered_count,
        score_percentage=score_percentage,
        performance_rating=rating,
        performance_summary=summary,
        time_spent_seconds=time_spent_seconds,
        questions_review=reviews
    )
