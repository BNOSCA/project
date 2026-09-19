from __future__ import annotations

from backend.repositories.base import FirestoreRepository
from backend.schemas import UserProfile


class UserRepository(FirestoreRepository[UserProfile]):
    collection_name = "users"
    id_field = "user_id"
    model = UserProfile

    def get_user(self, user_id: str) -> UserProfile | None:
        return self.get(user_id)

    def upsert_user(self, user: UserProfile | dict) -> str:
        return self.upsert(user)
