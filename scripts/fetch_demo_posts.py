"""從 Pexels 抓取合法授權的穿搭照片，作為「貼文推薦」demo 素材的候選池。

為什麼用 Pexels：免費商用、不需標註、可修改；唯一限制是不能暗示照片中
人物代言我們的產品，我們只拿來當 Feed 展示內容，不涉及代言問題。

使用方式：
    1. 到 https://www.pexels.com/api/ 免費註冊拿 API key（即時核發，不用審核）
    2. 在 .env 加一行 PEXELS_API_KEY=xxxx
    3. python scripts/fetch_demo_posts.py

輸出：data/posts_raw.json（候選池，尚未跑過屬性抽取，不是最終 posts.json）
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"

# search query -> (可能的 style 種子, occasion 種子)
# 種子只是給人看的參考標記，不直接寫入最終 styles/occasion，
# 真正的標籤由 extract_post_attributes.py 對圖片重新判斷。
#
# 涵蓋 vocab.py 全部 9 個 styles、8 個 occasion，避免詞彙表裡有些標籤
# 因為候選池根本沒有對應圖片，永遠不會被抽到。
QUERIES: list[tuple[str, list[str], list[str]]] = [
    ("streetwear outfit fashion", ["street", "casual"], ["outdoor", "casual"]),
    ("japanese minimalist outfit fashion", ["japanese", "minimal"], ["casual"]),
    ("office business casual outfit fashion", ["formal", "minimal"], ["work"]),
    ("outdoor hiking outfit fashion", ["casual", "sporty"], ["outdoor", "travel"]),
    ("elegant date night outfit fashion", ["elegant", "formal"], ["date", "party"]),
    ("sporty athleisure outfit fashion", ["sporty"], ["sport", "casual"]),
    ("vintage retro outfit fashion", ["vintage"], ["casual"]),
    ("preppy collegiate outfit fashion", ["preppy"], ["work", "casual"]),
    ("monochrome minimalist outfit fashion", ["minimal"], ["work", "casual"]),
    ("travel airport outfit fashion", ["casual", "sporty"], ["travel"]),
    ("party night out outfit fashion", ["elegant", "street"], ["party"]),
    ("formal cocktail outfit fashion", ["formal", "elegant"], ["party", "formal"]),
    ("vintage denim outfit fashion", ["vintage", "casual"], ["casual"]),
    ("preppy formal outfit fashion", ["preppy", "formal"], ["work", "formal"]),
    ("cozy loungewear at home fashion", ["minimal", "casual"], ["casual"]),
    ("rainy day outfit fashion", ["street", "casual"], ["outdoor", "casual"]),
    ("beach summer outfit fashion", ["casual", "sporty"], ["travel", "outdoor"]),
]

PER_QUERY = 6
OUT_PATH = Path("data/posts_raw.json")


def fetch_query(query: str, per_page: int) -> list[dict]:
    resp = requests.get(
        PEXELS_SEARCH_URL,
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "per_page": per_page, "orientation": "portrait"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("photos", [])


def main() -> None:
    if not PEXELS_API_KEY:
        raise SystemExit("請先在 .env 設定 PEXELS_API_KEY（見檔頭說明）")

    raw_posts = []
    seen_ids: set[int] = set()
    for query, seed_styles, seed_occasion in QUERIES:
        photos = fetch_query(query, PER_QUERY)
        for photo in photos:
            if photo["id"] in seen_ids:
                continue
            seen_ids.add(photo["id"])
            raw_posts.append(
                {
                    "post_id": f"post-pexels-{photo['id']}",
                    "image_url": photo["src"]["large"],
                    "photographer": photo["photographer"],
                    "photographer_url": photo["photographer_url"],
                    "pexels_url": photo["url"],
                    "alt_description": photo.get("alt") or "",
                    "seed_styles": seed_styles,
                    "seed_occasion": seed_occasion,
                    "source": "pexels_licensed",
                    "source_checked_at": time.strftime("%Y-%m-%d"),
                }
            )
        time.sleep(1)  # 客氣地限速

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(raw_posts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"抓到 {len(raw_posts)} 張候選照片 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
