"""Small SQLite store for idempotent mock events and session state."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class EventStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    target_type TEXT,
                    target_id TEXT,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS session_profiles (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    profile_json TEXT NOT NULL,
                    intent_json TEXT
                );
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS external_trend_signals (
                    trend_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    keyword TEXT NOT NULL,
                    attribute TEXT NOT NULL,
                    geo TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    raw_score REAL NOT NULL,
                    normalized_score REAL NOT NULL CHECK(normalized_score >= 0 AND normalized_score <= 1),
                    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source, keyword, geo, period_start, period_end)
                );
                CREATE INDEX IF NOT EXISTS idx_external_trends_lookup
                ON external_trend_signals(source, geo, attribute, period_end);
                CREATE INDEX IF NOT EXISTS idx_events_user_type_target
                ON events(user_id, event_type, target_id);
            """)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        return db

    def insert_event(self, event: dict) -> bool:
        with self.connect() as db:
            cur = db.execute(
                "INSERT OR IGNORE INTO events (event_id, session_id, user_id, event_type, target_type, target_id, payload) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (event["event_id"], event["session_id"], event["user_id"], event["event_type"], event.get("target_type"), event.get("target_id"), json.dumps(event, ensure_ascii=False, default=str)),
            )
            return cur.rowcount == 1

    def has_event_id(self, event_id: str) -> bool:
        with self.connect() as db:
            return db.execute("SELECT 1 FROM events WHERE event_id = ?", (event_id,)).fetchone() is not None

    def has_qualifying_dwell(self, session_id: str, target_type: str, target_id: str) -> bool:
        with self.connect() as db:
            rows = db.execute(
                "SELECT payload FROM events WHERE session_id = ? AND event_type = 'dwell' AND target_type = ? AND target_id = ?",
                (session_id, target_type, target_id),
            ).fetchall()
            return any((event := json.loads(row["payload"])).get("is_foreground", True) and
                       (event.get("dwell_ms") or 0) >= 2000 for row in rows)

    def list_events(self, session_id: str, user_id: str, limit: int = 500) -> list[dict]:
        """Return the stored session events that feed ranking actually consumes."""
        with self.connect() as db:
            rows = db.execute(
                """SELECT payload FROM events
                WHERE session_id = ? AND user_id = ?
                ORDER BY created_at ASC LIMIT ?""",
                (session_id, user_id, limit),
            ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def list_user_events(self, user_id: str, limit: int = 5000) -> list[dict]:
        """Return cross-session events for account-level ranking and exposure history."""
        with self.connect() as db:
            rows = db.execute(
                """SELECT payload FROM events
                WHERE user_id = ?
                ORDER BY created_at ASC LIMIT ?""",
                (user_id, limit),
            ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def get_profile(self, session_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT profile_json FROM session_profiles WHERE session_id = ?", (session_id,)).fetchone()
            return json.loads(row["profile_json"]) if row else None

    def get_user_profile(self, user_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT profile_json FROM user_profiles WHERE user_id = ?", (user_id,)
            ).fetchone()
            return json.loads(row["profile_json"]) if row else None

    def save_user_profile(self, user_id: str, profile: dict) -> None:
        with self.connect() as db:
            db.execute(
                """INSERT INTO user_profiles(user_id, profile_json) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    profile_json=excluded.profile_json, updated_at=CURRENT_TIMESTAMP""",
                (user_id, json.dumps(profile, ensure_ascii=False, default=str)),
            )

    def save_profile(self, session_id: str, user_id: str, profile: dict) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO session_profiles(session_id, user_id, profile_json) VALUES (?, ?, ?) ON CONFLICT(session_id) DO UPDATE SET user_id=excluded.user_id, profile_json=excluded.profile_json",
                (session_id, user_id, json.dumps(profile, ensure_ascii=False, default=str)),
            )

    def get_intent(self, session_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT intent_json FROM session_profiles WHERE session_id = ?", (session_id,)).fetchone()
            return json.loads(row["intent_json"]) if row and row["intent_json"] else None

    def save_intent(self, session_id: str, user_id: str, intent: dict) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO session_profiles(session_id, user_id, profile_json, intent_json) VALUES (?, ?, '{}', ?) ON CONFLICT(session_id) DO UPDATE SET intent_json=excluded.intent_json",
                (session_id, user_id, json.dumps(intent, ensure_ascii=False, default=str)),
            )

    def reset(self, session_id: str) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM events WHERE session_id = ?", (session_id,))
            db.execute("DELETE FROM session_profiles WHERE session_id = ?", (session_id,))

    def upsert_trend_signals(self, signals: list[dict]) -> int:
        with self.connect() as db:
            for signal in signals:
                signal = signal.model_dump(mode="json") if hasattr(signal, "model_dump") else signal
                db.execute(
                    """INSERT INTO external_trend_signals
                    (source, keyword, attribute, geo, period_start, period_end, raw_score, normalized_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source, keyword, geo, period_start, period_end) DO UPDATE SET
                    attribute=excluded.attribute, raw_score=excluded.raw_score,
                    normalized_score=excluded.normalized_score, imported_at=CURRENT_TIMESTAMP""",
                    (
                        signal["source"], signal["keyword"], signal["attribute"], signal["geo"],
                        signal["period_start"], signal["period_end"], signal["raw_score"],
                        signal["normalized_score"],
                    ),
                )
        return len(signals)

    def trend_scores(self, geo: str = "TW", source: str = "google_trends") -> dict[str, float]:
        """Average the latest 14 points and normalize within each attribute dimension."""
        with self.connect() as db:
            rows = db.execute(
                """WITH ranked AS (
                    SELECT attribute, keyword, normalized_score,
                           ROW_NUMBER() OVER (
                               PARTITION BY source, geo, keyword ORDER BY period_end DESC
                           ) AS recency_rank
                    FROM external_trend_signals WHERE geo=? AND source=?
                ), keyword_averages AS (
                    SELECT attribute, keyword, AVG(normalized_score) AS recent_average
                    FROM ranked WHERE recency_rank <= 14 GROUP BY attribute, keyword
                )
                SELECT attribute, MAX(recent_average) AS score
                FROM keyword_averages GROUP BY attribute""",
                (geo, source),
            ).fetchall()
        raw = {row["attribute"]: float(row["score"]) for row in rows}
        ceilings: dict[str, float] = {}
        for attribute, score in raw.items():
            dimension = attribute.split(":", 1)[0]
            ceilings[dimension] = max(ceilings.get(dimension, 0.0), score)
        return {
            attribute: score / ceilings[attribute.split(":", 1)[0]]
            if ceilings[attribute.split(":", 1)[0]] else 0.0
            for attribute, score in raw.items()
        }

    def insights(self) -> dict:
        with self.connect() as db:
            rows = db.execute("SELECT event_type, COUNT(*) AS count FROM events GROUP BY event_type").fetchall()
            bounds = db.execute("SELECT MIN(created_at) AS start, MAX(created_at) AS end, COUNT(DISTINCT session_id) AS sample_size FROM events").fetchone()
            return {
                "sample_size": bounds["sample_size"],
                "time_range": {"start": bounds["start"], "end": bounds["end"]},
                "source_type": "demo",
                "event_counts": {row["event_type"]: row["count"] for row in rows},
            }
