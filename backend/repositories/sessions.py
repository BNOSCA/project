from __future__ import annotations

from typing import Any

from google.cloud.firestore_v1 import Client

from backend.firebase import get_firestore_client
from backend.repositories.base import utc_now_iso


class SessionRepository:
    collection_name = "sessions"

    def __init__(self, client: Client | None = None):
        self.client = client or get_firestore_client()
        self.collection = self.client.collection(self.collection_name)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        doc = self.collection.document(session_id).get()
        if not doc.exists:
            return None
        return {"session_id": doc.id, **(doc.to_dict() or {})}

    def upsert_session(self, session_id: str, data: dict[str, Any]) -> str:
        payload = {"session_id": session_id, "updated_at": utc_now_iso(), **data}
        self.collection.document(session_id).set(payload, merge=True)
        return session_id
