"""Shared API and B/C/D module contracts from draft2.md, section 5."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Attributes(Contract):
    styles: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    fits: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)


class ExcludedAttributes(Contract):
    colors: list[str] = Field(default_factory=list)
    fits: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)


class Intent(Contract):
    session_id: str
    occasion: list[str] = Field(default_factory=list)
    budget_total: int | None = Field(default=None, ge=0)
    currency: Literal["TWD"] = "TWD"
    required_categories: list[str] = Field(default_factory=lambda: ["top", "bottom", "shoes"])
    preferred: Attributes = Field(default_factory=Attributes)
    excluded: ExcludedAttributes = Field(default_factory=ExcludedAttributes)
    hard_constraints: list[str] = Field(default_factory=list)
    soft_constraints: list[str] = Field(default_factory=list)
    unknown_fields: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarifying_question: str | None = None
    semantic_query: str = ""
    source_text: str = ""


class Product(Contract):
    product_id: str
    name: str
    category: str
    price: int = Field(ge=0)
    currency: Literal["TWD"] = "TWD"
    colors: list[str] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    fit: str | None = None
    materials: list[str] = Field(default_factory=list)
    sizes: list[str] = Field(default_factory=list)
    image_url: HttpUrl | None = None
    product_url: HttpUrl | None = None
    source: str
    source_checked_at: str | None = None
    availability: Literal["unknown", "demo_only", "available", "unavailable"] = "unknown"
    search_text: str = ""
    image_embedding_id: str | None = None
    text_embedding_id: str | None = None


class UserProfile(Contract):
    user_id: str
    gender: Literal["female", "male", "non_binary", "unspecified"] | None = None
    age_range: str | None = None
    preference_weights: dict[str, float] = Field(default_factory=dict)
    creator_affinity: dict[str, float] = Field(default_factory=dict)
    followed_creator_ids: list[str] = Field(default_factory=list)
    trend_affinity: float = 0
    profile_version: int = Field(default=0, ge=0)
    updated_at: datetime | None = None


class InteractionEvent(Contract):
    event_id: str
    session_id: str
    user_id: str = "anonymous-demo"
    event_type: Literal[
        "impression", "dwell", "post_open", "like", "dislike", "save", "follow",
        "product_click", "not_interested", "hide", "quick_skip",
    ]
    target_type: Literal["post", "product"]
    target_id: str
    dwell_ms: int | None = Field(default=None, ge=0)
    surface: str | None = None
    position: int | None = Field(default=None, ge=0)
    is_foreground: bool = True
    created_at: datetime | None = None

    @model_validator(mode="after")
    def dwell_requires_duration(self) -> "InteractionEvent":
        if self.event_type == "dwell" and self.dwell_ms is None:
            raise ValueError("dwell_ms is required for dwell events")
        return self


class EventBatchResult(Contract):
    accepted_count: int
    duplicate_count: int


class FeedbackEvent(Contract):
    event_id: str
    session_id: str
    user_id: str = "anonymous-demo"
    event_type: Literal["like", "dislike", "explicit"]
    target_type: Literal["post", "product"] | None = None
    target_id: str | None = None
    explicit_patch: dict[str, list[str]] = Field(default_factory=dict)
    text: str | None = None
    remember_preference: bool = False
    created_at: datetime | None = None

    @model_validator(mode="after")
    def require_effective_feedback(self) -> "FeedbackEvent":
        if self.event_type in {"like", "dislike"} and (not self.target_type or not self.target_id):
            raise ValueError("like/dislike feedback requires a target")
        if self.event_type == "explicit" and not self.explicit_patch and not self.text:
            raise ValueError("explicit feedback requires text or explicit_patch")
        return self


class ScoreBreakdown(Contract):
    relevance: float = 0
    preference: float = 0
    compatibility: float = 0
    trend: float = 0


class Outfit(Contract):
    outfit_id: str
    items: list[Product]
    total_price: int = Field(ge=0)
    score: float = 0
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    matched_constraints: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reason: str = ""


class RecommendationResponse(Contract):
    session_id: str
    intent: Intent
    outfits: list[Outfit] = Field(default_factory=list)
    fallback_used: bool = False
    message: str | None = None


class RecommendRequest(Contract):
    session_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=2000)
    user_id: str = "anonymous-demo"
    filters: "SearchFilters" = Field(default_factory=lambda: SearchFilters())
    image: str | None = None


class SearchFilters(Contract):
    categories: list[str] = Field(default_factory=list)
    price_max: int | None = Field(default=None, ge=0)
    available_only: bool = False
    excluded_colors: list[str] = Field(default_factory=list)
    excluded_fits: list[str] = Field(default_factory=list)
    sizes: list[str] = Field(default_factory=list)


class SearchRequest(Contract):
    session_id: str = Field(min_length=1)
    query_text: str = ""
    query_image: str | None = None
    mode: Literal["text", "image", "mixed"] = "text"
    image_weight: float = Field(default=0.5, ge=0, le=1)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    limit: int = Field(default=30, ge=1, le=100)


class SearchHit(Contract):
    product_id: str
    score: float = 0
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    matched_filters: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    product: Product | None = None


class RetrievalInfo(Contract):
    prefilter_count: int = 0
    image_candidates: int = 0
    text_candidates: int = 0
    fusion_method: str = "rules"


class SearchResponse(Contract):
    session_id: str
    mode: Literal["text", "image", "mixed"]
    products: list[SearchHit] = Field(default_factory=list)
    retrieval: RetrievalInfo = Field(default_factory=RetrievalInfo)


class ProductTag(Contract):
    product_id: str
    label: str
    bbox: tuple[float, float, float, float] | None = None
    match_type: Literal["exact", "similar"]


class PostEngagement(Contract):
    like_count: int = Field(default=0, ge=0)
    save_count: int = Field(default=0, ge=0)
    comment_count: int = Field(default=0, ge=0)


class Post(Contract):
    post_id: str
    creator_id: str
    image_url: HttpUrl | None = None
    caption: str
    styles: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    occasion: list[str] = Field(default_factory=list)
    item_tags: list[str] = Field(default_factory=list)
    tagged_products: list[ProductTag] = Field(default_factory=list)
    engagement: PostEngagement = Field(default_factory=PostEngagement)
    source: str
    source_checked_at: str | None = None
    is_demo: bool = True
    created_at: datetime | None = None


class Creator(Contract):
    creator_id: str
    display_name: str
    is_demo: bool = True


class FeedScoreBreakdown(Contract):
    preference: float = 0
    long_term_preference: float = 0
    session_intent: float = 0
    social: float = 0
    deep_engagement: float = 0
    quality: float = 0
    collaborative: float = 0
    velocity: float = 0
    exploration: float = 0
    style_trend: float = 0
    color_trend: float = 0
    occasion_trend: float = 0
    item_trend: float = 0
    external_trend: float = 0
    fatigue_multiplier: float = 1
    recency_multiplier: float = 1
    negative_penalty: float = 0
    total_score: float = 0


class FeedItem(Contract):
    post_id: str
    rank: int
    score: float = 0
    ranking_reason: list[str] = Field(default_factory=list)
    score_breakdown: FeedScoreBreakdown = Field(default_factory=FeedScoreBreakdown)
    post: Post | None = None


class FeedResponse(Contract):
    user_id: str
    items: list[FeedItem] = Field(default_factory=list)
    next_cursor: str | None = None
    profile_version: int = 0


class ExternalTrendSignal(Contract):
    source: Literal["google_trends"] = "google_trends"
    keyword: str
    attribute: str
    geo: str = "TW"
    period_start: str
    period_end: str
    raw_score: float = Field(ge=0, le=100)
    normalized_score: float = Field(ge=0, le=1)


class TaggedProductDetail(ProductTag):
    product: Product


class PostDetail(Contract):
    post: Post
    creator: Creator
    tagged_products: list[TaggedProductDetail]
    similar_products: list[Product] = Field(default_factory=list)


class FeedbackResponse(Contract):
    profile: UserProfile
    recommendation: RecommendationResponse | None = None
    duplicate: bool = False


class InsightsResponse(Contract):
    sample_size: int
    time_range: dict[str, str | None]
    source_type: Literal["real", "demo", "synthetic"] = "demo"
    event_counts: dict[str, int] = Field(default_factory=dict)


class ErrorBody(Contract):
    code: str
    message: str
    retryable: bool = False
    details: dict = Field(default_factory=dict)


class ErrorResponse(Contract):
    error: ErrorBody
