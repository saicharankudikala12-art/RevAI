"""Service for generating smart revision flashcards prioritized by weak topics and incorrect answers."""
import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx

try:
    from backend.app.core.config import settings
    from backend.app.models.schemas import FlashcardItem, WeakTopicItem, QuestionReviewItem
    from backend.app.services.ai_service import (
        AIServiceError,
        AIServiceConfigurationError,
        InsufficientContentError,
        MINIMUM_EXTRACTED_CHARS,
        MINIMUM_EXTRACTED_WORDS,
        _clean_json_text,
    )
    from backend.app.services.topic_service import extract_topic_from_question
except ImportError:  # pragma: no cover
    from app.core.config import settings
    from app.models.schemas import FlashcardItem, WeakTopicItem, QuestionReviewItem
    from app.services.ai_service import (
        AIServiceError,
        AIServiceConfigurationError,
        InsufficientContentError,
        MINIMUM_EXTRACTED_CHARS,
        MINIMUM_EXTRACTED_WORDS,
        _clean_json_text,
    )
    from app.services.topic_service import extract_topic_from_question

logger = logging.getLogger(__name__)


def build_flashcards_prompt(
    extracted_text: str,
    weak_topics: List[WeakTopicItem],
    incorrect_questions: List[QuestionReviewItem],
    max_cards: int = 10
) -> str:
    """Construct prompt for Gemini to generate focused revision flashcards."""
    weak_topics_summary = ""
    if weak_topics:
        topics_lines = [
            f"- {wt.topic} (Priority: {wt.priority}, Missed: {wt.incorrect_count}, Accuracy: {wt.accuracy_percentage}%)"
            for wt in weak_topics[:5]
        ]
        weak_topics_summary = "IDENTIFIED STUDENT WEAK TOPICS:\n" + "\n".join(topics_lines) + "\n\n"

    missed_questions_summary = ""
    if incorrect_questions:
        q_lines = []
        for q in incorrect_questions[:6]:
            q_lines.append(f"- Question: {q.question}\n  Correct Answer: {q.options.get(q.correct_answer, '')}\n  Explanation: {q.explanation}")
        missed_questions_summary = "SPECIFIC MISSED / SKIPPED QUESTIONS:\n" + "\n".join(q_lines) + "\n\n"

    return f"""You are an expert exam tutor creating rapid-review revision flashcards for a student right before an exam.

CRITICAL INSTRUCTIONS:
1. Base all flashcards strictly and exclusively on the STUDY MATERIAL provided below.
2. Prioritize concepts from the student's WEAK TOPICS and MISSED QUESTIONS.
3. Generate exactly {max_cards} high-yield flashcards.
4. Each card must have:
   - "front": A clear, concise question or term/concept prompt to test recall.
   - "back": A direct, accurate answer or definition (1-3 sentences max).
   - "topic": The subject concept/topic name.
   - "memory_tip": A short mnemonic, memory trick, or key distinction to help remember under exam pressure.

{weak_topics_summary}{missed_questions_summary}OUTPUT FORMAT:
You MUST respond with a valid JSON object matching this exact schema:
{{
  "cards": [
    {{
      "id": 1,
      "front": "What is ...?",
      "back": "Clear, concise definition or answer.",
      "topic": "Topic Name",
      "memory_tip": "Short memory tip or mnemonic"
    }}
  ]
}}

STUDY MATERIAL:
\"\"\"
{extracted_text}
\"\"\"
"""


