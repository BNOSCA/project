"""Exercise the default combined catalog through the public P0 API."""

from pathlib import Path
import base64

import pytest

from fastapi.testclient import TestClient

from backend.config import ROOT, Settings
from backend.main import create_app


@pytest.fixture(autouse=True)
def disable_external_llm(monkeypatch):
    """Integration tests must be deterministic and never call a paid API."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)


def test_three_combined_catalog_demo_runs(tmp_path: Path):
    settings = Settings(
        mode="mock",
        cors_origins=("http://localhost:5173",),
        db_path=tmp_path / "demo.sqlite3",
        data_dir=ROOT / "data" / "catalog" / "combined",
        llm_timeout_seconds=8,
    )
    client = TestClient(create_app(settings))
    assert client.get("/health").json()["status"] == "ok"

    for index in range(3):
        session = f"combined-demo-{index}"
        feed_response = client.get("/api/v1/feed", params={
            "user_id": "anonymous-demo", "session_id": session, "limit": 20,
        })
        assert feed_response.status_code == 200
        feed = feed_response.json()
        assert len(feed["items"]) >= 3
        post = feed["items"][0]["post"]
        assert post["item_tags"] or post["detected_regions"]
        assert feed["items"][0]["creator"]["display_name"]

        detail_response = client.get(f"/api/v1/posts/{post['post_id']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["creator"]["creator_id"] == post["creator_id"]
        if detail["tagged_products"]:
            assert all(tag["match_type"] == "similar" and tag["product"]["product_url"]
                       for tag in detail["tagged_products"])
        else:
            # Network-bound post images or a weak visual match may legitimately
            # leave this empty; the focused retrieval test below checks the
            # actual image-search wiring without relying on an external CDN.
            assert detail["post"]["detected_regions"]
            assert all(product["product_url"] for product in detail["similar_products"])

        recommendation_response = client.post("/api/v1/recommend", json={
            "session_id": session,
            "text": "週末想戶外走走，整套預算 3000 元，想要日系寬鬆，不要太貼身。",
        })
        assert recommendation_response.status_code == 200, recommendation_response.text
        recommendation = recommendation_response.json()
        assert 1 <= len(recommendation["outfits"]) <= 3
        assert len({tuple(item["product_url"] for item in outfit["items"])
                    for outfit in recommendation["outfits"]}) == len(recommendation["outfits"])
        for outfit in recommendation["outfits"]:
            assert {item["category"] for item in outfit["items"]} == {"top", "bottom", "shoes"}
            assert outfit["total_price"] == sum(item["price"] for item in outfit["items"])
            assert outfit["total_price"] <= 3000
            assert all(item["product_url"] for item in outfit["items"])
            assert all(item["fit"] != "slim" for item in outfit["items"])
            assert all("吊飾" not in item["name"] for item in outfit["items"] if item["category"] == "shoes")

        search_response = client.post("/api/v1/search", json={
            "session_id": session,
            "query_text": "襯衫 不要米色 1000元以下",
            "mode": "text",
            "filters": {"categories": ["top"], "price_max": 1000, "excluded_colors": ["beige"]},
        })
        assert search_response.status_code == 200, search_response.text
        hits = search_response.json()["products"]
        assert hits
        assert search_response.json()["retrieval"]["fusion_method"] in {
            "metadata_text", "fashion_clip_text", "fashion_clip_text_image",
        }
        assert all(hit["explanation"] and hit["explanation_source"] in {"llm", "fallback"}
                   for hit in hits)
        assert all(hit["product"]["category"] == "top" and
                   hit["product"]["price"] <= 1000 and
                   "beige" not in hit["product"]["colors"] for hit in hits)

        for event_type in ("post_open", "dwell", "save"):
            event = {
                "event_id": f"{session}-{event_type}", "session_id": session,
                "event_type": event_type, "target_type": "post", "target_id": post["post_id"],
                "dwell_ms": 8200 if event_type == "dwell" else None,
            }
            assert client.post("/api/v1/events/batch", json=[event]).status_code == 200
        like = client.post("/api/v1/feedback", json={
            "event_id": f"{session}-like", "session_id": session,
            "event_type": "like", "target_type": "post", "target_id": post["post_id"],
        })
        assert like.status_code == 200
        assert like.json()["profile"]["preference_weights"]
        assert client.get("/api/v1/feed", params={"session_id": session}).json()["profile_version"] > 0
        assert client.get("/api/v1/insights").json()["event_counts"]["post_open"] == 1
        assert client.post(f"/api/v1/session/{session}/reset").json()["reset"] is True
        # A reset only clears short-term session state. Long-term preferences
        # belong to the account and must survive a new query/session.
        assert client.get("/api/v1/profile/anonymous-demo", params={"session_id": session}).json()[
            "preference_weights"]

    insights = client.get("/api/v1/insights").json()
    assert insights["source_type"] == "demo"
    assert insights["event_counts"] == {}


def test_implemented_search_modes_and_feed_events_are_reachable(tmp_path: Path):
    settings = Settings("mock", ("http://localhost:5173",), tmp_path / "demo.sqlite3",
                        ROOT / "data" / "catalog" / "combined", 8)
    client = TestClient(create_app(settings))
    one_pixel = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xcf\xc0\x00\x00\x04\xbf\x01\xfe\xa7\x89\x81\xa0\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode()
    search = client.post("/api/v1/search", json={
        "session_id": "multimodal", "query_text": "帆布鞋", "mode": "mixed",
        "query_image": f"data:image/png;base64,{one_pixel}",
        "filters": {"categories": ["shoes"]},
    })
    assert search.status_code == 200, search.text
    assert search.json()["retrieval"]["fusion_method"] in {"metadata_text", "rrf"}
    assert search.json()["products"]
    assert all(hit["product"]["category"] == "shoes" for hit in search.json()["products"])

    before = client.get("/api/v1/feed", params={"session_id": "events", "limit": 20}).json()
    post_id = before["items"][0]["post_id"]
    client.post("/api/v1/events/batch", json=[{
        "event_id": "events-open", "session_id": "events", "event_type": "post_open",
        "target_type": "post", "target_id": post_id,
    }])
    items = []
    cursor = None
    while True:
        params = {"session_id": "events", "limit": 100}
        if cursor:
            params["cursor"] = cursor
        page = client.get("/api/v1/feed", params=params).json()
        items.extend(page["items"])
        cursor = page["next_cursor"]
        if not cursor:
            break
    opened = next(item for item in items if item["post_id"] == post_id)
    assert opened["score_breakdown"]["exploration"] == 0


def test_post_detail_populates_image_retrieved_similar_products(monkeypatch, tmp_path: Path):
    """A post image must drive product selection, not reuse a static tag list."""
    from backend import main

    calls = {}
    monkeypatch.setattr(main, "embedding_runtime", lambda: {
        "model_backend": "transformers", "store_backend": "transformers", "store_compatible": True,
    })

    def fake_rank(*, image_input, regions, candidates, excluded_product_ids):
        calls.update(image_input=image_input, regions=[region.label for region in regions],
                     candidate_ids=[product.product_id for product in candidates],
                     excluded_product_ids=excluded_product_ids)
        return [next(product for product in candidates if product.category == category)
                for category in ("top", "bottom", "shoes")]

    monkeypatch.setattr(main, "rank_post_image_products", fake_rank)
    settings = Settings("mock", ("http://localhost:5173",), tmp_path / "post-search.sqlite3",
                        ROOT / "data" / "catalog" / "combined", 8)
    client = TestClient(create_app(settings))

    response = client.get("/api/v1/posts/post-pexels-batch-13008395")

    assert response.status_code == 200
    detail = response.json()
    assert calls["image_input"] == detail["post"]["image_url"]
    assert set(calls["regions"]) == {"top", "bottom", "shoes"}
    assert calls["excluded_product_ids"] == set()
    assert detail["tagged_products"] == []
    assert {item["category"] for item in detail["similar_products"]} == {"top", "bottom", "shoes"}


def test_shop_search_infers_garment_category_without_explicit_filter(tmp_path: Path):
    settings = Settings("mock", ("http://localhost:5173",), tmp_path / "shop-search.sqlite3",
                        ROOT / "data" / "catalog" / "combined", 8)
    client = TestClient(create_app(settings))
    response = client.post("/api/v1/search", json={
        "session_id": "shop-category", "query_text": "日系 寬鬆 襯衫", "mode": "text",
        "filters": {"available_only": True},
    })
    assert response.status_code == 200, response.text
    assert response.json()["retrieval"]["prefilter_count"] > 0
    assert all(hit["product"]["category"] == "top" for hit in response.json()["products"])
    assert all(not any(word in hit["product"]["name"] for word in ("吊飾", "腰帶", "領巾", "襪"))
               for hit in response.json()["products"])
