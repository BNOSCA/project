"""Small typed helpers around Firestore collection access."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from google.cloud.firestore_v1 import Client
from pydantic import BaseModel

from backend.firebase import get_firestore_client


ModelT = TypeVar("ModelT", bound=BaseModel)


class FirestoreRepository(Generic[ModelT]):
    collection_name: str
    id_field: str
    model: type[ModelT]

    def __init__(self, client: Client | None = None):
        self.client = client or get_firestore_client()
        self.collection = self.client.collection(self.collection_name)

    def list(self, limit: int = 100) -> list[ModelT]:
        docs = self.collection.limit(limit).stream()
        return [self.model.model_validate(self._with_document_id(doc.id, doc.to_dict() or {})) for doc in docs]

    def get(self, document_id: str) -> ModelT | None:
        doc = self.collection.document(document_id).get()
        if not doc.exists:
            return None
        return self.model.model_validate(self._with_document_id(doc.id, doc.to_dict() or {}))

    def upsert(self, item: ModelT | dict[str, Any]) -> str:
        data = item.model_dump(mode="json") if isinstance(item, BaseModel) else dict(item)
        document_id = data[self.id_field]
        self.collection.document(document_id).set(data, merge=True)
        return document_id

    def _with_document_id(self, document_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return {self.id_field: document_id, **data}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
