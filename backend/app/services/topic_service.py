"""Topic extraction and weak-topic analysis for revision tests."""
import re
from typing import Any, Dict, List, Optional
from backend.app.models.schemas import WeakTopicItem, QuestionReviewItem

COMMON_STOP_WORDS = {
    "the", "of", "and", "a", "to", "in", "is", "you", "that", "it", "he", "was",
    "for", "on", "are", "as", "with", "his", "they", "i", "at", "be", "this",
    "have", "from", "or", "one", "had", "by", "word", "but", "not", "what",
    "all", "were", "we", "when", "your", "can", "said", "there", "use", "an",
    "each", "which", "she", "do", "how", "their", "if", "will", "up", "other",
    "about", "out", "many", "then", "them", "these", "so", "some", "her", "would",
    "make", "like", "him", "into", "time", "has", "look", "two", "more", "write",
    "go", "see", "number", "no", "way", "could", "people", "my", "than", "first",
    "water", "been", "call", "who", "oil", "its", "now", "find", "long", "down",
    "day", "did", "get", "come", "made", "may", "part", "according", "study",
    "material", "statement", "accurately", "reflects", "concept", "following",
    "correct", "primary", "function", "most", "such", "cells", "cellular",
    "question", "options", "option", "review", "fallback", "true", "false",
    "described", "process", "defined", "refers", "known", "conducts", "carries",
    "produces", "occurs", "responsible", "responsible", "eukaryotic", "prokaryotic"
}


def extract_topic_from_question(
    question: str = "",
    explanation: str = "",
    explicit_topic: Optional[str] = None
) -> str:
    """
    Extract a concise, standardized topic name for a question.
    Prioritizes explicit_topic if present.
    Otherwise derives from explanation / question text.
    """
    if explicit_topic and explicit_topic.strip():
        clean_exp = explicit_topic.strip()
        # Clean leading numbering like "1. Topic" or brackets "[Topic]"
        clean_exp = re.sub(r"^[0-9]+[\.\)\s\-]+", "", clean_exp)
        clean_exp = clean_exp.strip("[](){}:.,; ")
        if len(clean_exp) >= 3:
            return clean_exp.title()

    combined_text = f"{question} {explanation}".strip()

    # Check for prefix patterns like "Chapter X: Topic Name" or "Topic: Name"
    prefix_match = re.search(
        r"(?:Chapter\s+\d+|Topic|Section|Module)\s*[:\-]\s*([A-Za-z0-9\s]{3,40})",
        combined_text,
        re.IGNORECASE
    )
    if prefix_match:
        topic_cand = prefix_match.group(1).strip()
        if len(topic_cand) >= 3:
            return topic_cand.title()

    # Look for quoted subject concept like: 'Operating Systems Memory Management Revision'
    quoted_match = re.search(r"['\"]([A-Za-z0-9\s\-]{4,45})['\"]", combined_text)
    if quoted_match:
        cand = quoted_match.group(1).strip()
        # If contains colon or chapter, take the main title
        if ":" in cand:
            cand = cand.split(":")[-1].strip()
        words = [w for w in re.findall(r"[A-Za-z0-9]+", cand) if w.lower() not in COMMON_STOP_WORDS]
        if words:
            return " ".join(words[:3]).title()

    # Extract high-frequency significant nouns / keywords from question and explanation
    words = re.findall(r"\b[A-Za-z]{3,}\b", combined_text)
    filtered = [w for w in words if w.lower() not in COMMON_STOP_WORDS]

    if not filtered:
        return "General Core Concept"

    # Count occurrences
    freq: Dict[str, int] = {}
    ordered_unique: List[str] = []
    for w in filtered:
        norm = w.lower()
        if norm not in freq:
            freq[norm] = 0
            ordered_unique.append(w.capitalize())
        freq[norm] += 1

    # Sort by frequency, preserving initial appearance
    sorted_keywords = sorted(ordered_unique, key=lambda k: freq[k.lower()], reverse=True)

    if len(sorted_keywords) >= 2:
        return f"{sorted_keywords[0]} {sorted_keywords[1]}"
    return sorted_keywords[0]


