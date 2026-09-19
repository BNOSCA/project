"""Grounded, short explanations for catalog-search matches."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .intent.llm import LLMResponseError, LLMUnavailableError, _call_structured
from .schemas import Product, SearchResponse


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Explanation(_StrictModel):
    product_id: str
    explanation: str = Field(min_length=1, max_length=72)


class _ExplanationBatch(_StrictModel):
    explanations: list[_Explanation]


def _fallback(product: Product) -> str:
    """Remain factual when an LLM key is not configured or unavailable."""
    details = [product.category]
    if product.colors:
        details.append("、".join(product.colors[:2]))
    if product.styles:
        details.append("、".join(product.styles[:2]))
    return f"符合篩選條件；商品標籤包含{'／'.join(details)}。"


def _llm_explanations(query_text: str, products: list[Product]) -> dict[str, str]:
    payload = {
        "user_query": query_text,
        "products": [
            {
                "product_id": product.product_id,
                "name": product.name,
                "category": product.category,
                "colors": product.colors,
                "styles": product.styles,
                "fit": product.fit,
                "price_twd": product.price,
            }
            for product in products
        ],
    }
    messages = [
        {
            "role": "system",
            "content": (
                "You explain catalog search matches in Traditional Chinese. "
                "For every supplied product, return one concise explanation of at most 36 Chinese characters. "
                "Use only the supplied product fields and user query. Do not claim the item is identical, in stock, "
                "or suitable for an unstated occasion."
            ),
        },
        {
            "role": "user",
            "content": "Return only the schema object.\n\n" + json.dumps(payload, ensure_ascii=False),
        },
    ]
    raw = _call_structured(
        messages=messages,
        schema_model=_ExplanationBatch,
        schema_name="catalog_search_explanations",
    )
    try:
        batch = _ExplanationBatch.model_validate(raw)
    except ValidationError as exc:
        raise LLMResponseError("Search explanation validation failed") from exc
    expected_ids = {product.product_id for product in products}
    return {
        item.product_id: item.explanation.strip()
        for item in batch.explanations
        if item.product_id in expected_ids and item.explanation.strip()
    }


def add_search_explanations(response: SearchResponse, query_text: str) -> SearchResponse:
    """Add batch LLM explanations, with an explicitly labelled factual fallback."""
    hits = [hit for hit in response.products if hit.product is not None]
    if not query_text.strip() or not hits:
        return response

    products = [hit.product for hit in hits if hit.product is not None]
    try:
        explanations = _llm_explanations(query_text, products)
    except (LLMUnavailableError, LLMResponseError):
        explanations = {}

    for hit in hits:
        assert hit.product is not None
        explanation = explanations.get(hit.product_id)
        if explanation:
            hit.explanation = explanation
            hit.explanation_source = "llm"
        else:
            hit.explanation = _fallback(hit.product)
            hit.explanation_source = "fallback"
    return response


def visual_search_explanations(products: list[Product], categories: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """Explain visual matches without claiming that they are the original item."""
    if not products:
        return {}, {}
    category_context = "、".join(dict.fromkeys(categories)) or "穿搭單品"
    query = f"貼文中偵測到的單品類別：{category_context}；結果由 FashionCLIP 視覺相似檢索取得。"
    try:
        explanations = _llm_explanations(query, products)
    except (LLMUnavailableError, LLMResponseError):
        explanations = {}

    text, sources = {}, {}
    for product in products:
        explanation = explanations.get(product.product_id)
        text[product.product_id] = explanation or f"與貼文中的 {product.category} 同類別，並通過視覺相似檢索。"
        sources[product.product_id] = "llm" if explanation else "fallback"
    return text, sources
