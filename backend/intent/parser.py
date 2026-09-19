"""Public orchestration boundary for the B intent module."""
from __future__ import annotations

from pydantic import ValidationError
from backend.schemas import Intent
from .fallback import parse_fallback_intent
from .llm import LLMResponseError, LLMUnavailableError, parse_feedback_with_llm, parse_with_llm


def parse_intent(text: str, previous_intent: Intent | None = None) -> dict:
    if not text.strip():
        raise ValueError("intent text cannot be empty")
    try:
        return parse_with_llm(text=text, previous_intent=previous_intent)
    except (LLMUnavailableError, LLMResponseError, ValidationError):
        return parse_fallback_intent(text=text, previous_intent=previous_intent)


def _fallback_feedback_patch(text: str) -> dict[str, list[str]]:
    parsed = parse_fallback_intent(text=text, previous_intent=None)
    preferred, excluded = parsed["preferred"], parsed["excluded"]
    patch = {}
    if preferred["styles"]: patch["preferred.styles"] = preferred["styles"]
    if preferred["colors"]: patch["preferred.colors"] = preferred["colors"]
    if preferred["fits"]: patch["preferred.fits"] = preferred["fits"]
    if excluded["colors"]: patch["excluded.colors"] = excluded["colors"]
    if excluded["fits"]: patch["excluded.fits"] = excluded["fits"]
    return patch


def parse_feedback(text: str, current_intent: Intent) -> dict[str, list[str]]:
    if not text.strip():
        raise ValueError("feedback text cannot be empty")
    try:
        return parse_feedback_with_llm(text=text, current_intent=current_intent)
    except (LLMUnavailableError, LLMResponseError, ValidationError):
        return _fallback_feedback_patch(text)


