"""Deterministic intent parser used as a safe fallback.

This module intentionally handles only high-confidence rules.
Anything that cannot be safely normalized remains in semantic_query.
"""

from __future__ import annotations

import re
import unicodedata

from backend.schemas import Intent

from .taxonomy import (
    COLOR_ALIASES,
    FIT_ALIASES,
    MATERIAL_ALIASES,
    OCCASION_ALIASES,
    STYLE_ALIASES,
)


NEGATIVE_MARKERS = (
    "不要",
    "不想要",
    "不想",
    "不喜歡",
    "避免",
    "不能",
    "別",
)


CLAUSE_BOUNDARIES = (
    "，",
    ",",
    "。",
    ".",
    "；",
    ";",
    "！",
    "!",
    "？",
    "?",
    "\n",
    "但是",
    "但",
    "可是",
    "不過",
    "改成",
    "換成",
)


CN_DIGITS = {
    "一": 1,
    "二": 2,
    "兩": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def preprocess_text(
    text: str,
) -> str:
    text = unicodedata.normalize(
        "NFKC",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text.strip(),
    )

    text = normalize_budget_notation(
        text,
    )

    return text


def normalize_budget_notation(
    text: str,
) -> str:
    """
    Normalize common budget expressions:

    2k       -> 2000
    2.5k     -> 2500
    3千      -> 3000
    三千     -> 3000
    兩千五   -> 2500
    兩千五百 -> 2500
    """

    def replace_k(
        match: re.Match[str],
    ) -> str:
        number = float(
            match.group(1)
        )

        return str(
            int(number * 1000)
        )

    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*[kK]\b",
        replace_k,
        text,
    )

    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*千",
        replace_k,
        text,
    )

    # 兩千五百 / 三千二百
    def replace_cn_thousand_hundred(
        match: re.Match[str],
    ) -> str:
        thousand = CN_DIGITS[
            match.group(1)
        ]

        hundred = CN_DIGITS[
            match.group(2)
        ]

        return str(
            thousand * 1000
            + hundred * 100
        )

    text = re.sub(
        r"([一二兩三四五六七八九])千"
        r"([一二兩三四五六七八九])百",
        replace_cn_thousand_hundred,
        text,
    )

    # 口語「兩千五」通常表示 2500
    def replace_cn_colloquial(
        match: re.Match[str],
    ) -> str:
        thousand = CN_DIGITS[
            match.group(1)
        ]

        hundred = CN_DIGITS[
            match.group(2)
        ]

        return str(
            thousand * 1000
            + hundred * 100
        )

    text = re.sub(
        r"([一二兩三四五六七八九])千"
        r"([一二兩三四五六七八九])"
        r"(?=\s*(?:元|塊|內|以內|以下|左右|預算|$))",
        replace_cn_colloquial,
        text,
    )

    # 兩千 / 三千
    def replace_cn_thousand(
        match: re.Match[str],
    ) -> str:
        value = CN_DIGITS[
            match.group(1)
        ]

        return str(
            value * 1000
        )

    text = re.sub(
        r"([一二兩三四五六七八九])千",
        replace_cn_thousand,
        text,
    )

    return text


