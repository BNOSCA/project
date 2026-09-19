from backend.intent import parser
from backend.intent.llm import LLMUnavailableError
from backend.schemas import Intent


def _intent() -> Intent:
    return Intent.model_validate({
        "session_id": "test-session",
        "occasion": [],
        "budget_total": None,
        "currency": "TWD",
        "required_categories": ["top", "bottom", "shoes"],
        "preferred": {"styles": [], "colors": [], "fits": [], "materials": []},
        "excluded": {"colors": [], "fits": [], "materials": []},
        "hard_constraints": [],
        "soft_constraints": [],
        "unknown_fields": [],
        "needs_clarification": False,
        "clarifying_question": None,
        "semantic_query": "",
        "source_text": "",
    })


def test_parser_prefers_llm(monkeypatch):
    expected = {"ok": "llm"}
    monkeypatch.setattr(parser, "parse_with_llm", lambda **kwargs: expected)
    monkeypatch.setattr(parser, "parse_fallback_intent", lambda **kwargs: (_ for _ in ()).throw(AssertionError("fallback should not run")))
    assert parser.parse_intent("想有電影男主角的感覺") == expected


def test_parser_falls_back(monkeypatch):
    monkeypatch.setattr(parser, "parse_with_llm", lambda **kwargs: (_ for _ in ()).throw(LLMUnavailableError("offline")))
    monkeypatch.setattr(parser, "parse_fallback_intent", lambda **kwargs: {"ok": "fallback"})
    assert parser.parse_intent("日系寬鬆") == {"ok": "fallback"}


def test_feedback_prefers_llm(monkeypatch):
    monkeypatch.setattr(parser, "parse_feedback_with_llm", lambda **kwargs: {"excluded.colors": ["white"], "preferred.colors": ["black"]})
    assert parser.parse_feedback("不要白色，想要黑色", _intent()) == {"excluded.colors": ["white"], "preferred.colors": ["black"]}


