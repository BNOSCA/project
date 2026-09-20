"""Groq-backed semantic intent parsing."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from groq import Groq
from groq.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ConfigDict, ValidationError

from backend.schemas import Intent
from .normalizer import normalize_value
from .taxonomy import COLOR_ALIASES, FIT_ALIASES, MATERIAL_ALIASES, OCCASION_ALIASES, STYLE_ALIASES

DEFAULT_MODEL = "qwen/qwen3.8-27b"

class LLMUnavailableError(RuntimeError):
    pass

class LLMResponseError(RuntimeError):
    pass

class StrictExtractionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class ExtractedAttributes(StrictExtractionModel):
    styles: list[str]
    colors: list[str]
    fits: list[str]
    materials: list[str]

class ExtractedExcluded(StrictExtractionModel):
    styles: list[str]
    colors: list[str]
    fits: list[str]
    materials: list[str]

class IntentExtraction(StrictExtractionModel):
    occasion: list[str]
    budget_total: int | None
    currency: Literal["TWD"]
    preferred: ExtractedAttributes
    excluded: ExtractedExcluded
    unknown_fields: list[str]
    needs_clarification: bool
    clarifying_question: str | None
    semantic_query: str

class FeedbackPatchExtraction(StrictExtractionModel):
    preferred_styles: list[str]
    preferred_colors: list[str]
    preferred_fits: list[str]
    excluded_colors: list[str]
    excluded_fits: list[str]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    return (_repo_root() / "prompts" / "intent_system_v1.txt").read_text(encoding="utf-8")


def _api_key() -> str:
    key = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
    if not key:
        raise LLMUnavailableError("Set GROQ_API_KEY or LLM_API_KEY")
    return key


def _model_name() -> str:
    return os.getenv("GROQ_MODEL") or os.getenv("LLM_MODEL") or DEFAULT_MODEL


def _timeout_seconds() -> float:
    return float(os.getenv("LLM_TIMEOUT_SECONDS", "8"))


def _call_structured(
    *,
    messages: list[ChatCompletionMessageParam],
    schema_model: type[BaseModel],
    schema_name: str,
) -> dict:
    try:
        client = Groq(api_key=_api_key(), timeout=_timeout_seconds())
        completion = client.chat.completions.create(
            model=_model_name(),
            messages=messages,
            temperature=0.1,
            reasoning_effort="none",
            max_completion_tokens=1200,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema_model.model_json_schema(),
                },
            },
        )
    except Exception as exc:
        raise LLMUnavailableError(f"Groq request failed: {type(exc).__name__}: {exc}") from exc

    try:
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("empty response")
        return json.loads(content)
    except Exception as exc:
        raise LLMResponseError("Groq returned unusable structured output") from exc


def _previous_payload(intent: Intent | None) -> dict | None:
    if intent is None:
        return None
    return intent.model_dump(mode="json", exclude={"session_id"})


def _partition_known(values: list[str], aliases: dict[str, str]) -> tuple[list[str], list[str]]:
    canonical = set(aliases.values())
    known, residual = [], []
    for raw in values:
        normalized = normalize_value(raw, aliases)
        if normalized in canonical:
            if normalized not in known:
                known.append(normalized)
        else:
            cleaned = raw.strip()
            if cleaned and cleaned not in residual:
                residual.append(cleaned)
    return known, residual


def _intent_messages(
    text: str,
    previous_intent: Intent | None,
) -> list[ChatCompletionMessageParam]:
    payload = {"previous_intent": _previous_payload(previous_intent), "new_user_message": text}
    return [
        {"role": "system", "content": load_system_prompt()},
        {"role": "user", "content": "Return the FULL current intent after applying the new message. Output only the schema object.\n\n" + json.dumps(payload, ensure_ascii=False, indent=2)},
    ]


def _feedback_messages(
    text: str,
    current_intent: Intent,
) -> list[ChatCompletionMessageParam]:
    payload = {"current_intent": _previous_payload(current_intent), "feedback_message": text}
    return [
        {"role": "system", "content": load_system_prompt()},
        {"role": "user", "content": "Feedback PATCH task: return ONLY fields explicitly changed by feedback_message; do not repeat unchanged preferences.\n\n" + json.dumps(payload, ensure_ascii=False, indent=2)},
    ]


def _to_shared_intent(extraction: IntentExtraction, *, text: str, previous_intent: Intent | None) -> dict:
    occasions, residual_occasions = _partition_known(extraction.occasion, OCCASION_ALIASES)
    p_styles, residual_styles = _partition_known(extraction.preferred.styles, STYLE_ALIASES)
    p_colors, residual_colors = _partition_known(extraction.preferred.colors, COLOR_ALIASES)
    p_fits, residual_fits = _partition_known(extraction.preferred.fits, FIT_ALIASES)
    p_materials, residual_materials = _partition_known(extraction.preferred.materials, MATERIAL_ALIASES)
    e_colors, residual_e_colors = _partition_known(extraction.excluded.colors, COLOR_ALIASES)
    e_fits, residual_e_fits = _partition_known(extraction.excluded.fits, FIT_ALIASES)
    e_materials, residual_e_materials = _partition_known(extraction.excluded.materials, MATERIAL_ALIASES)

    hard, soft = [], []
    if extraction.budget_total is not None: hard.append("budget_total")
    if e_colors: hard.append("excluded.colors")
    if e_fits: hard.append("excluded.fits")
    if e_materials: hard.append("excluded.materials")
    if p_styles: soft.append("preferred.styles")
    if p_colors: soft.append("preferred.colors")
    if p_fits: soft.append("preferred.fits")
    if p_materials: soft.append("preferred.materials")

    semantic_parts = []
    if extraction.semantic_query.strip():
        semantic_parts.append(extraction.semantic_query.strip())
    for item in residual_occasions + residual_styles + residual_colors + residual_fits + residual_materials + residual_e_colors + residual_e_fits + residual_e_materials:
        if item and item not in semantic_parts:
            semantic_parts.append(item)
    for style in extraction.excluded.styles:
        normalized = normalize_value(style, STYLE_ALIASES) or style
        token = f"避免風格：{normalized}"
        if token not in semantic_parts:
            semantic_parts.append(token)

    conflict = bool(set(p_colors) & set(e_colors) or set(p_fits) & set(e_fits) or set(p_materials) & set(e_materials))
    needs_clarification = extraction.needs_clarification or conflict
    question = extraction.clarifying_question
    if needs_clarification and not question:
        question = "你的需求中有互相衝突的偏好，請確認希望保留哪一項？"

    unknown_fields = list(extraction.unknown_fields)

    if "size" not in unknown_fields:
        unknown_fields.append("size")

    result = {
        "occasion": occasions,
        "budget_total": extraction.budget_total,
        "currency": "TWD",
        "required_categories": previous_intent.required_categories if previous_intent else ["top", "bottom", "shoes"],
        "preferred": {
            "styles": p_styles,
            "colors": p_colors,
            "fits": p_fits,
            "materials": p_materials,
        },
        "excluded": {
            "colors": e_colors,
            "fits": e_fits,
            "materials": e_materials,
        },
        "hard_constraints": hard,
        "soft_constraints": soft,
        "unknown_fields": unknown_fields,
        "needs_clarification": needs_clarification,
        "clarifying_question": question,
        "semantic_query": "；".join(semantic_parts),
        "source_text": text,
    }
    return result


def parse_with_llm(text: str, previous_intent: Intent | None = None) -> dict:
    raw = _call_structured(messages=_intent_messages(text, previous_intent), schema_model=IntentExtraction, schema_name="fashion_intent")
    try:
        extraction = IntentExtraction.model_validate(raw)
    except ValidationError as exc:
        raise LLMResponseError("IntentExtraction validation failed") from exc

    result = _to_shared_intent(extraction, text=text, previous_intent=previous_intent)
    session_id = previous_intent.session_id if previous_intent else "__validation__"
    try:
        validated = Intent.model_validate({"session_id": session_id, **result})
    except ValidationError as exc:
        raise LLMResponseError("Shared Intent validation failed") from exc

    output = validated.model_dump(mode="json")
    output.pop("session_id", None)
    return output


def parse_feedback_with_llm(text: str, current_intent: Intent) -> dict[str, list[str]]:
    raw = _call_structured(messages=_feedback_messages(text, current_intent), schema_model=FeedbackPatchExtraction, schema_name="fashion_feedback_patch")
    try:
        x = FeedbackPatchExtraction.model_validate(raw)
    except ValidationError as exc:
        raise LLMResponseError("FeedbackPatchExtraction validation failed") from exc

    p_styles, _ = _partition_known(x.preferred_styles, STYLE_ALIASES)
    p_colors, _ = _partition_known(x.preferred_colors, COLOR_ALIASES)
    p_fits, _ = _partition_known(x.preferred_fits, FIT_ALIASES)
    e_colors, _ = _partition_known(x.excluded_colors, COLOR_ALIASES)
    e_fits, _ = _partition_known(x.excluded_fits, FIT_ALIASES)

    patch = {}
    if p_styles: patch["preferred.styles"] = p_styles
    if p_colors: patch["preferred.colors"] = p_colors
    if p_fits: patch["preferred.fits"] = p_fits
    if e_colors: patch["excluded.colors"] = e_colors
    if e_fits: patch["excluded.fits"] = e_fits
    return patch

