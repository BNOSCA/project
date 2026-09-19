from __future__ import annotations

from backend.repositories.base import FirestoreRepository
from backend.schemas import Post


class PostRepository(FirestoreRepository[Post]):
    collection_name = "posts"
    id_field = "post_id"
    model = Post

    def list_posts(self, limit: int = 100) -> list[Post]:
        return self.list(limit)

    def get_post(self, post_id: str) -> Post | None:
        return self.get(post_id)

    def upsert_post(self, post: Post | dict) -> str:
        return self.upsert(post)
