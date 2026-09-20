"""Small server-side aggregates for the protected company insights view."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from google.cloud.firestore_v1 import Client

from .firebase import get_firestore_client


def _as_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def build_admin_insights(client: Client | None = None, now: datetime | None = None) -> dict:
    client = client or get_firestore_client()
    now = now or datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    users = [doc.to_dict() or {} for doc in client.collection("users").stream()]
    interactions = [doc.to_dict() or {} for doc in client.collection("interactions").stream()]

    age_distribution = Counter(
        user.get("age_range") for user in users if user.get("age_range")
    )
    style_distribution = Counter(
        style
        for user in users
        for style in user.get("preferred_styles", [])
        if isinstance(style, str)
    )
    engagement = Counter(event.get("event_type") for event in interactions)
    active_users = {
        event.get("user_id")
        for event in interactions
        if event.get("user_id") and (timestamp := _as_datetime(event.get("created_at"))) is not None
        and week_ago <= timestamp <= now
    }
    sessions = {event.get("session_id") for event in interactions if event.get("session_id")}
    impressions = engagement.get("impression", 0)

    return {
        "overview": {
            "total_users": len(users),
            "active_users_7d": len(active_users),
            "total_sessions": len(sessions),
            "total_interactions": len(interactions),
        },
        "age_distribution": dict(sorted(age_distribution.items())),
        "style_distribution": dict(style_distribution.most_common()),
        "engagement": dict(engagement),
        "rates": {
            "like_rate": round(engagement.get("like", 0) / impressions, 3) if impressions else 0.0,
            "save_rate": round(engagement.get("save", 0) / impressions, 3) if impressions else 0.0,
            "product_ctr": round(engagement.get("product_click", 0) / impressions, 3) if impressions else 0.0,
        },
    }
