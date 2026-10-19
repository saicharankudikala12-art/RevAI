"""Gemini AI revision test generation service."""
import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx

try:
    from backend.app.core.config import settings
except ImportError:  # pragma: no cover
    from app.core.config import settings

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Base exception for AI generation service errors."""
    def __init__(self, message: str, status_code: int = 502):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AIServiceConfigurationError(AIServiceError):
    """Raised when the AI service is missing required configuration such as an API key."""
    def __init__(self, message: str = "AI generation is not configured yet. Please check the backend Gemini configuration."):
        super().__init__(message=message, status_code=503)


def build_revision_prompt(extracted_text: str, time_remaining: int, question_count: int) -> str:
    """
    Construct a focused prompt instructing Gemini to generate high-yield MCQs
    tailored to the student's study material, available time, and target question count.
    """
    pace = round(time_remaining / question_count, 1) if question_count > 0 else 1.0

    return f"""You are an expert exam revision tutor helping a student conduct high-yield, last-minute exam revision.

STUDENT CONTEXT:
- Allocated Revision Time: {time_remaining} minutes
- Target Question Count: {question_count} questions
- Estimated Pace: ~{pace} minutes per question

CRITICAL RULES:
1. Base all questions strictly and exclusively on the STUDY MATERIAL provided below. Do not test external facts, niche trivia, or concepts not covered in the text.
2. Prioritize high-yield, core concepts, essential definitions, primary mechanisms, and frequently examined principles.
3. Generate exactly {question_count} distinct multiple-choice questions (MCQs).
4. Each question must have exactly 4 choices: "A", "B", "C", and "D". Only one option must be correct.
5. Provide a concise explanation explaining why the correct choice is right and briefly why the distractors are incorrect.
6. The "correct_answer" must be a single uppercase letter: "A", "B", "C", or "D".

OUTPUT FORMAT:
You MUST respond with a valid JSON object matching this exact schema:
{{
  "questions": [
    {{
      "id": 1,
      "question": "Clear, direct question prompt?",
      "options": {{
        "A": "Option A text",
        "B": "Option B text",
        "C": "Option C text",
        "D": "Option D text"
      }},
      "correct_answer": "A",
      "explanation": "Clear explanation of the correct choice."
    }}
  ]
}}

