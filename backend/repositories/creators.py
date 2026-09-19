from __future__ import annotations

from backend.repositories.base import FirestoreRepository
from backend.schemas import Creator


class CreatorRepository(FirestoreRepository[Creator]):
    collection_name = "creators"
    id_field = "creator_id"
    model = Creator

    def list_creators(self, limit: int = 100) -> list[Creator]:
        return self.list(limit)

    def get_creator(self, creator_id: str) -> Creator | None:
        return self.get(creator_id)

    def upsert_creator(self, creator: Creator | dict) -> str:
        return self.upsert(creator)
