from backend.schemas import Product, RetrievalInfo, SearchHit, SearchResponse
from backend import search_explanations
from backend.search_explanations import add_search_explanations


def _product(product_id: str) -> Product:
    return Product(
        product_id=product_id,
        name=f"商品 {product_id}",
        category="top",
        price=1000,
        source="test",
        styles=["japanese"],
    )


def test_only_three_highest_scoring_search_products_receive_explanations(monkeypatch):
    response = SearchResponse(
        session_id="demo",
        mode="text",
        products=[
            SearchHit(product_id=f"product-{index}", score=score, product=_product(f"product-{index}"))
            for index, score in enumerate((0.48, 0.93, 0.77, 0.62, 0.31), 1)
        ],
        retrieval=RetrievalInfo(),
    )
    requested_ids: list[str] = []

    def explain(_query: str, products: list[Product]) -> dict[str, str]:
        requested_ids.extend(product.product_id for product in products)
        return {product.product_id: f"{product.name} 符合日系標籤。" for product in products}

    monkeypatch.setattr("backend.search_explanations._llm_explanations", explain)

    result = add_search_explanations(response, "日系穿搭")

    assert requested_ids == ["product-2", "product-3", "product-4"]
    assert [hit.explanation_source for hit in result.products] == ["none", "llm", "llm", "llm", "none"]


def test_fallback_explanation_describes_the_actual_product():
    product = Product(
        product_id="shirt-1",
        name="深藍牛津襯衫",
        category="top",
        price=1290,
        colors=["深藍"],
        styles=["日系"],
        fit="regular",
        source="test",
    )

    explanation = search_explanations._fallback(product, "日系面試穿搭")

    assert "深藍牛津襯衫" in explanation
    assert "上身單品" in explanation
    assert "深藍色" in explanation
    assert "搜尋相關分數" not in explanation
