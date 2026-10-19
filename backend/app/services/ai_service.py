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


async def generate_revision_questions(
    extracted_text: str,
    time_remaining: int,
    question_count: int,
    client: Optional[httpx.AsyncClient] = None
) -> List[Dict[str, Any]]:
    """
    Generate structured revision questions using Google Gemini.

    Args:
        extracted_text: Text extracted from the study PDF.
        time_remaining: Available study time in minutes.
        question_count: Target number of questions (1-50).
        client: Optional httpx.AsyncClient for dependency injection / testing.

    Returns:
        List of normalized question dictionaries.

    Raises:
        AIServiceConfigurationError: If AI_API_KEY is missing or empty.
        AIServiceError: If Gemini API fails, times out, or returns invalid structure.
    """
    api_key = settings.AI_API_KEY.strip()
    if not api_key:
        logger.warning("AI_API_KEY is not configured in settings")
        raise AIServiceConfigurationError(
            "AI generation is not configured yet. Please check the backend Gemini configuration."
        )

    # Clean model identifier
    model_name = settings.AI_MODEL.strip()
    if model_name.startswith("models/"):
        model_name = model_name[7:]

    # Build prompt
    prompt = build_revision_prompt(
        extracted_text=extracted_text,
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
        raise AIServiceError("We couldn't generate your revision test right now. Please try again.") from exc
    except httpx.RequestError as exc:
        logger.error("Gemini API network connection failed: %s", str(exc))
        raise AIServiceError("We couldn't generate your revision test right now. Please try again.") from exc

    if response.status_code != 200:
        logger.error(
            "Gemini API returned non-200 status %d: %s",
            response.status_code,
            response.text[:200]
        )
        raise AIServiceError("We couldn't generate your revision test right now. Please try again.")

    try:
        response_json = response.json()
        candidates = response_json.get("candidates", [])
        if not candidates:
            raise ValueError("No candidates returned in Gemini response")

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise ValueError("No content parts returned in candidate")

        raw_text = parts[0].get("text", "")
    except Exception as exc:
        logger.error("Failed to extract content part from Gemini response: %s", str(exc))
        raise AIServiceError("We couldn't generate your revision test right now. Please try again.") from exc

    return parse_and_validate_questions(raw_text, expected_count=question_count)
