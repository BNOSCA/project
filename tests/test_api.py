from pathlib import Path
import sys
import types
import time

import pytest
from fastapi.testclient import TestClient

from backend.config import ROOT, Settings
from backend.main import create_app


@pytest.fixture
def client(tmp_path: Path):
    settings = Settings(
        mode="mock",
        cors_origins=("http://localhost:5173",),
        db_path=tmp_path / "demo.sqlite3",
        data_dir=ROOT / "data" / "fixtures",
        llm_timeout_seconds=0.1,
    )
    return TestClient(create_app(settings))


def test_three_complete_mock_demo_runs(client: TestClient):
    assert client.get("/health").json()["status"] == "ok"
    for index in range(3):
        session = f"demo-{index}"
        recommendation = client.post("/api/v1/recommend", json={
            "session_id": session,
            "text": "週末想戶外走走，整套預算 3000 元，想要日系寬鬆，不要太貼身。",
        })
        assert recommendation.status_code == 200, recommendation.text
        data = recommendation.json()
        assert data["fallback_used"] is True
        assert data["outfits"]
        for outfit in data["outfits"]:
            assert {item["category"] for item in outfit["items"]} == {"top", "bottom", "shoes"}
            assert outfit["total_price"] == sum(item["price"] for item in outfit["items"])
            assert outfit["total_price"] <= 3000
            assert all(item["fit"] != "slim" for item in outfit["items"])

        search = client.post("/api/v1/search", json={
            "session_id": session, "query_text": "日系", "mode": "text",
            "filters": {"categories": ["top"], "excluded_colors": ["beige"]},
        })
        assert search.status_code == 200
        assert search.json()["products"]
        assert all(hit["product"]["category"] == "top" and "beige" not in hit["product"]["colors"]
                   for hit in search.json()["products"])

        feed = client.get("/api/v1/feed", params={"user_id": "anonymous-demo", "limit": 2}).json()
        second = client.get("/api/v1/feed", params={"cursor": feed["next_cursor"], "limit": 2}).json()
        assert feed["next_cursor"] == "2"
        assert {item["post_id"] for item in feed["items"]}.isdisjoint(
            {item["post_id"] for item in second["items"]})
        detail = client.get(f"/api/v1/posts/{feed['items'][0]['post_id']}")
        assert detail.status_code == 200
        assert all(tag["match_type"] == "similar" for tag in detail.json()["tagged_products"])

        event = {"event_id": f"like-{index}", "session_id": session, "event_type": "like",
                 "target_type": "post", "target_id": feed["items"][0]["post_id"]}
        accepted = client.post("/api/v1/events/batch", json=[event, event]).json()
        assert accepted == {"accepted_count": 1, "duplicate_count": 1}
        feedback = {"event_id": f"feedback-{index}", "session_id": session,
                    "event_type": "explicit", "explicit_patch": {"excluded.colors": ["beige"]}}
        first = client.post("/api/v1/feedback", json=feedback)
        second_feedback = client.post("/api/v1/feedback", json=feedback)
        assert first.status_code == 200
        assert first.json()["profile"]["preference_weights"]["color:beige"] == -1.0
        assert all("beige" not in item["colors"] for outfit in first.json()["recommendation"]["outfits"]
                   for item in outfit["items"])
        assert second_feedback.json()["duplicate"] is True
        assert client.get("/api/v1/profile/anonymous-demo", params={"session_id": session}).json()[
            "preference_weights"]["color:beige"] == -1.0
        assert client.post(f"/api/v1/session/{session}/reset").json()["reset"] is True
        # Reset clears the temporary session, while account-level preferences
        # remain available for future sessions.
        assert client.get("/api/v1/profile/anonymous-demo", params={"session_id": session}).json()[
            "preference_weights"]["color:beige"] == -1.0
    insights = client.get("/api/v1/insights").json()
    assert insights["sample_size"] == 0
    assert insights["source_type"] == "demo"


