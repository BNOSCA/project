from backend.intent import (
    parse_feedback,
    parse_intent,
)

from backend.schemas import (
    Intent,
)


def as_intent(
    parsed: dict,
) -> Intent:
    """
    Simulate E's integration layer adding session_id.
    """

    return Intent.model_validate(
        {
            "session_id":
                "test-session",
            **parsed,
        }
    )


def test_draft2_demo_query():
    parsed = parse_intent(
        "週末想戶外走走，"
        "整套預算3000元，"
        "想要日系寬鬆，"
        "不要太貼身。"
    )

    intent = as_intent(
        parsed
    )

    assert (
        intent.budget_total
        == 3000
    )

    assert (
        "outdoor"
        in intent.occasion
    )

    assert (
        "japanese"
        in intent.preferred.styles
    )

    assert (
        "relaxed"
        in intent.preferred.fits
    )

    assert (
        "fitted"
        in intent.excluded.fits
    )

    assert (
        "budget_total"
        in intent.hard_constraints
    )

    assert (
        "excluded.fits"
        in intent.hard_constraints
    )

    assert (
        "preferred.styles"
        in intent.soft_constraints
    )


def test_chinese_budget():
    parsed = parse_intent(
        "想找日系休閒穿搭，"
        "預算兩千內，"
        "適合平常穿。"
    )

    intent = as_intent(
        parsed
    )

    assert (
        intent.budget_total
        == 2000
    )

    assert (
        "japanese"
        in intent.preferred.styles
    )


def test_k_budget():
    parsed = parse_intent(
        "面試穿搭，預算2.5k"
    )

    intent = as_intent(
        parsed
    )

    assert (
        intent.budget_total
        == 2500
    )

    assert (
        "interview"
        in intent.occasion
    )


def test_negative_color():
    parsed = parse_intent(
        "週末約會想穿韓系，"
        "不喜歡白色"
    )

    intent = as_intent(
        parsed
    )

    assert (
        "date"
        in intent.occasion
    )

    assert (
        "korean"
        in intent.preferred.styles
    )

    assert (
        "white"
        in intent.excluded.colors
    )

    assert (
        "excluded.colors"
        in intent.hard_constraints
    )


def test_unknown_information_is_not_guessed():
    parsed = parse_intent(
        "想找一套簡約穿搭"
    )

    intent = as_intent(
        parsed
    )

    assert (
        intent.budget_total
        is None
    )

    assert (
        "minimal"
        in intent.preferred.styles
    )

    assert (
        "size"
        in intent.unknown_fields
    )


def test_previous_intent_is_preserved():
    first = as_intent(
        parse_intent(
            "想找日系穿搭，"
            "預算3000"
        )
    )

    second = as_intent(
        parse_intent(
            "改成寬鬆一點",
            first,
        )
    )

    assert (
        second.budget_total
        == 3000
    )

    assert (
        "japanese"
        in second.preferred.styles
    )

    assert (
        "relaxed"
        in second.preferred.fits
    )


def test_new_exclusion_overrides_old_preference():
    first = as_intent(
        parse_intent(
            "我喜歡白色的簡約穿搭"
        )
    )

    assert (
        "white"
        in first.preferred.colors
    )

    second = as_intent(
        parse_intent(
            "改一下，我不要白色",
            first,
        )
    )

    assert (
        "white"
        not in second.preferred.colors
    )

    assert (
        "white"
        in second.excluded.colors
    )


def test_feedback_patch():
    current = as_intent(
        parse_intent(
            "想找日系穿搭"
        )
    )

    patch = parse_feedback(
        "不喜歡白色，想要黑色",
        current,
    )

    assert (
        patch[
            "excluded.colors"
        ]
        == ["white"]
    )

    assert (
        patch[
            "preferred.colors"
        ]
        == ["black"]
    )


def test_same_turn_conflict_requires_clarification():
    parsed = parse_intent(
        "我喜歡白色，"
        "但不要白色"
    )

    intent = as_intent(
        parsed
    )

    assert (
        intent.needs_clarification
        is True
    )

    assert (
        intent.clarifying_question
        is not None
    )


def test_result_respects_shared_schema():
    parsed = parse_intent(
        "預算3000，"
        "日系寬鬆，"
        "不要米色"
    )

    intent = as_intent(
        parsed
    )

    assert (
        isinstance(
            intent,
            Intent,
        )
    )

    assert (
        intent.currency
        == "TWD"
    )

    assert (
        intent.required_categories
        == [
            "top",
            "bottom",
            "shoes",
        ]
    )
