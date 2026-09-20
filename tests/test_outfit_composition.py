from pathlib import Path

from backend.db import EventStore
from backend.mock import FixtureCatalog, MockServices
from backend.schemas import SearchFilters


def test_outfit_composition_uses_search_intent_tags_and_rejects_catalog_misclassifications(tmp_path: Path):
    service = MockServices(
        FixtureCatalog(Path("data/catalog/combined")),
        EventStore(tmp_path / "demo.sqlite3"),
    )
    intent = service.parse_intent("日系面試穿搭", "outfit-tags", "demo-user", origin="search")

    response = service.recommend(intent, "demo-user", filters=SearchFilters())

    assert 1 <= len(response.outfits) <= 3
    for outfit in response.outfits:
        assert [item.category for item in outfit.items] == ["top", "bottom", "shoes"]
        assert all("購物袋" not in item.name and "內褲" not in item.name for item in outfit.items)
        assert all(item.source != "synthetic_demo" and "（展示）" not in item.name for item in outfit.items)

    if len(response.outfits) == 3:
        for category in ("top", "bottom", "shoes"):
            item_ids = [next(item.product_id for item in outfit.items if item.category == category)
                        for outfit in response.outfits]
            assert len(set(item_ids)) == 3


def test_outfit_composition_never_uses_the_six_synthetic_display_products(tmp_path: Path):
    service = MockServices(
        FixtureCatalog(Path("data/fixtures")),
        EventStore(tmp_path / "demo.sqlite3"),
    )
    intent = service.parse_intent("日系面試穿搭", "display-only", "demo-user", origin="search")

    response = service.recommend(intent, "demo-user", filters=SearchFilters())

    assert response.outfits == []
