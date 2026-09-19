"""把 run_asian_fashion_pipeline.py 產生的一批貼文，轉成 schema-compliant 格式，
並且「附加」進 data/fixtures/posts.json / creators.json——絕對不會整個覆蓋掉，
會先檢查 id 有沒有衝突，衝突就直接中止、不動任何檔案。

用法：
    python scripts/append_batch_to_fixtures.py --batch-dir data/asian_fashion_batch_2

輸入：<batch-dir>/posts_with_captions.json、<batch-dir>/creators.json
輸出：直接更新 data/fixtures/posts.json、data/fixtures/creators.json（附加，不覆蓋）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from backend.schemas import Post, Creator  # noqa: E402

ALLOWED_GARMENT_LABELS = {"top", "bottom", "shoes", "outerwear", "dress"}
FIXTURES_POSTS = Path("data/fixtures/posts.json")
FIXTURES_CREATORS = Path("data/fixtures/creators.json")


def to_compliant_post(p: dict) -> dict:
    detected_regions = [
        {"label": g["label"], "bbox": g["bbox"]}
        for g in p.get("garments", []) if g["label"] in ALLOWED_GARMENT_LABELS
    ]
    return {
        "post_id": p["post_id"],
        "creator_id": p["creator_id"],
        "image_url": p["image_url"],
        "caption": p["generated_caption"],
        "styles": p["styles"],
        "colors": p["colors"],
        "occasion": p["occasion"],
        "tagged_products": [],
        "detected_regions": detected_regions,
        "source": p["source"],
        "source_checked_at": p["source_checked_at"],
        "is_demo": p["is_demo"],
        "created_at": p["created_at"],
    }


def to_compliant_creator(c: dict) -> dict:
    return {"creator_id": c["creator_id"], "display_name": c["display_name"], "is_demo": c["is_demo"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-dir", required=True, help="run_asian_fashion_pipeline.py 的輸出資料夾")
    args = parser.parse_args()
    batch_dir = Path(args.batch_dir)

    raw_posts = json.loads((batch_dir / "posts_with_captions.json").read_text(encoding="utf-8"))
    raw_creators = json.loads((batch_dir / "creators.json").read_text(encoding="utf-8"))

    missing_captions = [p["post_id"] for p in raw_posts if not p.get("generated_caption")]
    if missing_captions:
        raise SystemExit(f"中止：{len(missing_captions)} 篇還沒有配文，先跑完 generate captions 階段。例如：{missing_captions[:5]}")

    new_posts = [to_compliant_post(p) for p in raw_posts]
    new_creators = [to_compliant_creator(c) for c in raw_creators]

    for post in new_posts:
        Post(**post)
    for creator in new_creators:
        Creator(**creator)
    print(f"驗證通過：{len(new_posts)} 篇貼文、{len(new_creators)} 位創作者符合 schema")

    existing_posts = json.loads(FIXTURES_POSTS.read_text(encoding="utf-8"))
    existing_creators = json.loads(FIXTURES_CREATORS.read_text(encoding="utf-8"))

    existing_post_ids = {p["post_id"] for p in existing_posts}
    existing_creator_ids = {c["creator_id"] for c in existing_creators}
    new_post_ids = {p["post_id"] for p in new_posts}

    # 貼文 id 重複才是真的問題，直接中止。
    post_collisions = existing_post_ids & new_post_ids
    if post_collisions:
        raise SystemExit(f"中止，發現 post_id 衝突，沒有動任何檔案：{list(post_collisions)[:5]}")

    # 同一個攝影師／創作者出現在多個批次很正常，不是衝突；只加入真的沒見過的創作者。
    creators_to_add = [c for c in new_creators if c["creator_id"] not in existing_creator_ids]
    skipped_creators = len(new_creators) - len(creators_to_add)

    combined_posts = existing_posts + new_posts
    combined_creators = existing_creators + creators_to_add

    FIXTURES_POSTS.write_text(json.dumps(combined_posts, ensure_ascii=False, indent=2), encoding="utf-8")
    FIXTURES_CREATORS.write_text(json.dumps(combined_creators, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"完成（附加，非覆蓋）：")
    print(f"  posts.json    {len(existing_posts)} -> {len(combined_posts)}")
    print(f"  creators.json {len(existing_creators)} -> {len(combined_creators)}"
          f"（新增 {len(creators_to_add)} 位，{skipped_creators} 位已存在故跳過）")
    print("記得跑 python3 scripts/build_combined_catalog.py 讓後端讀到最新資料。")


if __name__ == "__main__":
    main()