def parse_and_validate_flashcards(raw_text: str, expected_count: int) -> List[Dict[str, Any]]:
    """Parse JSON string from Gemini and normalize flashcard structure."""
    clean_text = _clean_json_text(raw_text)

    try:
        data = json.loads(clean_text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to decode JSON from AI flashcard response: %s", str(exc))
        raise AIServiceError("We couldn't generate your revision flashcards right now. Please try again.") from exc

    raw_list: List[Any] = []
    if isinstance(data, dict):
        if "cards" in data and isinstance(data["cards"], list):
            raw_list = data["cards"]
        elif "flashcards" in data and isinstance(data["flashcards"], list):
            raw_list = data["flashcards"]
        else:
            for val in data.values():
                if isinstance(val, list):
                    raw_list = val
                    break
    elif isinstance(data, list):
        raw_list = data

    if not raw_list:
        logger.error("No flashcards list found in parsed AI response")
        raise AIServiceError("We couldn't generate your revision flashcards right now. Please try again.")

    normalized: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_list, start=1):
        if not isinstance(item, dict):
            continue

        front = str(item.get("front", "") or item.get("question", "")).strip()
        back = str(item.get("back", "") or item.get("answer", "")).strip()

        if not front or not back:
            continue

        topic = str(item.get("topic", "")).strip()
        if not topic:
            topic = extract_topic_from_question(front, back)

        memory_tip = str(item.get("memory_tip", "") or item.get("tip", "") or item.get("explanation", "")).strip()
        if not memory_tip:
            memory_tip = f"Key exam takeaway for {topic}."

        normalized.append({
            "id": idx,
            "front": front,
            "back": back,
            "topic": topic,
            "memory_tip": memory_tip
        })

    if not normalized:
        logger.error("No valid flashcards remained after normalization")
        raise AIServiceError("We couldn't generate your revision flashcards right now. Please try again.")

    return normalized


def generate_heuristic_fallback_flashcards(
    extracted_text: str,
    weak_topics: List[WeakTopicItem],
    incorrect_questions: List[QuestionReviewItem],
    max_cards: int = 10
) -> List[Dict[str, Any]]:
    """
    Generate grounded fallback flashcards directly derived from the study text,
    weak topics, and missed test questions without making external AI calls.
    """
    cards: List[Dict[str, Any]] = []
    card_id = 1

    # Source 1: Convert missed / skipped questions into high-yield flashcards
    for q in incorrect_questions:
        if card_id > max_cards:
            break

        correct_choice_text = q.options.get(q.correct_answer, "")
        front = q.question.strip()
        # Clean question lead-in like "According to the study material: ..., which statement accurately reflects this concept?"
        if front.startswith("According to the study material:") and "which statement accurately reflects this concept" in front:
            match = re.search(r"'(.*?)'", front)
            if match:
                snippet = match.group(1).strip()
                front = f"What is the key principle regarding: '{snippet[:80]}...'?"

        topic = q.topic or extract_topic_from_question(q.question, q.explanation)
        back = f"Correct Answer: {correct_choice_text}." if correct_choice_text else q.explanation
        tip = q.explanation if q.explanation and "[Fallback Review]" not in q.explanation else f"Core principle to review for {topic}."

        cards.append({
            "id": card_id,
            "front": front,
            "back": back,
            "topic": topic,
            "memory_tip": tip
        })
        card_id += 1

    # Source 2: If we still need cards, derive directly from weak topic recommendations & study text
    if card_id <= max_cards and weak_topics:
        for wt in weak_topics:
            if card_id > max_cards:
                break
            cards.append({
                "id": card_id,
                "front": f"Key Focus: What is the core mechanism of {wt.topic}?",
                "back": wt.recommendation,
                "topic": wt.topic,
                "memory_tip": f"Diagnosed {wt.weakness_indicator.lower()}: {wt.reason}"
            })
            card_id += 1

    # Source 3: Fill remaining cards from grounded text sentences
    if card_id <= max_cards:
        sentences = [
            s.strip() for s in re.split(r"(?<=[.!?])\s+", extracted_text)
            if len(s.strip()) > 25 and any(c.isalnum() for c in s)
        ]
        if not sentences:
            words = [w for w in extracted_text.split() if any(c.isalnum() for c in w)]
            if len(words) >= 5:
                chunk_size = 15
                sentences = [
                    " ".join(words[i:i + chunk_size])
                    for i in range(0, min(len(words), 150), chunk_size)
                ]

        if not sentences and not cards:
            raise InsufficientContentError("Not enough readable content in the PDF to generate fallback flashcards.")

        total_sents = len(sentences)
        for i in range(max_cards - len(cards)):
            if not sentences:
                break
            target_sent = sentences[i % total_sents]
            topic = extract_topic_from_question(target_sent, "")
            cards.append({
                "id": card_id,
                "front": f"Core Concept: What statement summarizes '{target_sent[:70]}...'?",
                "back": f"{target_sent}.",
                "topic": topic,
                "memory_tip": f"Directly grounded review from study notes on {topic}."
            })
            card_id += 1

    if not cards:
        raise InsufficientContentError("Not enough readable content in the PDF to generate fallback flashcards.")

    return cards[:max_cards]


