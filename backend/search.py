"""
Search and Multimodal Relevance Module
Author: Hackathon Role C / F (Data & Embeddings)

Computes Cosine Similarity relevance scores for text, image, and mixed multimodal queries.
Directly implements `search_products(request, catalog) -> SearchResponse` for Role E/FastAPI,
and exports `compute_relevance()` for Role C/Recommender outfit ranking.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
from io import BytesIO
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from .config import ROOT
from .schemas import DetectedRegion, Product, RetrievalInfo, SearchHit, SearchRequest, SearchResponse
from scripts.build_embeddings import FashionCLIPWrapper, extract_search_text, l2_normalize
from scripts.embedding_store import EmbeddingStore


# Global cache for embedding store and encoder
_GLOBAL_STORE: Optional[EmbeddingStore] = None
_GLOBAL_MODEL: Optional[FashionCLIPWrapper] = None


def infer_query_categories(query_text: str) -> list[str]:
    """Apply unambiguous garment nouns as a hard category filter."""
    text = query_text.casefold()
    if "吊飾" in text:
        return ["accessory"]
    terms = {
        "top": ("襯衫", "t恤", "tee", "上衣", "背心", "針織", "毛衣"),
        "bottom": ("褲", "裙"),
        "shoes": ("鞋", "靴"),
        "outerwear": ("外套", "夾克", "大衣"),
        "accessory": ("包包", "背包", "肩背包", "帽子", "襪", "圍巾", "眼鏡", "腰帶"),
    }
    return [category for category, keywords in terms.items()
            if any(keyword in text for keyword in keywords)]


def embedding_runtime() -> dict[str, str | bool | None]:
    """Describe the actually usable retrieval runtime.

    The vectors committed with the project record the encoder that created
    them.  A query vector from a different encoder must never be compared to
    those vectors: identical dimensions do not make two embedding spaces
    compatible.
    """
    store = get_embedding_store()
    model = get_model()
    store_backend = str(store.metadata.get("backend")) if store else None
    compatible = bool(
        store
        and store_backend == model.backend
        and model.backend != "mock"
    )
    return {
        "model_backend": model.backend,
        "store_backend": store_backend,
        "store_compatible": compatible,
    }


def get_embedding_store() -> Optional[EmbeddingStore]:
    """Retrieve or load cached EmbeddingStore."""
    global _GLOBAL_STORE
    if _GLOBAL_STORE is None:
        # The older `products` index mixes 500 Kaggle IDs with just 12 official
        # products.  Search only the index built from this app's official catalog.
        store_path = ROOT / "data" / "embeddings" / "official_products"
        if store_path.is_dir() and (store_path / "id_mapping.json").is_file():
            try:
                _GLOBAL_STORE = EmbeddingStore.load(store_path)
            except Exception as e:
                print(f"[Warning] Could not load EmbeddingStore: {e}")
    return _GLOBAL_STORE


def get_model() -> FashionCLIPWrapper:
    """Retrieve or load cached FashionCLIP encoder."""
    global _GLOBAL_MODEL
    if _GLOBAL_MODEL is None:
        # Use auto device (cuda if available, else cpu)
        _GLOBAL_MODEL = FashionCLIPWrapper(device="auto", mock=False)
    return _GLOBAL_MODEL


def load_query_image(image_input: str | Image.Image) -> Optional[Image.Image]:
    """Load query image from an in-memory crop, Base64, local path, or URL."""
    if isinstance(image_input, Image.Image):
        return image_input.convert("RGB")
    if not image_input:
        return None

    # 1. Base64 data URL
    if image_input.startswith("data:image"):
        try:
            _, b64data = image_input.split(",", 1)
            raw = base64.b64decode(b64data)
            return Image.open(BytesIO(raw)).convert("RGB")
        except Exception:
            return None

    # 2. Local path
    local_path = Path(image_input)
    if local_path.is_file():
        try:
            return Image.open(local_path).convert("RGB")
        except Exception:
            return None

    # 3. Remote URL
    if image_input.startswith("http://") or image_input.startswith("https://"):
        try:
            import requests
            resp = requests.get(image_input, timeout=5)
            if resp.status_code == 200:
                return Image.open(BytesIO(resp.content)).convert("RGB")
        except Exception:
            return None

    return None


def rank_post_image_products(
    image_input: str,
    regions: list[DetectedRegion],
    candidates: list[Product],
    excluded_product_ids: set[str] | None = None,
    min_similarity: float = 0.40,
    per_region: int = 2,
    limit: int = 8,
) -> list[Product]:
    """Retrieve products from garment crops, never from the whole outfit image.

    Full-person backgrounds and unrelated garments skew FashionCLIP image
    similarity. The detector's normalized boxes identify the item to compare;
    each crop is searched only against products of its category. Weak matches
    are omitted instead of filling the drawer with arbitrary nearest neighbors.
    """
    image = load_query_image(image_input)
    if image is None:
        return []
    by_category: dict[str, list[Product]] = {}
    for product in candidates:
        by_category.setdefault(product.category, []).append(product)
    excluded = set(excluded_product_ids or ())
    selected_images: set[str] = set()
    selected: list[Product] = []
    width, height = image.size

    # Support default crops when no regions are provided
    active_regions = list(regions) if regions else [
        DetectedRegion(label="top", bbox=(0.15, 0.15, 0.85, 0.55)),
        DetectedRegion(label="bottom", bbox=(0.15, 0.50, 0.85, 0.95)),
    ]

    REGION_LABEL_MAP: dict[str, list[str]] = {
        "dress": ["top", "bottom"],
        "onepiece": ["top", "bottom"],
        "suit": ["outerwear", "top"],
        "jacket": ["outerwear"],
        "coat": ["outerwear"],
        "pants": ["bottom"],
        "trousers": ["bottom"],
        "shirt": ["top"],
    }

    for region in active_regions:
        target_labels = REGION_LABEL_MAP.get(region.label, [region.label])
        if sum(item.category in target_labels for item in selected) >= per_region:
            continue
        category_products = [
            product for lbl in target_labels
            for product in by_category.get(lbl, ())
            if product.product_id not in excluded
        ]
        if not category_products:
            continue
        x1, y1, x2, y2 = region.bbox
        x1, y1 = max(0.0, x1), max(0.0, y1)
        x2, y2 = min(1.0, x2), min(1.0, y2)
        box = (round(x1 * width), round(y1 * height), round(x2 * width), round(y2 * height))
        if box[2] - box[0] < 24 or box[3] - box[1] < 24:
            continue
        crop = image.crop(box)
        scores = compute_relevance(query_image=crop, candidates=category_products, mode="image")
        ranked = sorted(category_products, key=lambda product: (-scores.get(product.product_id, 0.0), product.product_id))
        best_score = scores.get(ranked[0].product_id, 0.0)
        if best_score < min_similarity:
            continue
        for product in ranked:
            score = scores.get(product.product_id, 0.0)
            if score < min_similarity or score < best_score - 0.12:
                break
            image_key = str(product.image_url or product.product_id)
            if image_key in selected_images:
                continue
            selected.append(product)
            excluded.add(product.product_id)
            selected_images.add(image_key)
            if len(selected) >= limit or sum(item.category in target_labels for item in selected) >= per_region:
                break
        if len(selected) >= limit:
            break
    return selected


def compute_relevance(
    query_text: Optional[str] = None,
    query_image: Optional[str | Image.Image] = None,
    candidates: Optional[list[Product]] = None,
    mode: str = "text",
    image_weight: float = 0.5,
) -> dict[str, float]:
    """
    Core function to calculate the FashionCLIP Cosine Similarity relevance score
    for each candidate product.
    
    Returns:
        dict of {product_id: relevance_score} where relevance_score is in [0.0, 1.0].
    """
    if not candidates:
        return {}

    model = get_model()
    store = get_embedding_store()
    # Never mix vectors produced by different encoders.  In particular, a
    # mock query vector against the committed Transformers index would return
    # plausible-looking but meaningless rankings.
    use_store = bool(
        store
        and store.metadata.get("backend") == model.backend
        and model.backend != "mock"
    )

    # The deterministic mock encoder exists only to keep development and
    # tests operational.  For text it has no semantic meaning, so use the
    # transparent metadata fallback instead of presenting random vectors as
    # relevance.  Image scores remain unavailable until FashionCLIP loads.
    if model.backend == "mock" and query_text and query_text.strip():
        return _metadata_text_scores(query_text, candidates)

    cand_ids = [p.product_id for p in candidates]
    relevance_scores: dict[str, float] = {}

    # -------------------------------------------------------------
    # 1. Image Cosine Similarity
    # -------------------------------------------------------------
    img_scores: dict[str, float] = {}
    if mode in ("image", "mixed") and query_image:
        q_img = load_query_image(query_image)
        if q_img:
            q_img_vec = model.encode_images([q_img])[0]
            q_img_vec = l2_normalize(q_img_vec)

            if use_store and store and store.image_embeddings is not None:
                # Fast matrix dot product from precomputed store
                search_res = store.search(q_img_vec, modality="image", top_k=len(cand_ids), candidate_ids=cand_ids)
                for pid, sim in search_res:
                    # Cosine sim in [-1, 1] mapped to [0, 1]
                    img_scores[pid] = max(0.0, float(sim))
            elif model.backend != "mock":
                # There is no product-image encoder cache to calculate
                # against.  Returning no visual score is preferable to a
                # fabricated constant score.
                for p in candidates:
                    img_scores[p.product_id] = 0.0
            else:
                for p in candidates:
                    img_scores[p.product_id] = 0.0
        else:
            for pid in cand_ids:
                img_scores[pid] = 0.0

    # -------------------------------------------------------------
    # 2. Text Cosine Similarity
    # -------------------------------------------------------------
    txt_scores: dict[str, float] = {}
    if mode in ("text", "mixed") and query_text and query_text.strip():
        q_txt = query_text.strip()
        q_txt_vec = model.encode_texts([q_txt])[0]
        q_txt_vec = l2_normalize(q_txt_vec)

        if use_store and store and store.text_embeddings is not None:
            # Fast matrix dot product from precomputed store
            search_res = store.search(q_txt_vec, modality="text", top_k=len(cand_ids), candidate_ids=cand_ids)
            for pid, sim in search_res:
                txt_scores[pid] = max(0.0, float(sim))

        # For any candidates not in precomputed store, compute on-the-fly
        missing_products = [p for p in candidates if p.product_id not in txt_scores]
        if missing_products:
            missing_texts = [extract_search_text(p.model_dump(mode="json"), "search_text") for p in missing_products]
            missing_vecs = model.encode_texts(missing_texts)
            missing_vecs = l2_normalize(missing_vecs)
            sims = np.dot(missing_vecs, q_txt_vec)
            for p, sim in zip(missing_products, sims):
                txt_scores[p.product_id] = max(0.0, float(sim))

    # -------------------------------------------------------------
    # 3. Mode Fusion (Text / Image / Mixed RRF)
    # -------------------------------------------------------------
    if mode == "text":
        for pid in cand_ids:
            relevance_scores[pid] = round(txt_scores.get(pid, 0.0), 4)

    elif mode == "image":
        for pid in cand_ids:
            relevance_scores[pid] = round(img_scores.get(pid, 0.0), 4)

    elif mode == "mixed":
        # Reciprocal Rank Fusion (RRF) as specified in draft2.md Section 10.2:
        # RRF(item) = w_img / (60 + rank_img) + w_txt / (60 + rank_txt)
        w_img = float(image_weight)
        w_txt = 1.0 - w_img
        k_rrf = 60.0

        # Sort ranks (1-indexed)
        sorted_img = sorted(cand_ids, key=lambda pid: -img_scores.get(pid, 0.0))
        img_ranks = {pid: rank + 1 for rank, pid in enumerate(sorted_img)}

        sorted_txt = sorted(cand_ids, key=lambda pid: -txt_scores.get(pid, 0.0))
        txt_ranks = {pid: rank + 1 for rank, pid in enumerate(sorted_txt)}

        max_rrf_possible = (w_img / (k_rrf + 1.0)) + (w_txt / (k_rrf + 1.0))

        for pid in cand_ids:
            r_img = img_ranks.get(pid, len(cand_ids))
            r_txt = txt_ranks.get(pid, len(cand_ids))
            rrf = (w_img / (k_rrf + r_img)) + (w_txt / (k_rrf + r_txt))
            # Normalize to [0, 1]
            norm_rrf = rrf / max(max_rrf_possible, 1e-6)
            relevance_scores[pid] = round(float(norm_rrf), 4)

    return relevance_scores


def _metadata_text_scores(query_text: str, candidates: list[Product]) -> dict[str, float]:
    """Deterministic fallback when the real FashionCLIP runtime is unavailable.

    The committed embedding files may have been produced with the same mock
    encoder, but their scores do not preserve useful Chinese keyword matches.
    This keeps the HTTP search useful and makes the fallback observable.
    """
    terms = [term for term in re.split(r"[\s,，、；;]+", query_text.casefold()) if term]
    scores: dict[str, float] = {}
    for product in candidates:
        haystack = " ".join((product.name, product.search_text, *product.styles, *product.colors)).casefold()
        scores[product.product_id] = round(
            sum(term in haystack for term in terms) / max(len(terms), 1), 4
        )
    return scores


def search_products(request: SearchRequest, catalog: list[Product]) -> SearchResponse:
    """
    Search API implementation conforming to draft2.md and backend/main.py contracts.
    """
    if not catalog:
        return SearchResponse(
            session_id=request.session_id,
            mode=request.mode,
            products=[],
            retrieval=RetrievalInfo(prefilter_count=0, fusion_method="none"),
        )

    has_text = bool(request.query_text.strip())
    has_image = bool(request.query_image)
    # A filter-only browse keeps deterministic metadata order and avoids
    # loading a large encoder merely to give every candidate a score of zero.
    if not has_text and not has_image:
        relevance_map = {product.product_id: 0.0 for product in catalog}
        model_backend = "filters_only"
    else:
        # 1. Compute relevance scores
        relevance_map = compute_relevance(
            query_text=request.query_text,
            query_image=request.query_image,
            candidates=catalog,
            mode=request.mode,
            image_weight=request.image_weight,
        )
        model_backend = get_model().backend
        if request.query_text.strip() and model_backend == "mock":
            relevance_map = _metadata_text_scores(request.query_text, catalog)

    # 2. Build SearchHits
    hits: list[SearchHit] = []
    catalog_by_id = {p.product_id: p for p in catalog}

    for pid, score in relevance_map.items():
        matched_filters = []
        p = catalog_by_id.get(pid)
        if p and request.filters.categories and p.category in request.filters.categories:
            matched_filters.append(f"category:{p.category}")
        if p and request.filters.price_max is not None and p.price <= request.filters.price_max:
            matched_filters.append(f"price_max:{request.filters.price_max}")

        hits.append(
            SearchHit(
                product_id=pid,
                score=score,
                score_breakdown={"relevance": score},
                matched_filters=matched_filters,
                warnings=["embedding_fallback"] if model_backend == "mock" else [],
                product=p,
            )
        )

    # Sort descending by relevance score, ties broken by product_id
    hits.sort(key=lambda h: (-h.score, h.product_id))

    if model_backend == "filters_only":
        fusion_name = "filters_only"
    elif model_backend == "mock":
        fusion_name = "metadata_text" if request.query_text.strip() else "embedding_unavailable_image"
    else:
        fusion_name = "rrf" if request.mode == "mixed" else f"fashion_clip_{request.mode}"
    retrieval_info = RetrievalInfo(
        prefilter_count=len(catalog),
        image_candidates=len(catalog) if request.mode in ("image", "mixed") else 0,
        text_candidates=len(catalog) if request.mode in ("text", "mixed") else 0,
        fusion_method=fusion_name,
    )

    return SearchResponse(
        session_id=request.session_id,
        mode=request.mode,
        products=hits[: request.limit],
        retrieval=retrieval_info,
    )
