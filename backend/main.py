"""E's FastAPI boundary: validate, orchestrate, translate errors, expose health."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import logging
import os
import sqlite3
from typing import Any

from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import ROOT, Settings
from .db import EventStore
from .explanation import build_explanation
from .firebase import initialize_firebase
from .feed_debug import build_debug_router
from .mock import FixtureCatalog, MockServices, filter_products, parse_demo_intent
from .search import embedding_runtime, get_embedding_store, infer_query_categories, rank_post_image_products, search_products
from .search_explanations import add_search_explanations, visual_search_explanations
from .schemas import (
    ErrorBody, ErrorResponse, EventBatchResult, FeedbackEvent, FeedbackResponse,
    FeedResponse, InsightsResponse, Intent, InteractionEvent, Outfit, PostDetail,
    RecommendRequest, RecommendationResponse, SearchRequest, SearchResponse, UserProfile,
    SearchFilters,
)

logger = logging.getLogger("outfit_api")
PATCH_PATHS = {"excluded.colors", "preferred.colors", "excluded.fits", "preferred.styles", "preferred.fits"}


class APIError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False, details: dict | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


def authenticated_user_id(authorization: str | None) -> str | None:
    """Verify a Firebase bearer token and return its uid when supplied."""
    required = os.getenv("FIREBASE_AUTH_REQUIRED", "false").lower() == "true"
    if not authorization:
        if required:
            raise APIError(401, "UNAUTHENTICATED", "請先登入後再使用推薦服務。")
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise APIError(401, "UNAUTHENTICATED", "Authorization 格式無效。")
    try:
        from firebase_admin import auth as firebase_auth

        initialize_firebase()
        uid = firebase_auth.verify_id_token(token).get("uid")
        if not uid:
            raise ValueError("missing uid")
        return uid
    except Exception as exc:
        if not required:
            # Local development may have the Firebase web SDK configured before
            # Firebase Admin credentials are installed. Keep the mock runtime
            # usable, but never use this mode in a deployed environment.
            return None
        raise APIError(401, "UNAUTHENTICATED", "Firebase 登入驗證失敗。") from exc


def error_response(status: int, code: str, message: str, retryable: bool = False, details: dict | None = None) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, retryable=retryable, details=details or {}))
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="Outfit demo API", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
    local_images = settings.data_dir / "images"
    if settings.data_dir.name != "combined" and local_images.is_dir():
        app.mount("/products/kaggle", StaticFiles(directory=local_images), name="catalog-images")
    catalog_error = db_error = None
    try:
        catalog = FixtureCatalog(settings.data_dir)
    except (OSError, ValueError) as exc:
        catalog = None
        catalog_error = type(exc).__name__
        logger.exception("catalog unavailable")
    try:
        store = EventStore(settings.db_path)
    except (OSError, ValueError, sqlite3.Error) as exc:
        store = None
        db_error = type(exc).__name__
        logger.exception("database unavailable")
    mock = MockServices(catalog, store) if catalog is not None and store is not None else None
    # Post-image retrieval is computed once per static post for the lifetime of
    # this process.  The first drawer open remains a real FashionCLIP image
    # query; caching prevents repeated clicks from re-encoding the same photo.
    post_image_results: dict[str, list] = {}
    image_catalog_products = catalog.products if catalog is not None else []
    image_catalog_by_id = {product.product_id: product for product in image_catalog_products}
    image_store = get_embedding_store()
    # The small fixture catalog intentionally has no product images or image
    # embeddings.  Its Pexels posts still need to be demonstrable, so retrieve
    # against the checked-in official catalog whenever the active catalog has
    # no compatible image vectors.
    if image_store and image_store.image_embeddings is not None and not any(
        image_store.contains(product.product_id) for product in image_catalog_products
    ):
        try:
            official_catalog = FixtureCatalog(ROOT / "data" / "catalog" / "combined")
            image_catalog_products = official_catalog.products
            image_catalog_by_id = official_catalog.products_by_id
        except (OSError, ValueError):
            logger.exception("official image catalog unavailable")

    @app.exception_handler(APIError)
    async def handle_api_error(_request: Request, exc: APIError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message, exc.retryable, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [".".join(str(x) for x in item["loc"]) for item in exc.errors()]
        return error_response(422, "INVALID_INPUT", "輸入欄位無效。", details={"fields": fields})

    @app.exception_handler(sqlite3.Error)
    async def handle_database_error(_request: Request, exc: sqlite3.Error) -> JSONResponse:
        logger.exception("database error")
        return error_response(503, "DATA_UNAVAILABLE", "資料庫暫時無法使用。", retryable=True)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled API error")
        return error_response(500, "INTERNAL_ERROR", "服務暫時無法處理請求。", retryable=True)

    def require_mock() -> MockServices:
        if mock is None:
            raise APIError(503, "DATA_UNAVAILABLE", "展示資料或資料庫無法使用。", True,
                           {"catalog": catalog_error, "database": db_error})
        return mock

    def searchable_products(filters: SearchFilters) -> list:
        products = filter_products(catalog.products, filters)
        # Official catalog categories are normalized during catalog build.
        # A product without a successfully fetched image has no
        # trustworthy visual vector and would render a broken storefront card.
        # Fixture products are retained for the explicit fixture test mode.
        if image_store and image_store.image_embeddings is not None:
            products = [product for product in products
                        if product.source != "official_brand_catalog" or image_store.contains(product.product_id)]
        return products

    def image_similar_products(post: Any) -> list:
        if post.post_id in post_image_results:
            return post_image_results[post.post_id]
        if not post.image_url:
            return []

        runtime = embedding_runtime()
        # Do not fill the drawer with arbitrary product-ID order if the real
        # encoder or its compatible product index is unavailable.
        if not runtime["store_compatible"]:
            return []

        store = get_embedding_store()
        candidates = [
            product for product in image_catalog_products
            if product.price is not None and product.availability == "available"
            and store and store.image_embeddings is not None and store.contains(product.product_id)
        ]
        if not candidates:
            return []
        try:
            selected = rank_post_image_products(
                image_input=str(post.image_url),
                regions=post.detected_regions,
                candidates=candidates,
                excluded_product_ids={tag.product_id for tag in post.tagged_products},
            )
        except Exception:
            logger.exception("post image retrieval failed for %s", post.post_id)
            return []

        post_image_results[post.post_id] = selected
        return selected

    def get_module(name: str) -> Any:
        try:
            return importlib.import_module(f"backend.{name}")
        except ModuleNotFoundError as exc:
            if exc.name == f"backend.{name}":
                raise APIError(503, "DATA_UNAVAILABLE", f"{name} 模組尚未接入。", True) from exc
            raise

    async def call_module(name: str, function: str, *args: Any) -> Any:
        module = get_module(name)
        func = getattr(module, function, None)
        if func is None:
            raise APIError(503, "DATA_UNAVAILABLE", f"{name}.{function} 尚未接入。", True)
        try:
            return await asyncio.wait_for(asyncio.to_thread(func, *args), timeout=settings.llm_timeout_seconds)
        except asyncio.TimeoutError as exc:
            raise APIError(504, "LLM_TIMEOUT" if name == "intent" else "DATA_UNAVAILABLE",
                           f"{name} 模組逾時。", True) from exc

    def apply_intent_patch(intent: Intent, patch: dict[str, list[str]]) -> Intent:
        updated = intent.model_copy(deep=True)
        for path, values in patch.items():
            if path not in PATCH_PATHS:
                raise APIError(422, "INVALID_INPUT", f"不支援的偏好欄位：{path}")
            group, field = path.split(".")
            target = getattr(getattr(updated, group), field)
            for value in values:
                if value not in target:
                    target.append(value)
            if group == "excluded" and path not in updated.hard_constraints:
                updated.hard_constraints.append(path)
        if set(updated.preferred.colors) & set(updated.excluded.colors):
            updated.needs_clarification = True
            updated.clarifying_question = "你同時偏好並排除了同一顏色，請確認要保留哪一項？"
        return updated

    async def feedback_patch(event: FeedbackEvent, previous: Intent | None) -> dict[str, list[str]]:
        if event.explicit_patch:
            patch = event.explicit_patch
        elif event.text:
            patch = None
            if settings.mode == "live":
                try:
                    parsed = await call_module("intent", "parse_feedback", event.text, previous or Intent(session_id=event.session_id))
                    if hasattr(parsed, "model_dump"):
                        parsed = parsed.model_dump(mode="json")
                    if isinstance(parsed, dict):
                        patch = parsed.get("explicit_patch", parsed)
                except APIError as exc:
                    if exc.code not in {"LLM_TIMEOUT", "DATA_UNAVAILABLE"}:
                        raise
            if patch is None:
                before = previous or Intent(session_id=event.session_id)
                after = parse_demo_intent(event.text, event.session_id, before)
                patch = {}
                for path in PATCH_PATHS:
                    group, field = path.split(".")
                    values = set(getattr(getattr(before, group), field))
                    additions = [x for x in getattr(getattr(after, group), field) if x not in values]
                    if additions:
                        patch[path] = additions
            if not patch:
                # Repeating an explicit preference with a new event ID remains valid.
                patch = {}
                standalone = parse_demo_intent(event.text, event.session_id)
                for path in PATCH_PATHS:
                    group, field = path.split(".")
                    values = getattr(getattr(standalone, group), field)
                    if values:
                        patch[path] = values
        else:
            patch = {}
        if not isinstance(patch, dict) or any(path not in PATCH_PATHS or not isinstance(values, list) for path, values in patch.items()):
            raise APIError(422, "INVALID_INPUT", "偏好更新格式無效。")
        if event.text and not patch and not event.target_id:
            raise APIError(422, "INVALID_INPUT", "無法從文字辨識偏好更新。")
        return patch

    async def live_outfits(intent: Intent, profile: UserProfile, filters: SearchFilters) -> list[Outfit]:
        candidates = filter_products(catalog.products, filters, intent)
        outfits = [Outfit.model_validate(x) for x in await call_module("recommender", "recommend", intent, profile, candidates)]
        candidate_ids = {product.product_id for product in candidates}
        for outfit in outfits:
            if intent.budget_total is not None and outfit.total_price > intent.budget_total:
                raise APIError(500, "INTERNAL_ERROR", "推薦結果違反總預算。")
            if set(intent.required_categories) - {item.category for item in outfit.items}:
                raise APIError(500, "INTERNAL_ERROR", "推薦結果缺少必要類別。")
            if (any(item.product_id not in candidate_ids for item in outfit.items) or
                    len({item.product_id for item in outfit.items}) != len(outfit.items) or
                    sum(item.price for item in outfit.items) != outfit.total_price):
                raise APIError(500, "INTERNAL_ERROR", "推薦結果違反商品或價格契約。")
            outfit.reason = build_explanation(outfit, intent)
        return outfits

    @app.get("/health")
    def health() -> dict:
        dependencies = {}
        if settings.mode == "live":
            for name in ("intent", "search", "recommender", "feedback", "events"):
                try:
                    get_module(name)
                    dependencies[name] = "available"
                except APIError:
                    dependencies[name] = "missing"
        else:
            dependencies = {"intent": "fixture", "search": "fixture", "recommender": "fixture", "feedback": "fixture", "events": "fixture"}
        return {"status": "ok" if mock is not None and (settings.mode == "mock" or all(x == "available" for x in dependencies.values())) else "degraded",
                "mode": settings.mode, "catalog": "ok" if catalog else "unavailable", "database": "ok" if store else "unavailable",
                "dependencies": dependencies}

    @app.get("/products/catalog/{product_id}.jpg")
    def catalog_image(product_id: str) -> Response:
        """Proxy catalog CDN images so product cards remain visible in-app."""
        product = image_catalog_by_id.get(product_id) or (catalog.products_by_id.get(product_id) if catalog else None)
        image_urls = dict.fromkeys(
            str(url) for url in ([product.image_url, *product.image_urls] if product else []) if url
        )
        if not any(url.startswith(("http://", "https://")) for url in image_urls):
            raise APIError(404, "DATA_UNAVAILABLE", "找不到商品圖片。")
        import requests

        for image_url in image_urls:
            if not image_url.startswith(("http://", "https://")):
                continue
            cache_name = hashlib.sha256(image_url.encode("utf-8")).hexdigest() + ".jpg"
            cache_file = ROOT / "data" / "embeddings" / "official_products" / ".cache_images" / cache_name
            if cache_file.is_file():
                return FileResponse(cache_file, media_type="image/jpeg",
                                    headers={"Cache-Control": "public, max-age=86400"})
            try:
                upstream = requests.get(
                    image_url, timeout=(3, 6),
                    headers={"User-Agent": "Mozilla/5.0 (compatible; OutfitDemo/1.0)"},
                )
                upstream.raise_for_status()
                media_type = upstream.headers.get("content-type", "")
                if media_type.startswith("image/"):
                    return Response(
                        content=upstream.content,
                        media_type=media_type,
                        headers={"Cache-Control": "public, max-age=86400"},
                    )
            except requests.RequestException:
                logger.warning("catalog image unavailable for %s", product_id)
        raise APIError(502, "DATA_UNAVAILABLE", "商品圖片暫時無法載入。", True)

    @app.post("/api/v1/recommend", response_model=RecommendationResponse)
    async def recommend(request: RecommendRequest,
                        authorization: str | None = Header(default=None)) -> RecommendationResponse:
        verified_uid = authenticated_user_id(authorization)
        if verified_uid:
            request = request.model_copy(update={"user_id": verified_uid})
        if request.image is not None:
            raise APIError(422, "INVALID_INPUT", "圖片搜尋屬 P1，目前只支援文字。")
        service = require_mock()
        if settings.mode == "mock":
            intent = service.parse_intent(request.text, request.session_id, request.user_id, origin="recommend")
            if intent.needs_clarification:
                return RecommendationResponse(session_id=request.session_id, intent=intent, fallback_used=True, message=intent.clarifying_question)
            result = service.recommend(intent, request.user_id, request.filters)
        else:
            previous_data = store.get_intent(request.session_id) if store else None
            previous = Intent.model_validate(previous_data) if previous_data else None
            fallback_used = False
            try:
                parsed = await call_module("intent", "parse_intent", request.text, previous)
                if isinstance(parsed, dict):
                    parsed = {"session_id": request.session_id, **parsed}
                intent = Intent.model_validate(parsed)
            except (APIError, ValueError) as exc:
                if isinstance(exc, APIError) and exc.code != "LLM_TIMEOUT" and exc.code != "DATA_UNAVAILABLE":
                    raise
                intent = parse_demo_intent(request.text, request.session_id, previous)
                fallback_used = True
            intent.session_id = request.session_id
            intent.origin = "recommend"
            store.save_intent(request.session_id, request.user_id, intent.model_dump(mode="json"))
            if intent.needs_clarification:
                return RecommendationResponse(session_id=request.session_id, intent=intent, fallback_used=fallback_used, message=intent.clarifying_question)
            profile = UserProfile.model_validate(await call_module("feedback", "get_profile", request.user_id))
            outfits = await live_outfits(intent, profile, request.filters)
            result = RecommendationResponse(session_id=request.session_id, intent=intent, outfits=outfits, fallback_used=fallback_used)
        if not result.outfits:
            raise APIError(422, "NO_MATCHING_PRODUCTS", "目前沒有同時符合條件的完整穿搭。", details={"failed_constraints": intent.hard_constraints})
        return result

    @app.post("/api/v1/search", response_model=SearchResponse)
    async def search(request: SearchRequest) -> SearchResponse:
        has_text = bool(request.query_text.strip())
        has_filters = bool(
            request.filters.categories or request.filters.price_max is not None or
            request.filters.available_only or request.filters.excluded_colors or
            request.filters.excluded_fits or request.filters.sizes
        )
        if request.mode in {"image", "mixed"} and not request.query_image:
            raise APIError(422, "INVALID_INPUT", "圖片或圖文搜尋需要 query_image。")
        if request.mode == "mixed" and not has_text:
            raise APIError(422, "INVALID_INPUT", "文字或圖文搜尋需要 query_text。")
        if request.mode == "text" and not has_text and not has_filters:
            raise APIError(422, "INVALID_INPUT", "請輸入搜尋文字，或至少選擇一項篩選條件。")
        service = require_mock()
        session_data = store.get_intent(request.session_id) if store else None
        previous_intent = Intent.model_validate(session_data) if session_data else None
        if has_text:
            try:
                parsed = await call_module("intent", "parse_intent", request.query_text, previous_intent)
                if isinstance(parsed, dict):
                    parsed = {"session_id": request.session_id, **parsed}
                query_intent = Intent.model_validate(parsed)
            except (APIError, ValueError) as exc:
                if isinstance(exc, APIError) and exc.code not in {"LLM_TIMEOUT", "DATA_UNAVAILABLE"}:
                    raise
                query_intent = parse_demo_intent(request.query_text, request.session_id, previous_intent)
        else:
            query_intent = Intent(session_id=request.session_id)
        query_intent.session_id = request.session_id
        query_intent.origin = "search"
        if store:
            store.save_intent(request.session_id, "anonymous-demo", query_intent.model_dump(mode="json"))
        merged = request.model_copy(deep=True)
        if has_text and not merged.filters.categories:
            merged.filters.categories = infer_query_categories(request.query_text)
        merged.filters.excluded_colors = sorted(set(merged.filters.excluded_colors + query_intent.excluded.colors))
        merged.filters.excluded_fits = sorted(set(merged.filters.excluded_fits + query_intent.excluded.fits))
        if query_intent.budget_total is not None and "budget_total" in query_intent.hard_constraints:
            limit = query_intent.budget_total
            merged.filters.price_max = min(merged.filters.price_max, limit) if merged.filters.price_max is not None else limit
        if previous_intent:
            session_intent = previous_intent
            merged.filters.excluded_colors = sorted(set(merged.filters.excluded_colors + session_intent.excluded.colors))
            merged.filters.excluded_fits = sorted(set(merged.filters.excluded_fits + session_intent.excluded.fits))
        if settings.mode == "mock":
            candidates = searchable_products(merged.filters)
            response = search_products(merged, candidates)
            return await asyncio.to_thread(add_search_explanations, response, query_intent.semantic_query)
        candidates = searchable_products(merged.filters)
        response = SearchResponse.model_validate(await call_module("search", "search_products", merged, candidates))
        product_ids = {p.product_id for p in candidates}
        for hit in response.products:
            if hit.product_id not in product_ids:
                raise APIError(500, "INTERNAL_ERROR", "搜尋結果違反硬篩選。")
            hit.product = catalog.products_by_id[hit.product_id]
        return await asyncio.to_thread(add_search_explanations, response, query_intent.semantic_query)

    app.include_router(build_debug_router(require_mock))

    @app.get("/api/v1/feed", response_model=FeedResponse)
    def feed(user_id: str = "anonymous-demo", session_id: str | None = None,
             cursor: str | None = None, limit: int = Query(20, ge=1, le=100),
             authorization: str | None = Header(default=None)) -> FeedResponse:
        verified_uid = authenticated_user_id(authorization)
        if verified_uid:
            user_id = verified_uid
        if cursor is not None and (not cursor.isdigit() or int(cursor) > 1000000):
            raise APIError(422, "INVALID_INPUT", "cursor 無效。")
        return require_mock().feed(user_id, session_id, cursor, limit)

    @app.get("/api/v1/posts/{post_id}", response_model=PostDetail)
    def post_detail(post_id: str) -> PostDetail:
        detail = require_mock().catalog.post_detail(post_id)
        if detail is None:
            raise APIError(404, "DATA_UNAVAILABLE", "找不到這篇貼文。")
        similar_products = image_similar_products(detail.post)
        explanations, sources = visual_search_explanations(
            similar_products, [region.label for region in detail.post.detected_regions],
        )
        return detail.model_copy(update={
            "similar_products": similar_products,
            "similar_product_explanations": explanations,
            "similar_product_explanation_sources": sources,
        })

    @app.post("/api/v1/events/batch", response_model=EventBatchResult)
    async def events_batch(events: list[InteractionEvent],
                           authorization: str | None = Header(default=None)) -> EventBatchResult:
        verified_uid = authenticated_user_id(authorization)
        if verified_uid:
            events = [event.model_copy(update={"user_id": verified_uid}) for event in events]
        if len(events) > 100:
            raise APIError(422, "INVALID_INPUT", "一次最多上報 100 個事件。")
        for event in events:
            if event.target_type == "post" and event.target_id not in require_mock().catalog.posts_by_id:
                raise APIError(422, "INVALID_INPUT", "事件貼文不存在。")
            if event.target_type == "product" and event.target_id not in require_mock().catalog.products_by_id:
                raise APIError(422, "INVALID_INPUT", "事件商品不存在。")
        events = [event.model_copy(update={"dwell_ms": min(event.dwell_ms, 30000)})
                  if event.dwell_ms is not None else event for event in events]
        if settings.mode == "mock":
            return require_mock().record_interactions(events)
        return EventBatchResult.model_validate(await call_module("events", "record_interactions", events))

    @app.post("/api/v1/feedback", response_model=FeedbackResponse)
    async def feedback(event: FeedbackEvent,
                       authorization: str | None = Header(default=None)) -> FeedbackResponse:
        verified_uid = authenticated_user_id(authorization)
        if verified_uid:
            event = event.model_copy(update={"user_id": verified_uid})
        if event.remember_preference:
            raise APIError(422, "INVALID_INPUT", "P0 只支援 session 偏好；長期偏好尚未啟用。")
        if event.target_type == "post" and event.target_id not in require_mock().catalog.posts_by_id:
            raise APIError(422, "INVALID_INPUT", "回饋貼文不存在。")
        if event.target_type == "product" and event.target_id not in require_mock().catalog.products_by_id:
            raise APIError(422, "INVALID_INPUT", "回饋商品不存在。")
        if settings.mode == "mock" and require_mock().store.has_event_id(event.event_id):
            return FeedbackResponse(profile=require_mock().profile(event.session_id, event.user_id), duplicate=True)
        previous_data = store.get_intent(event.session_id) if store else None
        previous = Intent.model_validate(previous_data) if previous_data else None
        patch = await feedback_patch(event, previous)
        event = event.model_copy(update={"explicit_patch": patch})
        if settings.mode == "mock":
            service = require_mock()
            try:
                profile, duplicate = service.feedback(event)
            except ValueError as exc:
                raise APIError(422, "INVALID_INPUT", str(exc)) from exc
            recommendation = None
            if previous and not duplicate:
                intent = apply_intent_patch(previous, patch)
                service.store.save_intent(event.session_id, event.user_id, intent.model_dump(mode="json"))
                if not intent.needs_clarification:
                    recommendation = service.recommend(intent, event.user_id, SearchFilters())
            return FeedbackResponse(profile=profile, recommendation=recommendation, duplicate=duplicate)
        profile = UserProfile.model_validate(await call_module("feedback", "record_feedback", event))
        recommendation = None
        if previous:
            intent = apply_intent_patch(previous, patch)
            store.save_intent(event.session_id, event.user_id, intent.model_dump(mode="json"))
            if not intent.needs_clarification:
                outfits = await live_outfits(intent, profile, SearchFilters())
                recommendation = RecommendationResponse(session_id=event.session_id, intent=intent, outfits=outfits)
        return FeedbackResponse(profile=profile, recommendation=recommendation)

    @app.get("/api/v1/profile/{user_id}", response_model=UserProfile)
    async def profile(user_id: str, session_id: str | None = None) -> UserProfile:
        if settings.mode == "mock":
            return require_mock().profile(session_id or user_id, user_id)
        return UserProfile.model_validate(await call_module("feedback", "get_profile", user_id))

    @app.post("/api/v1/session/{session_id}/reset")
    async def reset(session_id: str) -> dict:
        if settings.mode == "mock":
            require_mock().store.reset(session_id)
        else:
            await call_module("feedback", "reset_session", session_id)
        return {"session_id": session_id, "reset": True}

    @app.get("/api/v1/insights", response_model=InsightsResponse)
    async def insights() -> InsightsResponse:
        if settings.mode == "mock":
            return require_mock().insights()
        return InsightsResponse.model_validate(await call_module("feedback", "get_insights"))

    built_frontend = ROOT / "frontend" / "dist"
    if built_frontend.is_dir():
        app.mount("/", StaticFiles(directory=built_frontend, html=True), name="frontend")

    return app


app = create_app()
