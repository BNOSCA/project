"""把 data/posts.json（我們的完整版原始資料）轉成符合 backend/schemas.py
`Post` 的格式，交給團隊整合用。

原始資料（含 garments/fits/materials/unknown_fields/image_embedding_id）
完全不動，這支腳本只是「多輸出一份」轉換過的版本，不會覆蓋掉原始檔案。

設計前提（跟團隊確認過的方向）：
    我們完全沒有「這張貼文的這個單品＝商品庫裡的哪個 product_id」這種
    真實對應資料，所以 `tagged_products`（人工/已知的精確標記）對這批
    資料來說**恆為空**，不是暫時空著。真正要用的是：使用者點擊貼文上的
    單品時，後端拿該單品的裁切區域即時去商城做圖片搜尋，回傳
    `PostDetail.similar_products`（schema 裡已經有這個欄位，就是設計來
    裝「搜出來的相似商品」，不是我們發明的）。

    要讓這個流程跑起來，後端只需要知道「這張貼文的這個位置有一件
    什麼類型的單品」，不需要也不應該預先塞一個假的 product_id。
    所以這裡改成輸出一個新提案欄位 `detected_regions`（label+bbox，
    不含 product_id/match_type），而不是硬湊 tagged_products。

    這是一個**要向團隊提案、由 E 決定是否收進 schema** 的新欄位，
    不是我們可以自己定案的事；在團隊確認前，這份輸出檔案不能直接
    當作最終格式使用。

轉換規則：
    - 只保留 garments 裡 label 屬於 top/bottom/shoes/outerwear/dress 的
      單品放進 detected_regions（團隊已確認擴充商品類別涵蓋這 5 類；
      accessory 目前仍不在範圍內，先不輸出）
    - tagged_products 固定輸出空陣列 []（符合現有 schema，誠實反映
      「沒有已知商品連結」這個事實）
    - caption 先填空字串佔位——這個欄位怎麼處理（要不要真的生文字、
      還是跟團隊提案把 schema 改成 optional）還沒有定論，故意留空
      讓人一眼看出這裡還沒決定，不要誤以為是有意義的空字串

輸出：
    - data/posts_schema_compliant.json   給團隊整合/提案討論用
"""

from __future__ import annotations

import json
from pathlib import Path

POSTS_IN_PATH = Path("data/posts.json")
# 檔名故意不叫 "schema_compliant"：detected_regions 是提案欄位，
# 在團隊接受之前這份輸出實際上會被現有 schema 的 extra="forbid" 擋下來，
# 叫 "compliant" 會誤導人以為可以直接拿去用。
POSTS_OUT_PATH = Path("data/posts_proposed_schema.json")

# 團隊確認擴充商品類別到 outerwear/dress（accessory 目前仍不在範圍內，
# 先不輸出這類 detected_regions，等之後決定再加）。
ALLOWED_GARMENT_LABELS = {"top", "bottom", "shoes", "outerwear", "dress"}


def convert_post(post: dict) -> dict:
    detected_regions = [
        {"label": g["label"], "bbox": g["bbox"]}
        for g in post.get("garments", [])
        if g["label"] in ALLOWED_GARMENT_LABELS
    ]

    return {
        "post_id": post["post_id"],
        "creator_id": post["creator_id"],
        "image_url": post["image_url"],
        "caption": "",  # TODO: 待團隊決定 caption 怎麼處理，先佔位
        "styles": post["styles"],
        "colors": post["colors"],
        "occasion": post["occasion"],
        "tagged_products": [],  # 恆為空：我們沒有任何已知商品對應資料
        "detected_regions": detected_regions,  # 提案欄位，待團隊確認是否收進 schema
        "source": post["source"],
        "source_checked_at": post["source_checked_at"],
        "is_demo": post["is_demo"],
        "created_at": post["created_at"],
    }


def main() -> None:
    posts = json.loads(POSTS_IN_PATH.read_text(encoding="utf-8"))
    converted = [convert_post(p) for p in posts]

    no_region_count = sum(1 for p in converted if not p["detected_regions"])

    POSTS_OUT_PATH.write_text(
        json.dumps(converted, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"完成：{len(converted)} 篇 -> {POSTS_OUT_PATH}")
    print(f"提醒：{no_region_count} 篇貼文沒有任何 top/bottom/shoes/outerwear/dress 單品，detected_regions 是空的")
    print("提醒：caption 全部是空字串佔位，還沒有真正內容")
    print("提醒：detected_regions 是提案欄位，還不在正式 schema 裡，交給團隊前要先講清楚")


if __name__ == "__main__":
    main()