def extract_budget(
    text: str,
) -> int | None:
    patterns = (
        r"(?:預算|budget)"
        r"(?:是|約|大概|大約|差不多)?"
        r"\s*[:：]?\s*(\d{2,7})",

        r"(\d{2,7})\s*"
        r"(?:元|塊)?\s*"
        r"(?:以內|以下|內)",

        r"(?:不超過|最多|上限)"
        r"\s*(\d{2,7})",
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            return int(
                match.group(1)
            )

    return None


def is_negative_context(
    text: str,
    start_index: int,
) -> bool:
    """
    Determine whether the entity at start_index is negated.

    Negation is scoped to the current local clause instead of a fixed
    character window. This prevents a negative marker in an earlier clause
    from leaking into a later positive preference.

    Examples:
        不喜歡白色，想要黑色
        white -> negative
        black -> positive

        不要白色但想要黑色
        white -> negative
        black -> positive
    """

    prefix = text[:start_index]

    clause_start = 0

    for boundary in CLAUSE_BOUNDARIES:
        boundary_index = prefix.rfind(
            boundary
        )

        if boundary_index >= 0:
            candidate_start = (
                boundary_index
                + len(boundary)
            )

            clause_start = max(
                clause_start,
                candidate_start,
            )

    local_context = prefix[
        clause_start:
    ]

    # Keep the context local even when the clause is unusually long.
    local_context = local_context[-20:]

    return any(
        marker in local_context
        for marker in NEGATIVE_MARKERS
    )


def split_alias_preferences(
    text: str,
    aliases: dict[str, str],
) -> tuple[list[str], list[str]]:
    """
    Return:
        positive canonical values,
        explicitly negative canonical values.
    """

    positive: list[str] = []
    negative: list[str] = []

    lowered = text.lower()

    for alias in sorted(
        aliases,
        key=len,
        reverse=True,
    ):
        pattern = re.escape(
            alias.lower()
        )

        for match in re.finditer(
            pattern,
            lowered,
        ):
            canonical = aliases[
                alias
            ]

            target = (
                negative
                if is_negative_context(
                    lowered,
                    match.start(),
                )
                else positive
            )

            if canonical not in target:
                target.append(
                    canonical
                )

    return positive, negative


def add_unique(
    target: list[str],
    values: list[str],
) -> None:
    for value in values:
        if value not in target:
            target.append(
                value
            )


def remove_values(
    target: list[str],
    values: list[str],
) -> None:
    for value in values:
        while value in target:
            target.remove(
                value
            )


def ensure_constraint(
    constraints: list[str],
    path: str,
    enabled: bool,
) -> None:
    if enabled:
        if path not in constraints:
            constraints.append(
                path
            )

    elif path in constraints:
        constraints.remove(
            path
        )


def make_empty_intent_data() -> dict:
    return {
        "occasion": [],
        "budget_total": None,
        "currency": "TWD",

        "required_categories": [
            "top",
            "bottom",
            "shoes",
        ],

        "preferred": {
            "styles": [],
            "colors": [],
            "fits": [],
            "materials": [],
        },

        "excluded": {
            "colors": [],
            "fits": [],
            "materials": [],
        },

        "hard_constraints": [],
        "soft_constraints": [],

        "unknown_fields": [
            "size",
        ],

        "needs_clarification": False,
        "clarifying_question": None,

        "semantic_query": "",
        "source_text": "",
    }


def parse_fallback_intent(
    text: str,
    previous_intent: Intent | None = None,
) -> dict:
    normalized_text = preprocess_text(
        text
    )

    if previous_intent is None:
        result = (
            make_empty_intent_data()
        )

    else:
        result = (
            previous_intent.model_dump(
                mode="json"
            )
        )

        # E's orchestration layer owns session_id.
        result.pop(
            "session_id",
            None,
        )

    budget = extract_budget(
        normalized_text
    )

    occasions, _ = (
        split_alias_preferences(
            normalized_text,
            OCCASION_ALIASES,
        )
    )

    preferred_styles, excluded_styles = (
        split_alias_preferences(
            normalized_text,
            STYLE_ALIASES,
        )
    )

    preferred_colors, excluded_colors = (
        split_alias_preferences(
            normalized_text,
            COLOR_ALIASES,
        )
    )

    preferred_fits, excluded_fits = (
        split_alias_preferences(
            normalized_text,
            FIT_ALIASES,
        )
    )

    preferred_materials, excluded_materials = (
        split_alias_preferences(
            normalized_text,
            MATERIAL_ALIASES,
        )
    )

    # --------------------------------------------------------
    # Multi-turn patch semantics
    # --------------------------------------------------------

    if occasions:
        result[
            "occasion"
        ] = occasions

    if budget is not None:
        result[
            "budget_total"
        ] = budget

    preferred = result[
        "preferred"
    ]

    excluded = result[
        "excluded"
    ]

    same_turn_color_conflict = (
        set(preferred_colors)
        & set(excluded_colors)
    )

    same_turn_fit_conflict = (
        set(preferred_fits)
        & set(excluded_fits)
    )

    same_turn_material_conflict = (
        set(preferred_materials)
        & set(excluded_materials)
    )

    # New explicit preference overrides an old exclusion.
    remove_values(
        excluded["colors"],
        [
            value
            for value
            in preferred_colors
            if value
            not in same_turn_color_conflict
        ],
    )

    remove_values(
        excluded["fits"],
        [
            value
            for value
            in preferred_fits
            if value
            not in same_turn_fit_conflict
        ],
    )

    remove_values(
        excluded["materials"],
        [
            value
            for value
            in preferred_materials
            if value
            not in same_turn_material_conflict
        ],
    )

    # New explicit exclusion overrides an old preference.
    remove_values(
        preferred["colors"],
        [
            value
            for value
            in excluded_colors
            if value
            not in same_turn_color_conflict
        ],
    )

    remove_values(
        preferred["fits"],
        [
            value
            for value
            in excluded_fits
            if value
            not in same_turn_fit_conflict
        ],
    )

    remove_values(
        preferred["materials"],
        [
            value
            for value
            in excluded_materials
            if value
            not in same_turn_material_conflict
        ],
    )

    add_unique(
        preferred["styles"],
        preferred_styles,
    )

    add_unique(
        preferred["colors"],
        preferred_colors,
    )

    add_unique(
        preferred["fits"],
        preferred_fits,
    )

    add_unique(
        preferred["materials"],
        preferred_materials,
    )

    add_unique(
        excluded["colors"],
        excluded_colors,
    )

    add_unique(
        excluded["fits"],
        excluded_fits,
    )

    add_unique(
        excluded["materials"],
        excluded_materials,
    )

    # --------------------------------------------------------
    # Hard / soft constraint metadata
    # --------------------------------------------------------

    ensure_constraint(
        result["hard_constraints"],
        "budget_total",
        result[
            "budget_total"
        ] is not None,
    )

    ensure_constraint(
        result["hard_constraints"],
        "excluded.colors",
        bool(
            excluded["colors"]
        ),
    )

    ensure_constraint(
        result["hard_constraints"],
        "excluded.fits",
        bool(
            excluded["fits"]
        ),
    )

    ensure_constraint(
        result["hard_constraints"],
        "excluded.materials",
        bool(
            excluded["materials"]
        ),
    )

    ensure_constraint(
        result["soft_constraints"],
        "preferred.styles",
        bool(
            preferred["styles"]
        ),
    )

    ensure_constraint(
        result["soft_constraints"],
        "preferred.colors",
        bool(
            preferred["colors"]
        ),
    )

    ensure_constraint(
        result["soft_constraints"],
        "preferred.fits",
        bool(
            preferred["fits"]
        ),
    )

    ensure_constraint(
        result["soft_constraints"],
        "preferred.materials",
        bool(
            preferred["materials"]
        ),
    )

    # --------------------------------------------------------
    # Clarification
    # --------------------------------------------------------

    conflict_messages: list[str] = []

    if same_turn_color_conflict:
        conflict_messages.append(
            "顏色"
        )

    if same_turn_fit_conflict:
        conflict_messages.append(
            "版型"
        )

    if same_turn_material_conflict:
        conflict_messages.append(
            "材質"
        )

    if conflict_messages:
        result[
            "needs_clarification"
        ] = True

        result[
            "clarifying_question"
        ] = (
            "你的需求中同時包含互相衝突的"
            + "、".join(
                conflict_messages
            )
            + "偏好，請確認要保留哪一個？"
        )

    else:
        result[
            "needs_clarification"
        ] = False

        result[
            "clarifying_question"
        ] = None

    # --------------------------------------------------------
    # semantic_query
    # --------------------------------------------------------

    # excluded.styles is not present in the shared Intent schema.
    # Preserve that meaning instead of inventing a new field.
    semantic_parts: list[str] = []

    previous_semantic = result.get(
        "semantic_query",
        "",
    ).strip()

    if previous_semantic:
        semantic_parts.append(
            previous_semantic
        )

    semantic_parts.append(
        text.strip()
    )

    if excluded_styles:
        semantic_parts.append(
            "避免風格："
            + "、".join(
                excluded_styles
            )
        )

    deduplicated_parts: list[str] = []

    for part in semantic_parts:
        if (
            part
            and part
            not in deduplicated_parts
        ):
            deduplicated_parts.append(
                part
            )

    result[
        "semantic_query"
    ] = "；".join(
        deduplicated_parts
    )

    result[
        "source_text"
    ] = text

    return result