def test_dwell_gates_and_insights(client: TestClient):
    feed = client.get("/api/v1/feed", params={"user_id": "anonymous-demo", "limit": 100}).json()
    post_id = next(item["post_id"] for item in feed["items"] if "japanese" in item["post"]["styles"])

    def send(event_id, dwell_ms, foreground=True):
        return client.post("/api/v1/events/batch", json=[{
            "event_id": event_id, "session_id": "dwell", "event_type": "dwell",
            "target_type": "post", "target_id": post_id,
            "dwell_ms": dwell_ms, "is_foreground": foreground,
        }])

    assert send("background", 30000, False).status_code == 200
    assert send("short", 1500).status_code == 200
    profile_url = "/api/v1/profile/anonymous-demo?session_id=dwell"
    assert client.get(profile_url).json()["preference_weights"] == {}
    send("valid", 8200)
    weight = client.get(profile_url).json()["preference_weights"]["style:japanese"]
    assert weight == 0.05
    send("second-valid", 9000)
    assert client.get(profile_url).json()["preference_weights"]["style:japanese"] == weight
    assert client.get("/api/v1/insights").json()["event_counts"] == {"dwell": 4}


def test_explore_like_changes_shop_fixture_score(client: TestClient):
    request = {
        "session_id": "cross-surface",
        "text": "整套預算 3000 元",
    }

    before = client.post(
        "/api/v1/recommend",
        json=request,
    ).json()["outfits"]

    feed = client.get(
        "/api/v1/feed",
        params={
            "user_id": "anonymous-demo",
            "limit": 100,
        },
    ).json()

    post_id = next(
        item["post_id"]
        for item in feed["items"]
        if "beige" in item["post"]["colors"]
    )

    response = client.post(
        "/api/v1/events/batch",
        json=[{
            "event_id": "beige-like",
            "session_id": "cross-surface",
            "event_type": "like",
            "target_type": "post",
            "target_id": post_id,
        }],
    )

    assert response.status_code == 200

    # 確認 Like 真的更新了長期偏好
    profile = client.get(
        "/api/v1/profile/anonymous-demo",
        params={"session_id": "cross-surface"},
    ).json()

    assert (
        profile["preference_weights"]
        .get("color:beige", 0)
        > 0
    )

    after = client.post(
        "/api/v1/recommend",
        json=request,
    ).json()["outfits"]

    assert before
    assert after

    # Like 後推薦結果的最佳分數應提高
    assert max(
        outfit["score"]
        for outfit in after
    ) > max(
        outfit["score"]
        for outfit in before
    )

    # 更新後的推薦中仍應有 beige 相關商品
    assert any(
        "beige" in item["colors"]
        for outfit in after
        for item in outfit["items"]
    )

def test_uniform_errors_and_hard_constraints(client: TestClient):
    cases = [
        ("/api/v1/recommend", {"session_id": "low", "text": "整套預算 200 元"}, "NO_MATCHING_PRODUCTS"),
        ("/api/v1/recommend", {"session_id": "bad", "text": "日系", "image": "base64"}, "INVALID_INPUT"),
        ("/api/v1/search", {"session_id": "bad", "query_text": "日系", "mode": "image"}, "INVALID_INPUT"),
        ("/api/v1/search", {"session_id": "bad", "query_text": "日系", "filters": {"price_max": -1}}, "INVALID_INPUT"),
    ]
    for url, body, code in cases:
        response = client.post(url, json=body)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == code
        assert set(response.json()["error"]) == {"code", "message", "retryable", "details"}
    assert client.get("/api/v1/posts/missing").status_code == 404
    assert client.get("/api/v1/feed?cursor=not-a-cursor").json()["error"]["code"] == "INVALID_INPUT"


