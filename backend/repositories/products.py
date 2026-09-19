from __future__ import annotations

from backend.repositories.base import FirestoreRepository
from backend.schemas import Product


class ProductRepository(FirestoreRepository[Product]):
    collection_name = "products"
    id_field = "product_id"
    model = Product

    def list_products(self, limit: int = 100) -> list[Product]:
        return self.list(limit)

    def get_product(self, product_id: str) -> Product | None:
        return self.get(product_id)

    def upsert_product(self, product: Product | dict) -> str:
        return self.upsert(product)