STUDY MATERIAL:
\"\"\"
{extracted_text}
\"\"\"
"""


def _clean_json_text(raw_text: str) -> str:
    """Strip markdown code fences and whitespace from raw LLM output."""
    text = raw_text.strip()
    # Match ```json ... ``` or ``` ... ```
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def parse_and_validate_questions(raw_text: str, expected_count: int) -> List[Dict[str, Any]]:
    """Parse JSON string from Gemini and normalize question structure."""
    clean_text = _clean_json_text(raw_text)

    try:
        data = json.loads(clean_text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to decode JSON from AI response: %s", str(exc))
        raise AIServiceError("We couldn't generate your revision test right now. Please try again.") from exc

    raw_list: List[Any] = []
    if isinstance(data, dict):
        if "questions" in data and isinstance(data["questions"], list):
            raw_list = data["questions"]
        elif "revision_test" in data and isinstance(data["revision_test"], list):
            raw_list = data["revision_test"]
        else:
            # Look for any list in the dict
            for val in data.values():
                if isinstance(val, list):
                    raw_list = val
                    break
    elif isinstance(data, list):
        raw_list = data

    if not raw_list:
        logger.error("No questions list found in parsed AI response")
        raise AIServiceError("We couldn't generate your revision test right now. Please try again.")

    normalized_questions: List[Dict[str, Any]] = []

    for idx, item in enumerate(raw_list, start=1):
        if not isinstance(item, dict):
            continue

        q_text = str(item.get("question", "")).strip()
        if not q_text:
            continue

        # Extract options
        raw_options = item.get("options")
        options_dict: Dict[str, str] = {}

        if isinstance(raw_options, dict):
            for opt_key in ["A", "B", "C", "D"]:
                val = raw_options.get(opt_key) or raw_options.get(opt_key.lower()) or ""
                options_dict[opt_key] = str(val).strip()
        elif isinstance(raw_options, list) and len(raw_options) >= 4:
            keys = ["A", "B", "C", "D"]
            for opt_idx, key in enumerate(keys):
                options_dict[key] = str(raw_options[opt_idx]).strip()
        else:
            continue

        # Validate that all 4 options have content
        if any(not options_dict[k] for k in ["A", "B", "C", "D"]):
            continue

        # Normalize correct_answer (strip 'Option A' or 'A.' -> 'A')
        raw_ans = str(item.get("correct_answer", "A")).strip().upper()
        match = re.search(r"\b([A-D])\b", raw_ans)
        correct_answer = match.group(1) if match else "A"

        explanation = str(item.get("explanation", "")).strip()
        if not explanation:
            explanation = f"Option {correct_answer} is the correct answer according to the study material."

        normalized_questions.append({
            "id": idx,
            "question": q_text,
            "options": options_dict,
            "correct_answer": correct_answer,
            "explanation": explanation
        })

    if not normalized_questions:
        logger.error("No valid questions remained after normalization")
        raise AIServiceError("We couldn't generate your revision test right now. Please try again.")

    return normalized_questions


MINIMUM_EXTRACTED_WORDS = 5
MINIMUM_EXTRACTED_CHARS = 30


class InsufficientContentError(AIServiceError):
    """Raised when the study material does not contain enough text to generate questions."""
    def __init__(self, message: str = "The study material does not provide enough text to generate revision questions."):
        super().__init__(message=message, status_code=400)


def generate_heuristic_fallback_questions(
    extracted_text: str,
    question_count: int
) -> List[Dict[str, Any]]:
    """
    Generate grounded fallback revision questions directly derived from the study text.
    Clearly marks questions as heuristic-fallback, ensuring never to present them
    as genuine Gemini AI output.
    """
    sentences = [
        s.strip() for s in re.split(r"(?<=[.!?])\s+", extracted_text)
        if len(s.strip()) > 20
    ]
    if not sentences:
        words = extracted_text.split()
        chunk_size = 15
        sentences = [
            " ".join(words[i:i + chunk_size])
            for i in range(0, min(len(words), 150), chunk_size)
        ]

    if not sentences:
        raise InsufficientContentError("Not enough readable content in the PDF to generate fallback questions.")

    questions: List[Dict[str, Any]] = []
    total_sentences = len(sentences)

    for i in range(question_count):
        target_sent = sentences[i % total_sentences]
        distractor_1 = sentences[(i + 1) % total_sentences]
        distractor_2 = sentences[(i + 2) % total_sentences]
        distractor_3 = sentences[(i + 3) % total_sentences]

        prompt_text = f"According to the study material: '{target_sent[:120]}...', which statement accurately reflects this concept?"

        options = {
            "A": f"{target_sent[:90]}.",
            "B": f"Contrastingly: {distractor_1[:80]}.",
            "C": f"Alternatively: {distractor_2[:80]}.",
            "D": f"Furthermore: {distractor_3[:80]}."
        }

        questions.append({
            "id": i + 1,
            "question": prompt_text,
            "options": options,
            "correct_answer": "A",
            "explanation": f"[Fallback Review] Option A is directly quoted from the study material: '{target_sent[:100]}...'"
        })

    return questions


async def generate_revision_questions(
    extracted_text: str,
    time_remaining: int,
    question_count: int,
    client: Optional[httpx.AsyncClient] = None,
    allow_fallback: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Generate structured revision questions using Google Gemini, with robust fallback
    and validation handling.

    Args:
        extracted_text: Text extracted from the study PDF.
        time_remaining: Available study time in minutes.
        question_count: Target number of questions (1-50).
        client: Optional httpx.AsyncClient for dependency injection / testing.
        allow_fallback: Whether to use heuristic fallback on AI failure (defaults to settings.ALLOW_HEURISTIC_FALLBACK).

    Returns:
        Dict with keys:
            - questions: List of normalized question dicts
            - provider: "gemini" or "heuristic-fallback"
            - model: AI model used (or None for fallback)

    Raises:
        InsufficientContentError: If text is empty or too short.
        AIServiceConfigurationError: If API key is missing or unauthorized.
        AIServiceError: If Gemini API fails, times out, rate limits, or outputs invalid schema.
    """
    clean_text = (extracted_text or "").strip()
    if not clean_text or len(clean_text) < MINIMUM_EXTRACTED_CHARS or len(clean_text.split()) < MINIMUM_EXTRACTED_WORDS:
        raise InsufficientContentError(
            "The study material does not provide enough text to generate revision questions. "
            "Please upload a document with more study content."
        )

    api_key = settings.effective_ai_api_key
    fallback_enabled = allow_fallback if allow_fallback is not None else settings.ALLOW_HEURISTIC_FALLBACK

    if not api_key:
        logger.warning("No effective Gemini API key configured in settings (AI_API_KEY / GEMINI_API_KEY)")
        if fallback_enabled:
            logger.info("Falling back to heuristic question generation due to missing API key")
            fallback_qs = generate_heuristic_fallback_questions(clean_text, question_count)
            return {
                "questions": fallback_qs,
                "provider": "heuristic-fallback",
                "model": None
            }
        raise AIServiceConfigurationError(
            "AI generation is not configured yet. Please check the backend Gemini configuration."
        )

    # Clean model identifier
    model_name = settings.AI_MODEL.strip()
    if model_name.startswith("models/"):
        model_name = model_name[7:]

    # Build prompt
    prompt = build_revision_prompt(
        extracted_text=clean_text,
        time_remaining=time_remaining,
        question_count=question_count
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }

    try:
        if client is not None:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        else:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(url, headers=headers, json=payload, timeout=60.0)
    except httpx.TimeoutException as exc:
        logger.error("Gemini API request timed out: %s", str(exc))
        if fallback_enabled:
            logger.info("Falling back to heuristic question generation due to Gemini timeout")
            fallback_qs = generate_heuristic_fallback_questions(clean_text, question_count)
            return {
                "questions": fallback_qs,
                "provider": "heuristic-fallback",
                "model": None
            }
        raise AIServiceError("We couldn't generate your revision test right now. Please try again.") from exc
    except httpx.RequestError as exc:
        logger.error("Gemini API network connection failed: %s", str(exc))
        if fallback_enabled:
            logger.info("Falling back to heuristic question generation due to network error")
            fallback_qs = generate_heuristic_fallback_questions(clean_text, question_count)
            return {
                "questions": fallback_qs,
                "provider": "heuristic-fallback",
                "model": None
            }
        raise AIServiceError("We couldn't generate your revision test right now. Please try again.") from exc

    if response.status_code == 401 or response.status_code == 403:
        logger.error("Gemini API authentication failed with status %d: %s", response.status_code, response.text[:200])
        if fallback_enabled:
            fallback_qs = generate_heuristic_fallback_questions(clean_text, question_count)
            return {
                "questions": fallback_qs,
                "provider": "heuristic-fallback",
                "model": None
            }
        raise AIServiceConfigurationError("AI service authentication failed. Please verify your Gemini API key.")

    if response.status_code == 429:
        logger.warning("Gemini API rate limit exceeded (429): %s", response.text[:200])
        if fallback_enabled:
            fallback_qs = generate_heuristic_fallback_questions(clean_text, question_count)
            return {
                "questions": fallback_qs,
                "provider": "heuristic-fallback",
                "model": None
            }
        raise AIServiceError("AI rate limit reached. Please wait a moment and try again.", status_code=429)

    if response.status_code != 200:
        logger.error(
            "Gemini API returned non-200 status %d: %s",
            response.status_code,
            response.text[:200]
        )
        if fallback_enabled:
            fallback_qs = generate_heuristic_fallback_questions(clean_text, question_count)
            return {
                "questions": fallback_qs,
                "provider": "heuristic-fallback",
                "model": None
            }
        raise AIServiceError("We couldn't generate your revision test right now. Please try again.")

    try:
        response_json = response.json()
        candidates = response_json.get("candidates", [])
        if not candidates:
            raise ValueError("No candidates returned in Gemini response")

        candidate = candidates[0]
        finish_reason = candidate.get("finishReason")
        if finish_reason and finish_reason in ["SAFETY", "RECITATION"]:
            logger.warning("Gemini generation stopped with finishReason: %s", finish_reason)
            raise AIServiceError("Study content could not be processed due to safety policies.")

        content = candidate.get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise ValueError("No content parts returned in candidate")

        raw_text = parts[0].get("text", "")
    except Exception as exc:
        logger.error("Failed to extract content part from Gemini response: %s", str(exc))
        if fallback_enabled:
            fallback_qs = generate_heuristic_fallback_questions(clean_text, question_count)
            return {
                "questions": fallback_qs,
                "provider": "heuristic-fallback",
                "model": None
            }
        raise AIServiceError("We couldn't generate your revision test right now. Please try again.") from exc

    try:
        parsed_questions = parse_and_validate_questions(raw_text, expected_count=question_count)
    except AIServiceError:
        if fallback_enabled:
            fallback_qs = generate_heuristic_fallback_questions(clean_text, question_count)
            return {
                "questions": fallback_qs,
                "provider": "heuristic-fallback",
                "model": None
            }
        raise

    return {
        "questions": parsed_questions,
        "provider": "gemini",
        "model": model_name
    }