def test_text_feedback_and_search_exclusions(client: TestClient):
    client.post("/api/v1/recommend", json={"session_id": "text", "text": "日系 預算 3000 元"})
    response = client.post("/api/v1/feedback", json={
        "event_id": "text-feedback", "session_id": "text", "event_type": "explicit", "text": "不要米色",
    })
    assert response.status_code == 200
    assert response.json()["profile"]["preference_weights"]["color:beige"] == -1.0
    repeated = client.post("/api/v1/feedback", json={
        "event_id": "text-feedback", "session_id": "text", "event_type": "explicit", "text": "不要米色",
    })
    assert repeated.status_code == 200
    assert repeated.json()["duplicate"] is True
    new_event = client.post("/api/v1/feedback", json={
        "event_id": "same-instruction-new-id", "session_id": "text", "event_type": "explicit", "text": "不要米色",
    })
    assert new_event.status_code == 200
    assert new_event.json()["profile"]["preference_weights"]["color:beige"] == -1.0
    search = client.post("/api/v1/search", json={"session_id": "text", "query_text": "日系，不要米色"})
    assert search.status_code == 200
    assert search.json()["products"]
    assert all("beige" not in hit["product"]["colors"] for hit in search.json()["products"])
    session_search = client.post("/api/v1/search", json={"session_id": "text", "query_text": "極簡"})
    assert session_search.status_code == 200
    assert all("beige" not in hit["product"]["colors"] for hit in session_search.json()["products"])
    invalid = client.post("/api/v1/feedback", json={
        "event_id": "unknown-text", "session_id": "text", "event_type": "explicit", "text": "換一個感覺",
    })
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "INVALID_INPUT"


def test_text_price_ceiling_is_a_search_hard_filter(client: TestClient):
    response = client.post("/api/v1/search", json={
        "session_id": "price", "query_text": "日系，900 以下", "mode": "text",
    })
    assert response.status_code == 200
    assert response.json()["products"]
    assert all(hit["product"]["price"] <= 900 for hit in response.json()["products"])
    assert response.json()["retrieval"]["prefilter_count"] < 6


def test_multiturn_fallback_replaces_only_mentioned_preference(client: TestClient):
    first = client.post("/api/v1/recommend", json={
        "session_id": "multi", "text": "日系寬鬆，喜歡白色，不要米色，整套預算 3000 元"})
    assert first.status_code == 200
    second = client.post("/api/v1/recommend", json={
        "session_id": "multi", "text": "改成黑色，預算提高到 4000 元"})
    assert second.status_code == 200
    intent = second.json()["intent"]
    assert intent["preferred"]["colors"] == ["black"]
    assert intent["preferred"]["styles"] == ["japanese"]
    assert intent["preferred"]["fits"] == ["relaxed"]
    assert intent["excluded"]["colors"] == ["beige"]
    assert intent["budget_total"] == 4000