def analyze_weak_topics(reviews: List[QuestionReviewItem]) -> List[WeakTopicItem]:
    """
    Analyze student performance per topic across questions.
    Returns prioritized WeakTopicItem list.
    """
    if not reviews:
        return []

    # Group by topic
    topic_map: Dict[str, Dict[str, Any]] = {}

    for q in reviews:
        topic_name = q.topic or extract_topic_from_question(
            question=q.question,
            explanation=q.explanation
        )

        if topic_name not in topic_map:
            topic_map[topic_name] = {
                "total": 0,
                "correct": 0,
                "incorrect": 0,
                "unanswered": 0,
                "questions": []
            }

        topic_map[topic_name]["total"] += 1
        topic_map[topic_name]["questions"].append(q)

        if q.is_correct:
            topic_map[topic_name]["correct"] += 1
        elif q.is_answered:
            topic_map[topic_name]["incorrect"] += 1
        else:
            topic_map[topic_name]["unanswered"] += 1

    weak_topics: List[WeakTopicItem] = []

    for topic_name, data in topic_map.items():
        total = data["total"]
        incorrect = data["incorrect"]
        unanswered = data["unanswered"]
        correct = data["correct"]

        # Only evaluate weakness if there are missed or skipped questions
        if incorrect == 0 and unanswered == 0:
            continue

        accuracy_pct = round((correct / total) * 100.0, 1)

        # Determine weakness indicator & priority
        # Requirement: Do not classify a topic as weak solely because of one unanswered question without explaining limited evidence.
        if total == 1 and unanswered == 1 and incorrect == 0:
            weakness_indicator = "Needs Attention"
            priority = "low"
            reason = (
                f"Topic '{topic_name}' had 1 question left unanswered. "
                "Because no questions were attempted on this concept, evidence is limited, but a quick review is advised."
            )
            recommendation = f"Review the fundamental definition of {topic_name} and attempt practice questions."
        elif accuracy_pct == 0.0:
            if total >= 2 or incorrect >= 1:
                weakness_indicator = "Critical Weakness"
                priority = "high"
                reason = (
                    f"0% accuracy across {total} question(s) on '{topic_name}' "
                    f"({incorrect} incorrect, {unanswered} unanswered). Significant knowledge gap identified."
                )
                recommendation = f"High Priority: Re-read the primary study notes and review explanations for {topic_name}."
            else:
                weakness_indicator = "Moderate Weakness"
                priority = "medium"
                reason = f"Missed 1 question on '{topic_name}'. Needs reinforcement before the exam."
                recommendation = f"Review the correct answer and core principle for {topic_name}."
        elif accuracy_pct < 60.0:
            weakness_indicator = "Moderate Weakness"
            priority = "medium"
            reason = (
                f"Scored {accuracy_pct}% on '{topic_name}' ({incorrect} missed, {unanswered} skipped out of {total}). "
                "Understanding is inconsistent."
            )
            recommendation = f"Targeted Review: Review missed questions and key mechanisms for {topic_name}."
        else:
            weakness_indicator = "Needs Attention"
            priority = "low"
            reason = (
                f"Minor gap on '{topic_name}': {incorrect} question(s) missed out of {total} "
                f"({accuracy_pct}% accuracy)."
            )
            recommendation = f"Quick Polish: Skim the explanation for the missed {topic_name} question."

        weak_topics.append(
            WeakTopicItem(
                topic=topic_name,
                total_questions=total,
                incorrect_count=incorrect,
                unanswered_count=unanswered,
                accuracy_percentage=accuracy_pct,
                weakness_indicator=weakness_indicator,
                priority=priority,
                reason=reason,
                recommendation=recommendation
            )
        )

    # Sort prioritized: high first, then medium, then low; secondary by incorrect_count descending
    priority_order = {"high": 1, "medium": 2, "low": 3}
    weak_topics.sort(
        key=lambda item: (priority_order.get(item.priority, 4), -item.incorrect_count, -item.unanswered_count)
    )

    return weak_topics
