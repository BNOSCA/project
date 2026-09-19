"""Seed Firestore with demo fixture data.

Run from the repository root after authenticating Google ADC:
    python scripts/seed_firestore.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.repositories import CreatorRepository, PostRepository, ProductRepository
from backend.schemas import Creator, Post, Product


FIXTURES = ROOT / "data" / "fixtures"


def load_fixture(name: str) -> list[dict[str, Any]]:
    with (FIXTURES / name).open("r", encoding="utf-8") as file:
        return json.load(file)


def seed() -> dict[str, int]:
    products = [Product.model_validate(item) for item in load_fixture("products.json")]
    posts = [Post.model_validate(item) for item in load_fixture("posts.json")]
    creators = [Creator.model_validate(item) for item in load_fixture("creators.json")]

    product_repo = ProductRepository()
    post_repo = PostRepository()
    creator_repo = CreatorRepository()

    for product in products:
        product_repo.upsert_product(product)
    for post in posts:
        post_repo.upsert_post(post)
    for creator in creators:
        creator_repo.upsert_creator(creator)

    return {"products": len(products), "posts": len(posts), "creators": len(creators)}


if __name__ == "__main__":
    counts = seed()
    print(f"Seeded Firestore: {counts}")
