from pathlib import Path

import pytest

from backend.db import EventStore
from backend.post_trends import parse_google_trends_csv


def test_parse_google_trends_tw_wide_export(tmp_path: Path):
    csv_path = tmp_path / "multiTimeline.csv"
    csv_path.write_text(
        "類別: 所有類別\n"
        "天,日系穿搭: (台灣),黑色穿搭: (台灣),未知穿搭: (台灣)\n"
        "2026-09-17,80,25,50\n"
        "2026-09-18,100,<1,—\n",
        encoding="utf-8",
    )

    signals, unmapped = parse_google_trends_csv(
        csv_path,
        {"日系穿搭": "style:japanese", "黑色穿搭": "color:black"},
    )

    assert len(signals) == 4
    assert signals[0].geo == "TW"
    assert signals[0].attribute == "style:japanese"
    assert signals[-1].raw_score == 0.5
    assert unmapped == ["未知穿搭"]


def test_sqlite_trend_upsert_and_dimension_normalization(tmp_path: Path):
    store = EventStore(tmp_path / "events.db")
    csv_path = tmp_path / "trends.csv"
    csv_path.write_text(
        "date,keyword,score,geo\n"
        "2026-09-18,日系穿搭,80,TW\n"
        "2026-09-18,街頭穿搭,40,TW\n"
        "2026-09-18,黑色穿搭,20,TW\n",
        encoding="utf-8",
    )
    mapping = {
        "日系穿搭": "style:japanese",
        "街頭穿搭": "style:street",
        "黑色穿搭": "color:black",
    }
    signals, _ = parse_google_trends_csv(csv_path, mapping)

    assert store.upsert_trend_signals(signals) == 3
    assert store.upsert_trend_signals(signals) == 3
    scores = store.trend_scores()

    assert scores["style:japanese"] == pytest.approx(1.0)
    assert scores["style:street"] == pytest.approx(0.5)
    assert scores["color:black"] == pytest.approx(1.0)
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM external_trend_signals").fetchone()[0] == 3
