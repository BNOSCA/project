"""Google Trends CSV ingestion for post-feed ranking."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from .schemas import ExternalTrendSignal


DATE_HEADERS = {"day", "week", "month", "year", "日期", "天", "日", "週", "月", "年"}


def load_keyword_mapping(path: str | Path) -> dict[str, str]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    for keyword, attribute in raw.items():
        value = str(attribute).strip().lower()
        if ":" not in value:
            raise ValueError(f"invalid trend mapping for {keyword}: {value}")
        mapping[str(keyword).strip()] = value
    return mapping


def _score(value: str) -> float | None:
    cleaned = value.strip().replace("%", "")
    if not cleaned or cleaned in {"—", "-"}:
        return None
    if cleaned.startswith("<"):
        return 0.5
    try:
        return max(0.0, min(100.0, float(cleaned)))
    except ValueError:
        return None


def _keyword(header: str) -> str:
    return re.sub(r"\s*:\s*\([^)]*\)\s*$", "", header).strip()


def parse_google_trends_csv(
    csv_path: str | Path,
    mapping: dict[str, str],
    geo: str = "TW",
) -> tuple[list[ExternalTrendSignal], list[str]]:
    """Parse an official wide export or date/keyword/score long-format CSV."""
    rows = list(csv.reader(Path(csv_path).read_text(encoding="utf-8-sig").splitlines()))
    header_index = next((
        index for index, row in enumerate(rows)
        if row and (
            row[0].strip().lower() in DATE_HEADERS
            or {cell.strip().lower() for cell in row} >= {"date", "keyword", "score"}
        )
    ), None)
    if header_index is None:
        raise ValueError("Google Trends CSV header was not found")

    header = [cell.strip() for cell in rows[header_index]]
    lower = [cell.lower() for cell in header]
    signals: list[ExternalTrendSignal] = []
    unmapped: set[str] = set()

    if {"date", "keyword", "score"}.issubset(lower):
        positions = {name: lower.index(name) for name in ("date", "keyword", "score")}
        geo_position = lower.index("geo") if "geo" in lower else None
        attribute_position = lower.index("attribute") if "attribute" in lower else None
        for row in rows[header_index + 1:]:
            if len(row) <= max(positions.values()):
                continue
            keyword = row[positions["keyword"]].strip()
            raw_score = _score(row[positions["score"]])
            attribute = (
                row[attribute_position].strip().lower()
                if attribute_position is not None and len(row) > attribute_position
                else mapping.get(keyword)
            )
            if raw_score is None or not keyword:
                continue
            if not attribute:
                unmapped.add(keyword)
                continue
            date = row[positions["date"]].strip()
            signals.append(ExternalTrendSignal(
                keyword=keyword,
                attribute=attribute,
                geo=row[geo_position].strip() if geo_position is not None and len(row) > geo_position and row[geo_position].strip() else geo,
                period_start=date,
                period_end=date,
                raw_score=raw_score,
                normalized_score=raw_score / 100,
            ))
    else:
        keywords = [_keyword(cell) for cell in header[1:]]
        for row in rows[header_index + 1:]:
            if not row or not row[0].strip():
                continue
            date = row[0].strip()
            for offset, keyword in enumerate(keywords, 1):
                if not keyword or offset >= len(row):
                    continue
                raw_score = _score(row[offset])
                if raw_score is None:
                    continue
                attribute = mapping.get(keyword)
                if not attribute:
                    unmapped.add(keyword)
                    continue
                signals.append(ExternalTrendSignal(
                    keyword=keyword,
                    attribute=attribute,
                    geo=geo,
                    period_start=date,
                    period_end=date,
                    raw_score=raw_score,
                    normalized_score=raw_score / 100,
                ))
    return signals, sorted(unmapped)