async def generate_revision_flashcards(
    extracted_text: str,
    weak_topics: Optional[List[WeakTopicItem]] = None,
    incorrect_questions: Optional[List[QuestionReviewItem]] = None,
    max_cards: int = 10,
    client: Optional[httpx.AsyncClient] = None,
    allow_fallback: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Generate structured revision flashcards using Google Gemini,
    with robust heuristic fallback prioritized by student weak topics and missed questions.
    """
    clean_text = (extracted_text or "").strip()
    if not clean_text or len(clean_text) < MINIMUM_EXTRACTED_CHARS or len(clean_text.split()) < MINIMUM_EXTRACTED_WORDS:
        raise InsufficientContentError(
            "The study material does not provide enough text to generate revision flashcards. "
            "Please upload a document with more study content."
        )

    w_topics = weak_topics or []
    inc_questions = incorrect_questions or []
    target_count = max(1, min(max_cards, 30))

    api_key = settings.effective_ai_api_key
    fallback_enabled = allow_fallback if allow_fallback is not None else settings.ALLOW_HEURISTIC_FALLBACK

    if not api_key:
        logger.warning("No effective Gemini API key configured for flashcards")
        if fallback_enabled:
            logger.info("Falling back to heuristic flashcard generation due to missing API key")
            cards = generate_heuristic_fallback_flashcards(clean_text, w_topics, inc_questions, target_count)
            return {
                "cards": cards,
                "provider": "heuristic-fallback",
                "model": None
            }
        raise AIServiceConfigurationError(
            "AI generation is not configured yet. Please check the backend Gemini configuration."
        )

    model_name = settings.AI_MODEL.strip()
    if model_name.startswith("models/"):
        model_name = model_name[7:]

    prompt = build_flashcards_prompt(
        extracted_text=clean_text,
        weak_topics=w_topics,
        incorrect_questions=inc_questions,
        max_cards=target_count
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
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        logger.error("Gemini API connection failed during flashcard generation: %s", str(exc))
        if fallback_enabled:
            cards = generate_heuristic_fallback_flashcards(clean_text, w_topics, inc_questions, target_count)
            return {
                "cards": cards,
                "provider": "heuristic-fallback",
                "model": None
            }
        raise AIServiceError("We couldn't generate your revision flashcards right now. Please try again.") from exc

    if response.status_code != 200:
        logger.warning("Gemini API non-200 (%d) during flashcards generation: %s", response.status_code, response.text[:200])
        if fallback_enabled:
            cards = generate_heuristic_fallback_flashcards(clean_text, w_topics, inc_questions, target_count)
            return {
                "cards": cards,
                "provider": "heuristic-fallback",
                "model": None
            }
        if response.status_code in [401, 403]:
            raise AIServiceConfigurationError("AI service authentication failed. Please verify your Gemini API key.")
        raise AIServiceError("We couldn't generate your revision flashcards right now. Please try again.")

    try:
        response_json = response.json()
        candidates = response_json.get("candidates", [])
        if not candidates:
            raise ValueError("No candidates returned in Gemini flashcards response")
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise ValueError("No content parts returned in candidate")
        raw_text = parts[0].get("text", "")
        cards_data = parse_and_validate_flashcards(raw_text, expected_count=target_count)
    except Exception as exc:
        logger.error("Error parsing flashcard AI response: %s", str(exc))
        if fallback_enabled:
            cards = generate_heuristic_fallback_flashcards(clean_text, w_topics, inc_questions, target_count)
            return {
                "cards": cards,
                "provider": "heuristic-fallback",
                "model": None
            }
        raise AIServiceError("We couldn't generate your revision flashcards right now. Please try again.") from exc

    return {
        "cards": cards_data,
        "provider": "gemini",
        "model": model_name
    }
