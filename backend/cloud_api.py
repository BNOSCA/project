"""Firestore-primary API. No local fallback for account data."""

from __future__ import annotations

import logging
import uuid
import time
from threading import Lock
from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .analytics import build_admin_insights
from .cloud_store import CloudCatalog, CloudServices, CloudStore, key
from .config import ROOT
from .firebase import get_firestore_client, initialize_firebase
from .mock import filter_products, parse_demo_intent
from .schemas import FeedbackEvent, FeedbackResponse, InteractionEvent, Intent, Post, RecommendRequest, SearchRequest, UserProfile
from .search import search_products

logger = logging.getLogger(__name__)
STYLES = {"japanese", "korean", "minimal", "streetwear", "casual", "outdoor", "sporty", "vintage", "preppy", "techwear", "old_money"}


class Onboarding(BaseModel):
    age_range: Literal["18-24", "25-34", "35-44", "45+", "不透露"]
    preferred_styles: list[str] = Field(max_length=11)


class PublicProfile(BaseModel):
    displayName: str = Field(min_length=1, max_length=40)
    username: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9._]+$")
    bio: str = Field(default="", max_length=160)
    avatarUrl: str | None = None


class PostStateChange(BaseModel):
    event_id: str = Field(min_length=1, max_length=200)
    session_id: str = Field(min_length=1, max_length=200)
    field: Literal["liked", "saved"]
    value: bool


class PublishRequest(BaseModel):
    post_id: str = Field(pattern=r"^post-user-[a-f0-9-]{36}$")
    caption: str = Field(max_length=500)
    image_path: str