def test_live_mode_reports_missing_modules(tmp_path: Path):
    settings = Settings("live", ("http://localhost:5173",), tmp_path / "live.sqlite3",
                        ROOT / "data" / "fixtures", 0.1)
    client = TestClient(create_app(settings))
    assert client.get("/health").json()["status"] == "degraded"
    response = client.post("/api/v1/recommend", json={"session_id": "live", "text": "日系 預算 3000 元"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATA_UNAVAILABLE"


def test_live_orchestration_contract(monkeypatch, tmp_path: Path):
    calls = {}

    intent_module = types.ModuleType("backend.intent")
    def parse_intent(text, previous):
        calls["parse"] = text
        return {"source_text": text, "semantic_query": text, "budget_total": 3000,
                "excluded": {"colors": ["beige"]} if "不要米色" in text else {}}
    intent_module.parse_intent = parse_intent
    intent_module.parse_feedback = lambda text, current: {"excluded.colors": ["beige"]}

    search_module = types.ModuleType("backend.search")
    def search_products(request, catalog):
        calls["search_candidates"] = catalog
        return {"session_id": request.session_id, "mode": "text",
                "products": [{"product_id": catalog[0].product_id, "score": 1}],
                "retrieval": {"prefilter_count": len(catalog), "text_candidates": 1}}
    search_module.search_products = search_products

    recommender_module = types.ModuleType("backend.recommender")
    def recommend(intent, profile, catalog):
        calls["recommend_candidates"] = catalog
        items = [next(p for p in catalog if p.category == category) for category in intent.required_categories]
        return [{"outfit_id": "live-outfit", "items": items,
                 "total_price": sum(p.price for p in items), "score": 0.7}]
    recommender_module.recommend = recommend

    feedback_module = types.ModuleType("backend.feedback")
    feedback_module.get_profile = lambda user_id: {"user_id": user_id}
    def record_feedback(event):
        calls["feedback_patch"] = event.explicit_patch
        return {"user_id": event.user_id, "preference_weights": {"color:beige": -1}}
    feedback_module.record_feedback = record_feedback
    feedback_module.get_insights = lambda: {"sample_size": 1, "time_range": {"start": None, "end": None}, "source_type": "demo"}
    feedback_module.reset_session = lambda session_id: None

    events_module = types.ModuleType("backend.events")
    events_module.record_interactions = lambda events: {"accepted_count": len(events), "duplicate_count": 0}
    for name, module in (("intent", intent_module), ("search", search_module),
                         ("recommender", recommender_module), ("feedback", feedback_module),
                         ("events", events_module)):
        monkeypatch.setitem(sys.modules, f"backend.{name}", module)

    settings = Settings("live", ("http://localhost:5173",), tmp_path / "live.sqlite3",
                        ROOT / "data" / "fixtures", 0.5)
    client = TestClient(create_app(settings))
    assert client.get("/health").json()["status"] == "ok"
    result = client.post("/api/v1/recommend", json={"session_id": "live", "text": "日系不要米色，預算 3000 元"})
    assert result.status_code == 200, result.text
    assert result.json()["outfits"][0]["reason"]
    assert all("beige" not in p.colors for p in calls["recommend_candidates"])

    search = client.post("/api/v1/search", json={"session_id": "live", "query_text": "日系不要米色"})
    assert search.status_code == 200
    assert all("beige" not in p.colors for p in calls["search_candidates"])
    assert search.json()["products"][0]["product"]["product_id"]

    feedback = client.post("/api/v1/feedback", json={
        "event_id": "live-feedback", "session_id": "live", "event_type": "explicit", "text": "不要米色"})
    assert feedback.status_code == 200, feedback.text
    assert calls["feedback_patch"] == {"excluded.colors": ["beige"]}
    assert feedback.json()["recommendation"]["outfits"]
    post_id = client.get("/api/v1/feed", params={"limit": 1}).json()["items"][0]["post_id"]
    assert client.post("/api/v1/events/batch", json=[{
        "event_id": "live-like", "session_id": "live", "event_type": "like",
        "target_type": "post", "target_id": post_id}]).json()["accepted_count"] == 1
    assert client.get("/api/v1/insights").json()["sample_size"] == 1


def test_llm_timeout_uses_rule_fallback(monkeypatch, tmp_path: Path):
    intent_module = types.ModuleType("backend.intent")
    def slow_parse(_text, _previous):
        time.sleep(0.1)
        raise AssertionError("late LLM result must not be used")
    intent_module.parse_intent = slow_parse
    feedback_module = types.ModuleType("backend.feedback")
    feedback_module.get_profile = lambda user_id: {"user_id": user_id}
    recommender_module = types.ModuleType("backend.recommender")
    def recommend(intent, _profile, catalog):
        items = [next(p for p in catalog if p.category == category) for category in intent.required_categories]
        return [{"outfit_id": "fallback-outfit", "items": items, "total_price": sum(p.price for p in items)}]
    recommender_module.recommend = recommend
    for name, module in (("intent", intent_module), ("feedback", feedback_module), ("recommender", recommender_module)):
        monkeypatch.setitem(sys.modules, f"backend.{name}", module)
    settings = Settings("live", ("http://localhost:5173",), tmp_path / "timeout.sqlite3",
                        ROOT / "data" / "fixtures", 0.02)
    response = TestClient(create_app(settings)).post("/api/v1/recommend", json={
        "session_id": "timeout", "text": "日系寬鬆，整套預算 3000 元"})
    assert response.status_code == 200, response.text
    assert response.json()["fallback_used"] is True
    assert response.json()["outfits"]


def test_missing_catalog_has_diagnostic_health_and_error(tmp_path: Path):
    settings = Settings("mock", ("http://localhost:5173",), tmp_path / "missing.sqlite3",
                        tmp_path / "no-data", 0.1)
    client = TestClient(create_app(settings))
    assert client.get("/health").json()["status"] == "degraded"
    response = client.post("/api/v1/recommend", json={"session_id": "missing", "text": "日系"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATA_UNAVAILABLE"
