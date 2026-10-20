"""Pydantic schemas for request and response validation."""
from datetime import datetime, timezone
from typing import Optional, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response schema for the system health check."""
    status: str = Field(default="healthy", description="Current health status of the service")
    app_name: str = Field(description="Name of the application")
    version: str = Field(description="Semantic version of the application")
    environment: str = Field(description="Current deployment environment")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the health check"
    )


class PDFUploadResponse(BaseModel):
    """Response schema for successful PDF upload and extraction."""
    success: bool = Field(default=True, description="Whether the processing succeeded")
    status: str = Field(default="processed", description="Current PDF processing status")
    filename: str = Field(description="Original name of the uploaded PDF")
    page_count: int = Field(description="Total number of pages automatically detected in the PDF")
    extracted_text: str = Field(description="Full extracted text from all pages of the PDF")
    text_length: int = Field(description="Total character count of extracted text")
    word_count: int = Field(description="Total word count of extracted text")
    preview: str = Field(description="Short preview snippet of the extracted text")
    message: str = Field(default="PDF processed successfully", description="User-friendly status message")


class APIErrorResponse(BaseModel):
    """Standard error response payload."""
    detail: str = Field(description="Error message detailing the failure")
    error_code: Optional[str] = Field(default=None, description="Optional machine-readable error code")
    context: Optional[dict[str, Any]] = Field(default=None, description="Additional context or validation details")


class QuestionItem(BaseModel):
    """Schema for a single multiple-choice revision question (server-side, includes answer & explanation)."""
    id: int = Field(description="1-based question number")
    question: str = Field(description="The question prompt")
    options: dict[str, str] = Field(description="Four choices keyed by A, B, C, D")
    correct_answer: str = Field(description="Correct choice identifier: A, B, C, or D")
    explanation: str = Field(description="Clear explanation of the correct choice")
    topic: Optional[str] = Field(default=None, description="Topic or core concept associated with this question")


class QuestionClientItem(BaseModel):
    """Client-facing question schema (omits correct_answer and explanation before submission)."""
    id: int = Field(description="1-based question number")
    question: str = Field(description="The question prompt")
    options: dict[str, str] = Field(description="Four choices keyed by A, B, C, D")
    topic: Optional[str] = Field(default=None, description="Topic or core concept associated with this question")


class RevisionGenerateRequest(BaseModel):
    """Request payload for generating revision test questions."""
    extracted_text: str = Field(..., description="Extracted study material text from PDF")
    time_remaining: int = Field(..., gt=0, description="Available study time in minutes")
    question_count: int = Field(..., gt=0, le=50, description="Target number of questions (1-50)")


class RevisionGenerateResponse(BaseModel):
    """Response payload for successfully generated revision questions."""
    success: bool = Field(default=True, description="Whether question generation succeeded")
    provider: str = Field(default="gemini", description="Question generation provider used: 'gemini' or 'heuristic-fallback'")
    model: Optional[str] = Field(default=None, description="AI model used if generated via AI")
    time_remaining: int = Field(description="Study time allocated in minutes")
    question_count: int = Field(description="Total number of generated questions")
    questions: list[QuestionItem] = Field(description="List of structured revision questions")
    test_token: Optional[str] = Field(default=None, description="HMAC-signed tamper-proof test token containing authoritative answer key")


class TestSubmissionRequest(BaseModel):
    """Request payload for submitting answers to be scored."""
    test_token: Optional[str] = Field(default=None, description="HMAC-signed test token provided at generation time")
    # For compatibility if client submits with original questions or token
    questions: Optional[list[QuestionItem]] = Field(default=None, description="Authoritative questions if token is omitted")
    user_answers: dict[str, Optional[str]] = Field(default_factory=dict, description="Map of question_id (as str or int) to selected option ('A', 'B', 'C', 'D' or null)")
    time_spent_seconds: Optional[int] = Field(default=None, ge=0, description="Optional time spent in seconds")


class QuestionReviewItem(BaseModel):
    """Detailed review item for each question after test grading."""
    id: int = Field(description="1-based question number")
    question: str = Field(description="The question prompt")
    options: dict[str, str] = Field(description="All four options")
    user_answer: Optional[str] = Field(default=None, description="User's selected option identifier or None if unanswered")
    correct_answer: str = Field(description="Authoritative correct option identifier: A, B, C, or D")
    is_correct: bool = Field(description="Whether the user answered correctly")
    is_answered: bool = Field(description="Whether the user attempted this question")
    explanation: str = Field(description="Explanation of the correct answer from AI study generation")
    topic: Optional[str] = Field(default=None, description="Topic or core concept associated with this question")


class WeakTopicItem(BaseModel):
    """Schema for a categorized weak topic or study concept."""
    topic: str = Field(description="Name of the topic or concept")
    total_questions: int = Field(description="Number of questions associated with this topic")
    incorrect_count: int = Field(description="Number of incorrectly answered questions for this topic")
    unanswered_count: int = Field(description="Number of unanswered questions for this topic")
    accuracy_percentage: float = Field(description="Accuracy percentage on this topic (0.0 - 100.0)")
    weakness_indicator: str = Field(description="Weakness severity: 'Critical Weakness', 'Moderate Weakness', or 'Needs Attention'")
    priority: str = Field(description="Priority ranking for revision: 'high', 'medium', or 'low'")
    reason: str = Field(description="Short diagnostic explanation of why this topic needs revision")
    recommendation: str = Field(description="Prioritized, actionable revision recommendation")


class TestSubmissionResponse(BaseModel):
    """Graded result and analysis payload for a submitted test."""
    success: bool = Field(default=True, description="Whether test grading succeeded")
    total_questions: int = Field(description="Total number of questions in test")
    correct_count: int = Field(description="Number of correctly answered questions")
    incorrect_count: int = Field(description="Number of incorrectly answered questions")
    unanswered_count: int = Field(description="Number of unanswered questions")
    score_percentage: float = Field(description="Score percentage rounded to 1 decimal place (0.0 - 100.0)")
    performance_rating: str = Field(description="Performance rating: Excellent, Good, Fair, Needs Review")
    performance_summary: str = Field(description="Actionable summary text evaluating the student's revision performance")
    time_spent_seconds: Optional[int] = Field(default=None, description="Time spent taking the test in seconds")
    questions_review: list[QuestionReviewItem] = Field(description="Per-question review breakdown with answers and explanations")
    weak_topics: list[WeakTopicItem] = Field(default_factory=list, description="Prioritized list of weak concepts and targeted revision recommendations")



