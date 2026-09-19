"""Pure post-feed ranking and profile updates for the recommendation module."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from .schemas import FeedItem, FeedResponse, FeedScoreBreakdown, InteractionEvent, Post, UserProfile


BASE_WEIGHTS = {
    "long_term_preference": 0.15,
    "session_intent": 0.10,
    "recommendation_intent": 0.20,
    "social": 0.10,
    "deep_engagement": 0.12,
    "quality": 0.10,
    "collaborative": 0.08,
    "velocity": 0.05,
    "exploration": 0.10,
}
EXTERNAL_TREND_WEIGHT = 0.10
TREND_DIMENSION_WEIGHTS = {"style": 0.50, "color": 0.25, "occasion": 0.15, "item": 0.10}
PROFILE_SIGNAL_WEIGHTS = {
    "dwell_2_8s": 0.03,
    "dwell_8s_plus": 0.05,
    "post_open": 0.03,
    "like": 0.15,
    "save": 0.20,
    "follow": 0.30,
    "product_click": 0.10,
    "dislike": -0.30,
    "not_interested": -0.30,
    "hide": -0.40,
    "quick_skip": -0.08,
}


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, value))


def _norm(value: float, ceiling: float) -> float:
    return min(1.0, math.log1p(max(0.0, value)) / math.log1p(max(1.0, ceiling)))


def _event_value(event: InteractionEvent | dict, key: str, default=None):
    return event.get(key, default) if isinstance(event, dict) else getattr(event, key, default)


def post_dimension_tags(post: Post) -> dict[str, list[str]]:
    items = list(post.item_tags)
    for tagged in post.tagged_products:
        label = tagged.label.strip().lower().replace("-", "_").replace(" ", "_")
        if label and label not in items:
            items.append(label)
    return {"style": post.styles, "color": post.colors, "occasion": post.occasion, "item": items}


def _weights_match(post: Post, preferences: dict[str, float]) -> float:
    keys = [f"{dimension}:{tag}" for dimension, tags in post_dimension_tags(post).items() for tag in tags]
    if not keys:
        return 0.5
    return _bounded((sum(preferences.get(key, 0.0) for key in keys) / len(keys) + 1) / 2)


def trend_components(post: Post, trend_scores: dict[str, float]) -> dict[str, float]:
    components: dict[str, float] = {}
    for dimension, tags in post_dimension_tags(post).items():
        components[f"{dimension}_trend"] = max(
            (_bounded(trend_scores.get(f"{dimension}:{tag}", 0.0)) for tag in tags),
            default=0.0,
        )
    components["external_trend"] = sum(
        TREND_DIMENSION_WEIGHTS[dimension] * components[f"{dimension}_trend"]
        for dimension in TREND_DIMENSION_WEIGHTS
    )
    return components


def update_profile(profile: UserProfile, post: Post, signal_type: str, scale: float = 1.0) -> UserProfile:
    """Return an updated copy; callers remain responsible for idempotency and persistence."""
    if signal_type not in PROFILE_SIGNAL_WEIGHTS:
        raise ValueError(f"unsupported profile signal: {signal_type}")
    updated = profile.model_copy(deep=True)
    weight = PROFILE_SIGNAL_WEIGHTS[signal_type] * scale
    if signal_type == "follow":
        if post.creator_id not in updated.followed_creator_ids:
            updated.followed_creator_ids.append(post.creator_id)
        updated.creator_affinity[post.creator_id] = min(
            1.0, updated.creator_affinity.get(post.creator_id, 0.0) + weight
        )
        dimensions = {"style": post.styles}
        weight = 0.05 * scale
    else:
        dimensions = post_dimension_tags(post)
    for dimension, tags in dimensions.items():
        for tag in tags:
            key = f"{dimension}:{tag}"
            updated.preference_weights[key] = max(
                -1.0, min(1.0, updated.preference_weights.get(key, 0.0) + weight)
            )
    updated.profile_version += 1
    updated.updated_at = datetime.now(timezone.utc)
    return updated


def rank_feed(
    user_id: str,
    posts: list[Post],
    profile: UserProfile,
    events: list[InteractionEvent | dict],
    limit: int = 20,
    *,
    session_weights: dict[str, float] | None = None,
    recommendation_weights: dict[str, float] | None = None,
    collaborative_scores: dict[str, float] | None = None,
    post_stats: dict[str, dict[str, float]] | None = None,
    external_trend_scores: dict[str, float] | None = None,
    current_time: datetime | None = None,
) -> FeedResponse:
    if user_id != profile.user_id:
        raise ValueError("profile user_id does not match feed user_id")
    session_weights = session_weights or {}
    recommendation_weights = recommendation_weights or {}
    collaborative_scores = collaborative_scores or {}
    post_stats = post_stats or {}
    external_trend_scores = external_trend_scores or {}
    current_time = current_time or datetime.now(timezone.utc)
    interacted = {
        _event_value(event, "target_id") for event in events
        if _event_value(event, "user_id", user_id) == user_id
    }
    impressions: dict[str, int] = {}
    for event in events:
        if _event_value(event, "user_id", user_id) == user_id and _event_value(event, "event_type") == "impression":
            post_id = _event_value(event, "target_id")
            impressions[post_id] = impressions.get(post_id, 0) + 1

    max_likes = max((post.engagement.like_count for post in posts), default=1)
    max_saves = max((post.engagement.save_count for post in posts), default=1)
    ranked: list[tuple[Post, float, FeedScoreBreakdown]] = []
    for post in posts:
        stats = post_stats.get(post.post_id, {})
        created_at = post.created_at or current_time
        created_at = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
        age_hours = max(0.0, (current_time - created_at).total_seconds() / 3600)
        base_quality = (
            0.55 * _norm(post.engagement.like_count, max_likes)
            + 0.45 * _norm(post.engagement.save_count, max_saves)
        )
        dynamic_quality = min(1.0, 3 * stats.get("like_rate", 0.0) + 5 * stats.get("save_rate", 0.0))
        deep_engagement = min(
            1.0,
            0.15 * stats.get("like_rate", 0.0)
            + 0.30 * stats.get("save_rate", 0.0)
            + 0.20 * stats.get("product_click_rate", 0.0)
            + 0.20 * stats.get("qualified_dwell_rate", 0.0)
            + 0.15 * stats.get("follow_rate", 0.0),
        )
        trend = trend_components(post, external_trend_scores)
        fatigue = max(0.20, 0.60 ** max(0, impressions.get(post.post_id, 0) - 1))
        recency = 0.65 + 0.35 * math.exp(-age_hours / (24 * 7))
        negative = min(0.50, stats.get("negative_rate", 0.0) * 0.50)
        values = {
            "long_term_preference": _weights_match(post, profile.preference_weights),
            "session_intent": _weights_match(post, session_weights),
            "recommendation_intent": _weights_match(post, recommendation_weights),
            "social": max(
                1.0 if post.creator_id in profile.followed_creator_ids else 0.0,
                profile.creator_affinity.get(post.creator_id, 0.0),
            ),
            "deep_engagement": deep_engagement,
            "quality": 0.70 * base_quality + 0.30 * dynamic_quality,
            "collaborative": _bounded(collaborative_scores.get(post.post_id, 0.0)),
            "velocity": _bounded(stats.get("velocity", 0.0)),
            "exploration": 0.0 if post.post_id in interacted else 1.0,
        }
        base_score = sum(BASE_WEIGHTS[key] * values[key] for key in BASE_WEIGHTS)
        total = ((1 - EXTERNAL_TREND_WEIGHT) * base_score + EXTERNAL_TREND_WEIGHT * trend["external_trend"])
        total = total * fatigue * recency - negative
        breakdown = FeedScoreBreakdown(
            **values,
            **trend,
            fatigue_multiplier=fatigue,
            recency_multiplier=recency,
            negative_penalty=negative,
            total_score=total,
        )
        ranked.append((post, total, breakdown))
    ranked.sort(key=lambda row: row[1], reverse=True)

    selected: list[tuple[Post, float, FeedScoreBreakdown]] = []
    deferred: list[tuple[Post, float, FeedScoreBreakdown]] = []
    creator_counts: dict[str, int] = {}
    for row in ranked:
        creator = row[0].creator_id
        if creator_counts.get(creator, 0) >= 3 or (selected and selected[-1][0].creator_id == creator):
            deferred.append(row)
            continue
        selected.append(row)
        creator_counts[creator] = creator_counts.get(creator, 0) + 1
        if len(selected) == limit:
            break
    for row in deferred:
        if len(selected) >= limit:
            break
        if creator_counts.get(row[0].creator_id, 0) < 3:
            selected.append(row)
            creator_counts[row[0].creator_id] = creator_counts.get(row[0].creator_id, 0) + 1

    items: list[FeedItem] = []
    for rank, (post, score, breakdown) in enumerate(selected[:limit], 1):
        reasons: list[str] = []
        if breakdown.long_term_preference >= 0.55:
            reasons.append("符合使用者偏好標籤")
        if breakdown.session_intent >= 0.55:
            reasons.append("符合本次瀏覽意圖")
        if breakdown.recommendation_intent >= 0.55:
            reasons.append("符合本次穿搭需求")
        if post.creator_id in profile.followed_creator_ids:
            reasons.append("來自已追蹤創作者")
        if breakdown.collaborative > 0:
            reasons.append("相似使用者也喜歡")
        if breakdown.velocity > 0.2:
            reasons.append("近期互動成長")
        if breakdown.external_trend >= 0.25:
            reasons.append("Google Trends 熱門趨勢")
        if breakdown.exploration > 0:
            reasons.append("探索／尚未互動內容")
        items.append(FeedItem(
            post_id=post.post_id,
            rank=rank,
            score=score,
            ranking_reason=reasons or ["綜合排序"],
            score_breakdown=breakdown,
            post=post,
        ))
    return FeedResponse(
        user_id=user_id,
        items=items,
        next_cursor=None,
        profile_version=profile.profile_version,
    )
