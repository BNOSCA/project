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

    def has_qualifying_dwell(self, session_id: str, target_type: str, target_id: str) -> bool:
        with self.connect() as db:
            rows = db.execute(
                "SELECT payload FROM events WHERE session_id = ? AND event_type = 'dwell' AND target_type = ? AND target_id = ?",
                (session_id, target_type, target_id),
            ).fetchall()
            return any((event := json.loads(row["payload"])).get("is_foreground", True) and
                       (event.get("dwell_ms") or 0) >= 2000 for row in rows)

    def get_profile(self, session_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT profile_json FROM session_profiles WHERE session_id = ?", (session_id,)).fetchone()
            return json.loads(row["profile_json"]) if row else None

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
