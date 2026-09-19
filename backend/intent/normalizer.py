"""Normalization helpers for intent extraction."""

from collections.abc import Iterable

from .taxonomy import (
    COLOR_ALIASES,
    FIT_ALIASES,
    MATERIAL_ALIASES,
    OCCASION_ALIASES,
    STYLE_ALIASES,
)


def normalize_value(
    value: str | None,
    aliases: dict[str, str],
) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()

    if not cleaned:
        return None

    lowered = cleaned.lower()

    for alias, canonical in aliases.items():
        if alias.lower() == lowered:
            return canonical

    canonical_values = set(
        aliases.values()
    )

    if lowered in canonical_values:
        return lowered

    return cleaned


def normalize_values(
    values: Iterable[str],
    aliases: dict[str, str],
) -> list[str]:
    result: list[str] = []

    for value in values:
        normalized = normalize_value(
            value,
            aliases,
        )

        if (
            normalized is not None
            and normalized not in result
        ):
            result.append(
                normalized
            )

    return result


def find_all_aliases(
    text: str,
    aliases: dict[str, str],
) -> list[str]:
    """Extract all canonical values mentioned in text."""

    lowered = text.lower()

    result: list[str] = []

    for alias in sorted(
        aliases,
        key=len,
        reverse=True,
    ):
        if alias.lower() not in lowered:
            continue

        canonical = aliases[alias]

        if canonical not in result:
            result.append(
                canonical
            )

    return result


def normalize_styles(
    values: Iterable[str],
) -> list[str]:
    return normalize_values(
        values,
        STYLE_ALIASES,
    )


def normalize_colors(
    values: Iterable[str],
) -> list[str]:
    return normalize_values(
        values,
        COLOR_ALIASES,
    )


def normalize_fits(
    values: Iterable[str],
) -> list[str]:
    return normalize_values(
        values,
        FIT_ALIASES,
    )


def normalize_materials(
    values: Iterable[str],
) -> list[str]:
    return normalize_values(
        values,
        MATERIAL_ALIASES,
    )


def normalize_occasions(
    values: Iterable[str],
) -> list[str]:
    return normalize_values(
        values,
        OCCASION_ALIASES,
    )
