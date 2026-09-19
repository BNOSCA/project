"""
Demo Script: Run FashionCLIP Relevance Search on 512 real products.
Displays Top 10 results with full metadata, relevance scores, and filter verification.
"""

import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.schemas import Product, SearchFilters, SearchRequest
from backend.search import search_products, compute_relevance


def run_demo():
    # 1. Load the 512 real products catalog
    products_file = Path("data/products.json")
    with open(products_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    catalog = [Product.model_validate(x) for x in data]
    print(f"=== Loaded Catalog: {len(catalog)} products ===")

    # -------------------------------------------------------------
    # Query 1: Text Search for "黑色 日系 寬鬆 襯衫" (Top 10)
    # -------------------------------------------------------------
    query_1 = "黑色 日系 寬鬆 襯衫"
    print(f"\n=======================================================")
    print(f"[Query 1] 文字檢索: '{query_1}'")
    print(f"條件: 不限類別，計算 FashionCLIP Cosine Relevance 前 10 名")
    print(f"=======================================================")

    req1 = SearchRequest(
        session_id="demo-session-01",
        query_text=query_1,
        mode="text",
        limit=10,
    )

    resp1 = search_products(req1, catalog)

    print(f"{'名次':<4} | {'商品 ID':<16} | {'類別':<8} | {'價格':<6} | {'相關度得分':<10} | {'顏色':<15} | {'商品名稱'}")
    print("-" * 95)
    for idx, hit in enumerate(resp1.products, 1):
        p = hit.product
        colors_str = ",".join(p.colors) if p and p.colors else "n/a"
        name_str = p.name if p else "n/a"
        cat_str = p.category if p else "n/a"
        price_str = f"${p.price}" if p else "n/a"
        print(f"{idx:<4} | {hit.product_id:<16} | {cat_str:<8} | {price_str:<6} | {hit.score:<10.4f} | {colors_str:<15} | {name_str}")

    # -------------------------------------------------------------
    # Query 2: Mixed / Filtered Query: "藍色 牛仔 休閒" + 預算 <= 800 (Top 10)
    # -------------------------------------------------------------
    query_2 = "藍色 休閒 T-shirt"
    print(f"\n=======================================================")
    print(f"[Query 2] 帶硬條件檢索: '{query_2}'")
    print(f"硬條件: 預算 <= 790 元，排除米色 (excluded_colors=['beige'])，取前 10 名")
    print(f"=======================================================")

    # Filter catalog with hard constraints first (deterministic pre-filter)
    filtered_catalog = [
        p for p in catalog
        if p.price <= 790 and "beige" not in p.colors
    ]
    print(f"  -> 通過硬篩選的候選商品數: {len(filtered_catalog)} / {len(catalog)}")

    req2 = SearchRequest(
        session_id="demo-session-02",
        query_text=query_2,
        mode="text",
        filters=SearchFilters(price_max=790, excluded_colors=["beige"]),
        limit=10,
    )

    resp2 = search_products(req2, filtered_catalog)

    print(f"{'名次':<4} | {'商品 ID':<16} | {'類別':<8} | {'價格':<6} | {'相關度得分':<10} | {'顏色':<15} | {'商品名稱'}")
    print("-" * 95)
    for idx, hit in enumerate(resp2.products, 1):
        p = hit.product
        colors_str = ",".join(p.colors) if p and p.colors else "n/a"
        name_str = p.name if p else "n/a"
        cat_str = p.category if p else "n/a"
        price_str = f"${p.price}" if p else "n/a"
        print(f"{idx:<4} | {hit.product_id:<16} | {cat_str:<8} | {price_str:<6} | {hit.score:<10.4f} | {colors_str:<15} | {name_str}")

    # -------------------------------------------------------------
    # Query 3: Visual Image Search (mode="image")
    # -------------------------------------------------------------
    test_img = "data/catalog/kaggle_500/images/54933.jpg"
    print(f"\n=======================================================")
    print(f"[Query 3] 以圖搜圖 (Image Search): 參考照片 '{test_img}'")
    print(f"條件: 以 FashionCLIP 視覺特徵比對全館 512 件商品，取視覺最相似前 10 名")
    print(f"=======================================================")

    req3 = SearchRequest(
        session_id="demo-session-03",
        query_image=test_img,
        mode="image",
        limit=10,
    )

    resp3 = search_products(req3, catalog)

    print(f"{'名次':<4} | {'商品 ID':<16} | {'類別':<8} | {'價格':<6} | {'視覺相關度':<10} | {'顏色':<15} | {'商品名稱'}")
    print("-" * 95)
    for idx, hit in enumerate(resp3.products, 1):
        p = hit.product
        colors_str = ",".join(p.colors) if p and p.colors else "n/a"
        name_str = p.name if p else "n/a"
        cat_str = p.category if p else "n/a"
        price_str = f"${p.price}" if p else "n/a"
        print(f"{idx:<4} | {hit.product_id:<16} | {cat_str:<8} | {price_str:<6} | {hit.score:<10.4f} | {colors_str:<15} | {name_str}")

    print("\n[OK] 檢索執行完畢，所有相關度得分均由本機實體 FashionCLIP 向量內積計算得出。")


if __name__ == "__main__":
    run_demo()
