"""Clearly labelled fixture service for frontend work before B/C/D land.

This is deterministic demo behavior, not a replacement for the owning modules.
"""

from __future__ import annotations

import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from .db import EventStore
from .explanation import build_explanation
from .intent import parse_intent as parse_structured_intent
from .post_feed import PROFILE_SIGNAL_WEIGHTS, rank_feed, update_profile
from .schemas import (
    Creator, EventBatchResult, FeedbackEvent, FeedResponse, InsightsResponse,
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
    fit_applicable_categories = {"top", "bottom", "outerwear", "dress", "set"}
    excluded_colors = set(filters.excluded_colors) | (set(intent.excluded.colors) if intent else set())
    excluded_fits = set(filters.excluded_fits) | (set(intent.excluded.fits) if intent else set())
    result = []
    for product in products:
        if filters.categories and product.category not in filters.categories:
            continue
        if filters.price_max is not None and (product.price is None or product.price > filters.price_max):
            continue
        if filters.available_only and product.availability != "available":
            continue
        if excluded_colors and (not product.colors or excluded_colors.intersection(product.colors)):
            continue
        if (excluded_fits and product.category in fit_applicable_categories and
                (product.fit is None or product.fit in excluded_fits)):
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


def intent_to_session_weights(intent: Intent | None) -> dict[str, float]:
    """Translate the current query intent into post-ranking attributes."""
    if intent is None:
        return {}

    weights: dict[str, float] = {}
    for value in intent.preferred.styles:
        weights[f"style:{value}"] = 1.0
    for value in intent.preferred.colors:
        weights[f"color:{value}"] = 1.0
    for value in intent.occasion:
        weights[f"occasion:{value}"] = 1.0
    for value in intent.excluded.colors:
        weights[f"color:{value}"] = -1.0
    return weights


class MockServices:
    def __init__(self, catalog: FixtureCatalog, store: EventStore):
        self.catalog = catalog
        self.store = store

    def profile(self, session_id: str, user_id: str) -> UserProfile:
        # Long-term preferences belong to an account, while intent remains
        # session-scoped. The session lookup is only a migration fallback for
        # existing local demo databases.
        saved = self.store.get_user_profile(user_id) or self.store.get_profile(session_id)
        return UserProfile.model_validate({"user_id": user_id, **(saved or {})})

    def parse_intent(self, text: str, session_id: str, user_id: str) -> Intent:
        previous_data = self.store.get_intent(session_id)
        previous = Intent.model_validate(previous_data) if previous_data else None
        parsed = parse_structured_intent(text, previous)
        intent = Intent.model_validate({"session_id": session_id, **parsed})
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
        products = [product for product in filter_products(self.catalog.products, filters, intent)
                    if product.price is not None and (intent.budget_total is None or product.price <= intent.budget_total)]
        profile = self.profile(intent.session_id, user_id)
        def priority(item: Product) -> tuple[float, int, str]:
            matches = (bool(set(item.styles) & set(intent.preferred.styles)) +
                       bool(set(item.colors) & set(intent.preferred.colors)) +
                       bool(item.fit and item.fit in intent.preferred.fits))
            preference = sum(profile.preference_weights.get(f"style:{style}", 0) for style in item.styles)
            preference += sum(profile.preference_weights.get(f"color:{color}", 0) for color in item.colors)
            return (-(matches + 0.35 * preference), item.price, item.product_id)

        by_category = {category: sorted((p for p in products if p.category == category), key=priority)[:10]
                       for category in intent.required_categories}
        outfits: list[Outfit] = []
        if all(by_category.values()):
            from itertools import product
            for items in product(*(by_category[c] for c in intent.required_categories)):
                total = sum(item.price for item in items)
                if intent.budget_total is not None and total > intent.budget_total:
                    continue
                style_hits = sum(bool(set(item.styles) & set(intent.preferred.styles)) for item in items)
                color_hits = sum(bool(set(item.colors) & set(intent.preferred.colors)) for item in items)
                fit_hits = sum(bool(item.fit and item.fit in intent.preferred.fits) for item in items)
                active_dimensions = sum(bool(values) for values in (intent.preferred.styles, intent.preferred.colors, intent.preferred.fits))
                relevance = (style_hits + color_hits + fit_hits) / max(active_dimensions * len(items), 1)
                weights = ([profile.preference_weights.get(f"style:{style}", 0) for item in items for style in item.styles] +
                           [profile.preference_weights.get(f"color:{color}", 0) for item in items for color in item.colors])
                preference = (sum(weights) / max(len(weights), 1) + 1) / 2
                score = round(0.65 * relevance + 0.35 * preference, 4)
                outfit_key = "|".join(item.product_id for item in items)
                outfit_id = "demo-outfit-" + hashlib.sha1(outfit_key.encode()).hexdigest()[:12]
                warnings = ["demo_only"] if any(item.availability == "demo_only" for item in items) else []
                if any(item.availability in {"unknown", "demo_only"} for item in items):
                    warnings.append("availability_unknown")
                outfit = Outfit(outfit_id=outfit_id, items=list(items), total_price=total, score=score,
                                score_breakdown=ScoreBreakdown(relevance=relevance, preference=preference, compatibility=0, trend=0),
                                matched_constraints=list(intent.hard_constraints), warnings=warnings)
                outfit.reason = build_explanation(outfit, intent)
                outfits.append(outfit)
        outfits.sort(key=lambda o: (-o.score, o.total_price, o.outfit_id))
        distinct_outfits = []
        seen_product_pages = set()
        for outfit in outfits:
            pages = tuple(str(item.product_url or item.product_id) for item in outfit.items)
            if pages in seen_product_pages:
                continue
            seen_product_pages.add(pages)
            distinct_outfits.append(outfit)
            if len(distinct_outfits) == 3:
                break
        return RecommendationResponse(session_id=intent.session_id, intent=intent, outfits=distinct_outfits, fallback_used=True,
                                      message="商品資料為展示快照；價格與庫存可能變動。")

    def feed(self, user_id: str, session_id: str | None, cursor: str | None, limit: int) -> FeedResponse:
        offset = int(cursor) if cursor else 0
        profile = self.profile(session_id, user_id) if session_id else UserProfile(user_id=user_id)
        events = self.store.list_user_events(user_id)
        intent_data = self.store.get_intent(session_id) if session_id else None
        intent = Intent.model_validate(intent_data) if intent_data else None
        session_weights = intent_to_session_weights(intent)
        ranked = rank_feed(user_id=user_id, posts=self.catalog.posts, profile=profile,
                           events=events, limit=len(self.catalog.posts),
                           session_weights=session_weights,
                           external_trend_scores=self.store.trend_scores())
        seen_post_ids = {
            event.get("target_id")
            for event in events
            if event.get("event_type") == "impression"
            and event.get("target_type") == "post"
            and event.get("is_foreground", True)
        }
        unseen_items = [item for item in ranked.items if item.post_id not in seen_post_ids]
        page = unseen_items[offset:offset + limit]
        for i, item in enumerate(page):
            item.rank = offset + i + 1
            if item.post is not None:
                item.creator = self.catalog.creators_by_id[item.post.creator_id]
        next_cursor = str(offset + len(page)) if offset + len(page) < len(unseen_items) else None
        return FeedResponse(user_id=user_id, items=page, next_cursor=next_cursor,
                            profile_version=profile.profile_version)

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
        # Single source of truth for signal -> preference-weight deltas is
        # post_feed.PROFILE_SIGNAL_WEIGHTS; this used to be reimplemented here with a
        # stale, smaller signal set (no follow/not_interested/hide/quick_skip and a
        # different dwell threshold constant).
        profile = self.profile(session_id, user_id)
        signal_type = event_type
        if event_type == "dwell":
            signal_type = "dwell_8s_plus" if (dwell_ms or 0) >= 8000 else "dwell_2_8s"
        if signal_type not in PROFILE_SIGNAL_WEIGHTS:
            return
        if target_type == "post":
            post = self.catalog.posts_by_id.get(target_id)
            if post is None:
                return
            profile = update_profile(profile, post, signal_type)
        else:
            product = self.catalog.products_by_id.get(target_id)
            attributes = ([f"style:{x}" for x in product.styles] + [f"color:{x}" for x in product.colors]) if product else []
            weight = PROFILE_SIGNAL_WEIGHTS[signal_type]
            for attribute in attributes:
                profile.preference_weights[attribute] = round(max(-1, min(1, profile.preference_weights.get(attribute, 0) + weight)), 3)
            profile.profile_version += 1
            profile.updated_at = datetime.now(timezone.utc)
        self.store.save_user_profile(user_id, profile.model_dump(mode="json"))

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
        self.store.save_user_profile(event.user_id, profile.model_dump(mode="json"))
        return profile, False

    def insights(self) -> InsightsResponse:
        return InsightsResponse.model_validate(self.store.insights())