def create_cloud_app(settings):
    app = FastAPI(title="LOOP Firestore API")
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_methods=["GET", "POST", "PUT"], allow_headers=["Content-Type", "Authorization"])
    catalog_cache = {"value": None, "expires": 0.0}
    catalog_lock = Lock()

    @app.exception_handler(HTTPException)
    async def http_error(_request, exc):
        return JSONResponse(status_code=exc.status_code, content={"error": {"message": str(exc.detail)}})

    @app.exception_handler(Exception)
    async def cloud_error(_request, exc):
        logger.exception("Cloud operation failed", exc_info=exc)
        return JSONResponse(status_code=503, content={"error": {
            "code": "CLOUD_UNAVAILABLE", "message": "雲端資料暫時無法存取，請稍後重試。", "retryable": True}})

    def uid(authorization: str | None = Header(default=None)):
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(401, "請先登入")
        from firebase_admin import auth
        try:
            app_instance = initialize_firebase()
            if not app_instance.project_id:
                raise HTTPException(503, "後端 Firebase 專案尚未設定")
            claims = auth.verify_id_token(authorization.split(" ", 1)[1])
            if claims.get("firebase", {}).get("sign_in_provider") == "anonymous":
                raise HTTPException(401, "請使用正式帳號登入")
            return claims["uid"]
        except HTTPException:
            raise
        except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError, auth.RevokedIdTokenError):
            raise HTTPException(401, "登入驗證失敗，請重新登入")

    def admin(user_id=Depends(uid)):
        if user_id not in settings.admin_uids:
            raise HTTPException(403, "你沒有管理洞察權限")
        return user_id

    def service(user_id):
        client = get_firestore_client()
        with catalog_lock:
            if catalog_cache["value"] is None or time.monotonic() >= catalog_cache["expires"]:
                catalog_cache["value"] = CloudCatalog(client)
                catalog_cache["expires"] = time.monotonic() + 30
        return CloudServices(catalog_cache["value"], CloudStore(client, user_id))

    def require_target(svc, target_type, target_id):
        values = svc.catalog.posts_by_id if target_type == "post" else svc.catalog.products_by_id
        if target_id not in values:
            raise HTTPException(404, "找不到貼文或商品")

    @app.get("/health")
    def health():
        try:
            client = get_firestore_client()
            client.document("system/readiness").get(timeout=5, retry=None)
            return {"status": "ok", "storage": "firestore", "project_id": client.project}
        except Exception as exc:
            logger.warning("Firestore readiness failed: %s", type(exc).__name__)
            return JSONResponse(status_code=503, content={"status": "degraded", "storage": "firestore",
                                                         "error": type(exc).__name__})

    @app.get("/api/v1/admin/status")
    def status(user_id=Depends(uid)):
        return {"is_admin": user_id in settings.admin_uids}

    @app.get("/api/v1/admin/insights")
    def insights(_user_id=Depends(admin)):
        return build_admin_insights()

    @app.get("/api/v1/me")
    def me(user_id=Depends(uid)):
        client = get_firestore_client()
        profile = client.document(f"users/{user_id}").get().to_dict()
        states = [doc.to_dict() for doc in client.collection(f"users/{user_id}/post_states").stream()]
        return {"profile": profile, "liked_ids": [s["post_id"] for s in states if s.get("liked")],
                "saved_ids": [s["post_id"] for s in states if s.get("saved")]}

    @app.put("/api/v1/me/onboarding")
    def onboarding(body: Onboarding, user_id=Depends(uid)):
        if set(body.preferred_styles) - STYLES:
            raise HTTPException(422, "不支援的風格")
        data = {**body.model_dump(), "preferred_styles": list(dict.fromkeys(body.preferred_styles)),
                "user_id": user_id, "onboarding_completed": True, "updated_at": datetime.now(timezone.utc)}
        get_firestore_client().document(f"users/{user_id}").set(data, merge=True)
        return data

    @app.put("/api/v1/me/public-profile")
    def public_profile(body: PublicProfile, user_id=Depends(uid)):
        if body.avatarUrl and not body.avatarUrl.startswith("https://"):
            raise HTTPException(422, "頭像網址必須使用 HTTPS")
        client = get_firestore_client()
        batch = client.batch()
        batch.set(client.document(f"users/{user_id}"), {"user_id": user_id, "public_profile": body.model_dump()}, merge=True)
        batch.set(client.document(f"creators/{user_id}"), {"creator_id": user_id,
                  "display_name": body.displayName, "is_demo": False}, merge=True)
        batch.commit()
        catalog_cache["expires"] = 0.0
        return body

    @app.get("/api/v1/feed")
    def feed(session_id: str = "default", cursor: str | None = None,
             limit: int = Query(20, ge=1, le=100), user_id=Depends(uid)):
        if cursor is not None and (not cursor.isdigit() or int(cursor) > 1000000):
            raise HTTPException(422, "無效的游標")
        svc = service(user_id)
        result = svc.feed(user_id, session_id, cursor, limit)
        # Delivery and actual exposure are deliberately separate records.
        svc.store.write(f"recommendation_runs/{uuid.uuid4()}", {
            "user_id": user_id, "session_id": session_id, "kind": "feed",
            "created_at": datetime.now(timezone.utc), "profile_version": result.profile_version,
            "items": [{"post_id": item.post_id, "score": item.score} for item in result.items]})
        return result

    @app.get("/api/v1/posts/{post_id}")
    def detail(post_id: str, user_id=Depends(uid)):
        result = service(user_id).catalog.post_detail(post_id)
        if result is None:
            raise HTTPException(404, "找不到貼文")
        return result

    @app.get("/api/v1/me/posts")
    def my_posts(kind: Literal["saved", "liked", "own"] = "saved", user_id=Depends(uid)):
        svc = service(user_id)
        if kind == "own":
            posts = [p for p in svc.catalog.posts if p.creator_id == user_id]
        else:
            states = me(user_id)
            ids = set(states["saved_ids" if kind == "saved" else "liked_ids"])
            posts = [p for p in svc.catalog.posts if p.post_id in ids]
        return {"items": [{"post": p, "score": 0, "creator": svc.catalog.creators_by_id.get(p.creator_id)}
                          for p in posts]}

    @app.post("/api/v1/events/batch")
    def events(body: list[InteractionEvent], user_id=Depends(uid)):
        if len(body) > 50:
            raise HTTPException(422, "每次最多 50 個事件")
        svc = service(user_id)
        normalized = []
        for event in body:
            require_target(svc, event.target_type, event.target_id)
            normalized.append(event.model_copy(update={"user_id": user_id,
                "dwell_ms": min(event.dwell_ms, 30000) if event.dwell_ms is not None else None,
                "created_at": datetime.now(timezone.utc)}))
        return svc.record_interactions(normalized)

    @app.put("/api/v1/me/posts/{post_id}/state")
    def state(post_id: str, body: PostStateChange, user_id=Depends(uid)):
        svc = service(user_id)
        require_target(svc, "post", post_id)
        def apply(store):
            path = f"users/{user_id}/post_states/{key(post_id)}"
            current = store.read(path) or {"post_id": post_id}
            if store.has_event_id(body.event_id) or bool(current.get(body.field)) == body.value:
                return current
            kind = ("like" if body.value else "unlike") if body.field == "liked" else ("save" if body.value else "unsave")
            event = InteractionEvent(event_id=body.event_id, user_id=user_id, session_id=body.session_id,
                                     event_type=kind, target_type="post", target_id=post_id)
            from .mock import MockServices
            MockServices(svc.catalog, store).record_interactions([event])
            return store.read(path)
        return svc.store.atomic(apply)

    @app.post("/api/v1/recommend")
    def recommend(body: RecommendRequest, user_id=Depends(uid)):
        if body.image:
            raise HTTPException(422, "目前只支援文字需求")
        svc = service(user_id)
        intent = svc.parse_intent(body.text, body.session_id, user_id)
        result = svc.recommend(intent, user_id, body.filters)
        svc.store.write(f"recommendation_runs/{uuid.uuid4()}", {"user_id": user_id,
            "kind": "outfits", "created_at": datetime.now(timezone.utc), **result.model_dump(mode="json")})
        return result

    @app.post("/api/v1/search")
    def search(body: SearchRequest, user_id=Depends(uid)):
        if body.mode in {"text", "mixed"} and not body.query_text.strip():
            raise HTTPException(422, "請輸入文字搜尋條件")
        if body.mode in {"image", "mixed"} and not body.query_image:
            raise HTTPException(422, "請提供搜尋圖片")
        svc = service(user_id)
        intent = parse_demo_intent(body.query_text, body.session_id)
        previous = svc.store.get_intent(body.session_id)
        filters = body.filters.model_copy(deep=True)
        filters.excluded_colors = list(set(filters.excluded_colors + intent.excluded.colors +
            (Intent.model_validate(previous).excluded.colors if previous else [])))
        filters.excluded_fits = list(set(filters.excluded_fits + intent.excluded.fits +
            (Intent.model_validate(previous).excluded.fits if previous else [])))
        if intent.budget_total is not None:
            filters.price_max = min(filters.price_max, intent.budget_total) if filters.price_max is not None else intent.budget_total
        result = search_products(body.model_copy(update={"filters": filters}), filter_products(svc.catalog.products, filters))
        svc.store.write(f"search_history/{uuid.uuid4()}", {"user_id": user_id,
            "session_id": body.session_id, "query": body.query_text, "filters": filters.model_dump(),
            "created_at": datetime.now(timezone.utc), "result_ids": [p.product_id for p in result.products]})
        return result

    @app.post("/api/v1/feedback")
    def feedback(body: FeedbackEvent, user_id=Depends(uid)):
        svc = service(user_id)
        if body.target_id:
            require_target(svc, body.target_type, body.target_id)
        patch = body.explicit_patch
        if body.text and not patch:
            parsed = parse_demo_intent(body.text, body.session_id)
            patch = {f"{group}.{field}": values for group in ("preferred", "excluded")
                     for field, values in getattr(parsed, group).model_dump().items()
                     if values and field in {"colors", "fits", "styles"} and not (group == "excluded" and field == "styles")}
            if not patch:
                raise HTTPException(422, "無法辨識偏好")
        event = body.model_copy(update={"user_id": user_id, "explicit_patch": patch,
                                       "created_at": datetime.now(timezone.utc)})
        try:
            profile, duplicate = svc.feedback(event)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return FeedbackResponse(profile=profile, duplicate=duplicate)

    @app.get("/api/v1/profile/{requested_uid}")
    def profile(requested_uid: str, user_id=Depends(uid)):
        if requested_uid != user_id:
            raise HTTPException(403, "只能讀取自己的偏好")
        return UserProfile.model_validate(CloudStore(get_firestore_client(), user_id).get_user_profile(user_id))

    @app.post("/api/v1/session/{session_id}/reset")
    def reset(session_id: str, user_id=Depends(uid)):
        store = CloudStore(get_firestore_client(), user_id)
        store.client.document(store.session_path(session_id)).delete()
        return {"session_id": session_id, "reset": True}

    @app.post("/api/v1/me/posts")
    def publish(body: PublishRequest, user_id=Depends(uid)):
        from firebase_admin import storage
        expected = f"uploads/{user_id}/{body.post_id}"
        if body.image_path != expected:
            raise HTTPException(422, "圖片路徑不符合目前帳號")
        blob = storage.bucket().blob(expected)
        blob.reload()
        if blob.content_type not in {"image/jpeg", "image/png", "image/webp"} or (blob.size or 0) > 10 * 1024 * 1024:
            raise HTTPException(422, "圖片格式或大小不符合限制")
        client = get_firestore_client()
        existing = client.document(f"posts/{body.post_id}").get()
        if existing.exists:
            if existing.to_dict().get("creator_id") != user_id:
                raise HTTPException(403, "貼文不屬於目前帳號")
            return {"post_id": body.post_id}
        from urllib.parse import quote
        token = (blob.metadata or {}).get("firebaseStorageDownloadTokens")
        if not token:
            token = str(uuid.uuid4())
            blob.metadata = {**(blob.metadata or {}), "firebaseStorageDownloadTokens": token}
            blob.patch()
        url = f"https://firebasestorage.googleapis.com/v0/b/{blob.bucket.name}/o/{quote(expected, safe='')}?alt=media&token={token.split(',')[0]}"
        post = Post(post_id=body.post_id, creator_id=user_id, image_url=url, caption=body.caption,
                    source="user", is_demo=False, created_at=datetime.now(timezone.utc))
        profile_data = client.document(f"users/{user_id}").get().to_dict() or {}
        name = profile_data.get("public_profile", {}).get("displayName", "LOOP 使用者")
        batch = client.batch()
        batch.create(client.document(f"posts/{body.post_id}"), post.model_dump(mode="json"))
        batch.set(client.document(f"creators/{user_id}"), {"creator_id": user_id,
                  "display_name": name, "is_demo": False}, merge=True)
        batch.commit()
        catalog_cache["expires"] = 0.0
        return {"post_id": body.post_id}

    @app.get("/api/v1/me/posts/{post_id}/status")
    def publish_status(post_id: str, user_id=Depends(uid)):
        doc = get_firestore_client().document(f"posts/{post_id}").get()
        if doc.exists and doc.to_dict().get("creator_id") != user_id:
            raise HTTPException(403, "貼文不屬於目前帳號")
        return {"published": doc.exists}

    images = settings.data_dir / "images"
    if images.is_dir():
        app.mount("/products/kaggle", StaticFiles(directory=images), name="catalog-images")
    built = ROOT / "frontend" / "dist"
    if built.is_dir():
        app.mount("/", StaticFiles(directory=built, html=True), name="frontend")
    return app
