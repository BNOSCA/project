from __future__ import annotations

from google.cloud.firestore_v1 import Client

from backend.firebase import get_firestore_client
from backend.schemas import InteractionEvent


class InteractionRepository:
    collection_name = "interactions"

    def __init__(self, client: Client | None = None):
        self.client = client or get_firestore_client()
        self.collection = self.client.collection(self.collection_name)

    def record_interaction(self, event: InteractionEvent | dict) -> str:
        data = event.model_dump(mode="json") if isinstance(event, InteractionEvent) else dict(event)
        event_id = data["event_id"]
        self.collection.document(event_id).set(data, merge=False)
        return event_id

    def list_for_session(self, session_id: str, limit: int = 100) -> list[InteractionEvent]:
        docs = self.collection.where("session_id", "==", session_id).limit(limit).stream()
        return [InteractionEvent.model_validate(doc.to_dict() or {}) for doc in docs]
