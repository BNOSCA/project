from datetime import datetime, timezone

import pytest

from backend.post_feed import rank_feed, trend_components, update_profile
from backend.schemas import InteractionEvent, Post, PostEngagement, UserProfile


NOW = datetime(2026, 9, 19, tzinfo=timezone.utc)


def make_post(post_id: str, style: str, color: str, item: str, creator: str) -> Post:
    return Post(
        post_id=post_id,
        creator_id=creator,
        caption=post_id,
        styles=[style],
        colors=[color],
        occasion=["commute"],
        item_tags=[item],
        engagement=PostEngagement(like_count=10, save_count=4),
        source="test",
        created_at=NOW,
    )


def test_schema_additions_are_optional_and_feed_response_validates():
    profile = UserProfile(user_id="u1", gender="unspecified", age_range="18-24")
    post = make_post("p1", "japanese", "black", "shirt", "c1")

    response = rank_feed("u1", [post], profile, [], current_time=NOW)

    assert response.profile_version == 0
    assert response.items[0].post == post
    assert response.items[0].score == response.items[0].score_breakdown.total_score
    assert response.items[0].score_breakdown.item_trend == 0


def test_trend_has_style_color_occasion_and_item_dimensions():
    post = make_post("p1", "japanese", "black", "shirt", "c1")

    result = trend_components(post, {
        "style:japanese": 1.0,
        "color:black": 0.8,
        "occasion:commute": 0.6,
        "item:shirt": 0.4,
    })

    assert result["style_trend"] == 1.0
    assert result["color_trend"] == 0.8
    assert result["occasion_trend"] == 0.6
    assert result["item_trend"] == 0.4
    assert result["external_trend"] == pytest.approx(0.83)


def test_like_updates_profile_and_improves_similar_post_score():
    liked = make_post("liked", "japanese", "black", "shirt", "c1")
    similar = make_post("similar", "japanese", "black", "shirt", "c2")
    different = make_post("different", "street", "red", "denim", "c3")
    profile = UserProfile(user_id="u1")
    before = rank_feed("u1", [similar, different], profile, [], current_time=NOW)

    updated = update_profile(profile, liked, "like")
    after = rank_feed("u1", [similar, different], updated, [], current_time=NOW)
    before_scores = {item.post_id: item.score_breakdown.total_score for item in before.items}
    after_scores = {item.post_id: item.score_breakdown.total_score for item in after.items}

    assert updated.profile_version == 1
    assert updated.preference_weights["style:japanese"] == pytest.approx(0.15)
    assert after_scores["similar"] > before_scores["similar"]
    assert after.items[0].post_id == "similar"


def test_interacted_post_loses_exploration_bonus_but_is_not_rejected():
    post = make_post("p1", "japanese", "black", "shirt", "c1")
    profile = UserProfile(user_id="u1")
    event = InteractionEvent(
        event_id="e1",
        session_id="s1",
        user_id="u1",
        event_type="like",
        target_type="post",
        target_id="p1",
    )

    response = rank_feed("u1", [post], profile, [event], current_time=NOW)

    assert response.items[0].post_id == "p1"
    assert response.items[0].score_breakdown.exploration == 0
    assert "探索／尚未互動內容" not in response.items[0].ranking_reason
