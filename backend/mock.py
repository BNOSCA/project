"""Clearly labelled fixture service for frontend work before B/C/D land.

This is deterministic demo behavior, not a replacement for the owning modules.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .db import EventStore
from .explanation import build_explanation
from .schemas import (
    Creator, EventBatchResult, FeedbackEvent, FeedItem, FeedResponse, InsightsResponse,
    Intent, InteractionEvent, Outfit, Post, PostDetail, Product, RecommendationResponse,
    RetrievalInfo, ScoreBreakdown, SearchFilters, SearchHit, SearchRequest, SearchResponse,
    TaggedProductDetail, UserProfile,
)


class FixtureCatalog:
    def __init__(self, data_dir: Path):
        self.products = [Product.model_validate(x) for x in self._read(data_dir / "products.json")]
        self.posts = [Post.model_validate(x) for x in self._read(data_dir / "posts.json")]
        self.creators = [Creator.model_validate(x) for x in self._read(data_dir / "creators.json")]
        self.products_by_id = {p.product_id: p for p in self.products}
        self.posts_by_id = {p.post_id: p for p in self.posts}
        self.creators_by_id = {c.creator_id: c for c in self.creators}
        if len(self.products_by_id) != len(self.products) or len(self.posts_by_id) != len(self.posts):
            raise ValueError("fixture IDs must be unique")
        for post in self.posts:
            if post.creator_id not in self.creators_by_id:
                raise ValueError(f"unknown creator in {post.post_id}")
            for tag in post.tagged_products:
                if tag.product_id not in self.products_by_id:
                    raise ValueError(f"unknown product in {post.post_id}")
                if tag.match_type == "exact":
                    raise ValueError("synthetic fixtures cannot claim exact product matches")

    @staticmethod
    def _read(path: Path) -> list[dict]:
        with path.open(encoding="utf-8") as file:
            return json.load(file)

    def post_detail(self, post_id: str) -> PostDetail | None:
        post = self.posts_by_id.get(post_id)
        if post is None:
            return None
        tagged = []
        for tag in post.tagged_products:
            tagged.append(TaggedProductDetail(**tag.model_dump(mode="json"), product=self.products_by_id[tag.product_id]))
        return PostDetail(post=post, creator=self.creators_by_id[post.creator_id], tagged_products=tagged)


def filter_products(products: list[Product], filters: SearchFilters, intent: Intent | None = None) -> list[Product]:
    """Apply deterministic metadata constraints before any retrieval or ranking."""
    excluded_colors = set(filters.excluded_colors) | (set(intent.excluded.colors) if intent else set())
    excluded_fits = set(filters.excluded_fits) | (set(intent.excluded.fits) if intent else set())
    result = []
    for product in products:
        if filters.categories and product.category not in filters.categories:
            continue
        if filters.price_max is not None and product.price > filters.price_max:
            continue
        if filters.available_only and product.availability != "available":
            continue
        if excluded_colors and (not product.colors or excluded_colors.intersection(product.colors)):
            continue
        if excluded_fits and (product.fit is None or product.fit in excluded_fits):
            continue
        if filters.sizes and not set(filters.sizes).intersection(product.sizes):
            continue
        result.append(product)
    return result


def parse_demo_intent(text: str, session_id: str, previous: Intent | None = None) -> Intent:
    """A small visible fallback: never invent attributes from an LLM response."""
    intent = previous.model_copy(deep=True) if previous else Intent(session_id=session_id)
    intent.session_id = session_id
    intent.source_text = text
    intent.semantic_query = text
    intent.needs_clarification = False
    intent.clarifying_question = None
    budget = re.search(r"(?:預算|總價|總預算|最多|以下|內)[^\d]{0,8}(\d{2,6})\s*(?:元|塊)?", text)
    if not budget:
        budget = re.search(r"(\d{2,6})\s*(?:元|塊)\s*(?:內|以下)", text)
    if not budget:
        budget = re.search(r"(\d{2,6})\s*(?:元|塊)?\s*(?:內|以下|以內)", text)
    if budget:
        intent.budget_total = int(budget.group(1))
        if "budget_total" not in intent.hard_constraints:
            intent.hard_constraints.append("budget_total")
    mentioned_colors: list[str] = []
    for phrase, color in (("黑", "black"), ("米色", "beige"), ("白", "white"), ("灰", "charcoal")):
        if phrase in text:
            if any(x in text for x in (f"不要{phrase}", f"不喜歡{phrase}", f"排除{phrase}")):
                if color not in intent.excluded.colors:
                    intent.excluded.colors.append(color)
                if "excluded.colors" not in intent.hard_constraints:
                    intent.hard_constraints.append("excluded.colors")
            else:
                mentioned_colors.append(color)
    if mentioned_colors and re.search(r"改成|換成|改為|換為", text):
        intent.preferred.colors = mentioned_colors
    else:
        for color in mentioned_colors:
            if color not in intent.preferred.colors:
                intent.preferred.colors.append(color)
    if "日系" in text and "japanese" not in intent.preferred.styles:
        intent.preferred.styles.append("japanese")
    if "寬鬆" in text and "relaxed" not in intent.preferred.fits:
        intent.preferred.fits.append("relaxed")
    if "不要太貼身" in text or "不要緊身" in text:
        if "slim" not in intent.excluded.fits:
            intent.excluded.fits.append("slim")
        if "excluded.fits" not in intent.hard_constraints:
            intent.hard_constraints.append("excluded.fits")
    if intent.preferred.styles:
        intent.soft_constraints = sorted(set(intent.soft_constraints + ["preferred.styles"]))
    if intent.preferred.colors:
        intent.soft_constraints = sorted(set(intent.soft_constraints + ["preferred.colors"]))
    if "戶外" in text:
        intent.occasion = sorted(set(intent.occasion + ["outdoor", "casual"]))
    if set(intent.preferred.colors) & set(intent.excluded.colors):
        intent.needs_clarification = True
        intent.clarifying_question = "你同時偏好並排除了同一顏色，請確認要保留哪一項？"
    return intent


class MockServices:
    def __init__(self, catalog: FixtureCatalog, store: EventStore):
        self.catalog = catalog
        self.store = store

    def profile(self, session_id: str, user_id: str) -> UserProfile:
        saved = self.store.get_profile(session_id)
        return UserProfile.model_validate({"user_id": user_id, **(saved or {})})

    def parse_intent(self, text: str, session_id: str, user_id: str) -> Intent:
        previous = self.store.get_intent(session_id)
        intent = parse_demo_intent(text, session_id, Intent.model_validate(previous) if previous else None)
        self.store.save_intent(session_id, user_id, intent.model_dump(mode="json"))
        return intent

    def search(self, request: SearchRequest, intent: Intent | None = None) -> SearchResponse:
        candidates = filter_products(self.catalog.products, request.filters, intent)
        query = request.query_text.casefold()
        terms = [t for t in re.split(r"[\s,，、；;]+", query) if t and not t.startswith(("不要", "排除", "不喜歡"))]
        hits = []
        for product in candidates:
            blob = (product.search_text + " " + product.name + " " + " ".join(product.styles + product.colors)).casefold()
            score = sum(1 for term in terms if term in blob) / max(len(terms), 1)
            if not terms or score > 0:
                hits.append(SearchHit(product_id=product.product_id, score=score, score_breakdown={"relevance": score}, warnings=["demo_only"], product=product))
        hits.sort(key=lambda h: (-h.score, h.product_id))
        return SearchResponse(session_id=request.session_id, mode=request.mode, products=hits[:request.limit], retrieval=RetrievalInfo(prefilter_count=len(candidates), text_candidates=len(hits), fusion_method="fixture_rules"))

    def recommend(self, intent: Intent, user_id: str, filters: SearchFilters) -> RecommendationResponse:
        products = filter_products(self.catalog.products, filters, intent)
        profile = self.profile(intent.session_id, user_id)
        by_category = {category: [p for p in products if p.category == category] for category in intent.required_categories}
        outfits: list[Outfit] = []
        if all(by_category.values()):
            # Fixture size is intentionally tiny; C owns production combination and scoring.
            from itertools import product
            for index, items in enumerate(product(*(by_category[c] for c in intent.required_categories))):
                total = sum(item.price for item in items)
                if intent.budget_total is not None and total > intent.budget_total:
                    continue
                style_hits = sum(bool(set(item.styles) & set(intent.preferred.styles)) for item in items)
                color_hits = sum(bool(set(item.colors) & set(intent.preferred.colors)) for item in items)
                relevance = (style_hits + color_hits) / max(2 * len(items), 1)
                weights = ([profile.preference_weights.get(f"style:{style}", 0) for item in items for style in item.styles] +
                           [profile.preference_weights.get(f"color:{color}", 0) for item in items for color in item.colors])
                preference = (sum(weights) / max(len(weights), 1) + 1) / 2
                score = round(0.65 * relevance + 0.35 * preference, 4)
                outfit = Outfit(outfit_id=f"demo-outfit-{index + 1}", items=list(items), total_price=total, score=score,
                                score_breakdown=ScoreBreakdown(relevance=relevance, preference=preference, compatibility=0, trend=0),
                                matched_constraints=list(intent.hard_constraints), warnings=["demo_only", "availability_unknown"])
                outfit.reason = build_explanation(outfit, intent)
                outfits.append(outfit)
        outfits.sort(key=lambda o: (-o.score, o.total_price, o.outfit_id))
        return RecommendationResponse(session_id=intent.session_id, intent=intent, outfits=outfits[:3], fallback_used=True,
                                      message="固定展示資料；商品價格與庫存不是即時資訊。")

    def feed(self, user_id: str, cursor: str | None, limit: int) -> FeedResponse:
        offset = int(cursor) if cursor else 0
        posts = self.catalog.posts[offset:offset + limit]
        items = [FeedItem(post_id=post.post_id, rank=offset + i + 1, ranking_reason=["editorial_demo"],
                          score_breakdown={"preference": 0, "social": 0, "exploration": 1}, post=post)
                 for i, post in enumerate(posts)]
        next_cursor = str(offset + len(posts)) if offset + len(posts) < len(self.catalog.posts) else None
        return FeedResponse(user_id=user_id, items=items, next_cursor=next_cursor)

    def record_interactions(self, events: list[InteractionEvent]) -> EventBatchResult:
        accepted = duplicates = 0
        for event in events:
            already_dwelled = (event.event_type == "dwell" and
                               self.store.has_qualifying_dwell(event.session_id, event.target_type, event.target_id))
            inserted = self.store.insert_event(event.model_dump(mode="json"))
            if not inserted:
                duplicates += 1
                continue
            accepted += 1
            if not event.is_foreground or event.event_type == "impression":
                continue
            if event.event_type == "dwell" and (event.dwell_ms or 0) < 2000:
                continue
            if already_dwelled and event.event_type == "dwell":
                continue
            self._apply_signal(event.session_id, event.user_id, event.target_type, event.target_id, event.event_type, event.dwell_ms)
        return EventBatchResult(accepted_count=accepted, duplicate_count=duplicates)

    def _apply_signal(self, session_id: str, user_id: str, target_type: str, target_id: str, event_type: str, dwell_ms: int | None = None) -> None:
        profile = self.profile(session_id, user_id)
        if target_type == "post":
            target = self.catalog.posts_by_id.get(target_id)
            attributes = ([f"style:{x}" for x in target.styles] + [f"color:{x}" for x in target.colors]) if target else []
        else:
            target = self.catalog.products_by_id.get(target_id)
            attributes = ([f"style:{x}" for x in target.styles] + [f"color:{x}" for x in target.colors]) if target else []
        if event_type == "dwell":
            delta = 0.05 if (dwell_ms or 0) >= 8000 else 0.02
        else:
            delta = {"post_open": 0.03, "like": 0.15 if target_type == "post" else 0.2,
                     "save": 0.2, "product_click": 0.1, "dislike": -0.3}.get(event_type, 0)
        for attribute in attributes:
            profile.preference_weights[attribute] = round(max(-1, min(1, profile.preference_weights.get(attribute, 0) + delta)), 3)
        profile.updated_at = datetime.now(timezone.utc)
        self.store.save_profile(session_id, user_id, profile.model_dump(mode="json"))

    def feedback(self, event: FeedbackEvent) -> tuple[UserProfile, bool]:
        for path in event.explicit_patch:
            if path not in {"excluded.colors", "preferred.colors", "excluded.fits", "preferred.styles", "preferred.fits"}:
                raise ValueError(f"unsupported explicit_patch path: {path}")
        if not self.store.insert_event(event.model_dump(mode="json")):
            return self.profile(event.session_id, event.user_id), True
        if event.target_type and event.target_id and event.event_type in {"like", "dislike"}:
            self._apply_signal(event.session_id, event.user_id, event.target_type, event.target_id, event.event_type)
        profile = self.profile(event.session_id, event.user_id)
        for path, values in event.explicit_patch.items():
            kind, field = path.split(".")
            for value in values:
                key = f"{field[:-1] if field.endswith('s') else field}:{value}"
                profile.preference_weights[key] = -1.0 if kind == "excluded" else 0.4
        profile.updated_at = datetime.now(timezone.utc)
        self.store.save_profile(event.session_id, event.user_id, profile.model_dump(mode="json"))
        return profile, False

    def insights(self) -> InsightsResponse:
        return InsightsResponse.model_validate(self.store.insights())
