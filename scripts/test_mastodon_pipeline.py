"""測試腳本：把黑客松爬蟲抓到的 Mastodon 貼文餵進既有的貼文屬性抽取 pipeline，
看 FashionCLIP + YOLOS-fashionpedia 對「真實社群貼文」的效果如何。

刻意輸出到 data/mastodon_test/，不動 data/posts.json 等既有 Pexels pipeline
的正式輸出，純粹讓人先看效果、決定要不要正式採用。

輸入：黑客松爬蟲-20260919T071454Z-1-001/黑客松爬蟲/data/social_fashion_seed_chinese_ootd/posts.json
      （沿用爬蟲已經下載好的本地預覽圖，不重新打 Mastodon）
輸出：
    - data/mastodon_test/posts.json       貼文屬性（含 caption/來源等原始欄位）
    - data/mastodon_test/creators.json
    - data/mastodon_test/posts_proposed_schema.json（比照 convert_to_schema.py 的轉換規則）
    - data/mastodon_test/embeddings/<post_id>.npy

用法：
    python scripts/test_mastodon_pipeline.py [--limit N] [--debug]
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForObjectDetection, CLIPModel, CLIPProcessor

from vocab import (
    COLORS,
    FASHIONPEDIA_LABEL_TO_GARMENT,
    FITS,
    GARMENT_LABELS,
    MATERIALS,
    OCCASIONS,
    STYLES,
)

SEED_DIR = Path(
    "黑客松爬蟲-20260919T071454Z-1-001/黑客松爬蟲/data/social_fashion_seed_chinese_ootd"
)
RAW_POSTS_PATH = SEED_DIR / "posts.json"

OUT_DIR = Path("data/mastodon_test")
POSTS_OUT_PATH = OUT_DIR / "posts.json"
SCHEMA_OUT_PATH = OUT_DIR / "posts_proposed_schema.json"
CREATORS_OUT_PATH = OUT_DIR / "creators.json"
EMBEDDINGS_DIR = OUT_DIR / "embeddings"

FASHION_CLIP_MODEL = "patrickjohncyh/fashion-clip"
DETECTOR_MODEL = "valentinafeve/yolos-fashionpedia"

# 跟 extract_post_attributes.py 用同一組門檻，才有可比性。
CATEGORY_CONFIG = [
    ("styles", STYLES, "a photo of an outfit in {} style", 0.21, 3, False),
    ("colors", COLORS, "an outfit that is mainly {} colored", 0.19, 3, True),
    ("occasion", OCCASIONS, "an outfit suitable for {}", 0.20, 1, False),
    ("fits", FITS, "clothing with a {} fit", 0.20, 2, False),
    ("materials", MATERIALS, "clothing made of {} material", 0.24, 1, False),
]
GARMENT_COLOR_THRESHOLD = 0.19
GARMENT_DETECTION_SCORE_THRESHOLD = 0.35
ALLOWED_GARMENT_LABELS = {"top", "bottom", "shoes", "outerwear", "dress"}


def build_text_bank(model, processor, labels, template):
    texts = [template.format(label) for label in labels]
    inputs = processor(text=texts, return_tensors="pt", padding=True)
    with torch.no_grad():
        text_embeds = model.get_text_features(**inputs).pooler_output
    return text_embeds / text_embeds.norm(dim=-1, keepdim=True)


def embed_image(model, processor, image):
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        image_embeds = model.get_image_features(**inputs).pooler_output
    return image_embeds / image_embeds.norm(dim=-1, keepdim=True)


def classify(image_embeds, text_embeds, labels, threshold, max_k, force_top1):
    sims = (image_embeds @ text_embeds.T).squeeze(0)
    ranked = sorted(zip(labels, sims.tolist()), key=lambda x: -x[1])
    picked = [label for label, score in ranked if score >= threshold][:max_k]
    if not picked and force_top1 and ranked:
        picked = [ranked[0][0]]
    return picked, ranked


def detect_garments(detector_model, detector_processor, clip_model, clip_processor, color_text_bank, image):
    width, height = image.size
    inputs = detector_processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = detector_model(**inputs)
    target_sizes = torch.tensor([image.size[::-1]])
    results = detector_processor.post_process_object_detection(
        outputs, threshold=GARMENT_DETECTION_SCORE_THRESHOLD, target_sizes=target_sizes
    )[0]

    best_per_bucket: dict[str, dict] = {}
    for score, label_id, box in zip(results["scores"], results["labels"], results["boxes"]):
        raw_label = detector_model.config.id2label[label_id.item()]
        bucket = FASHIONPEDIA_LABEL_TO_GARMENT.get(raw_label)
        if bucket is None or bucket not in GARMENT_LABELS:
            continue
        score = score.item()
        if bucket in best_per_bucket and best_per_bucket[bucket]["score"] >= score:
            continue
        best_per_bucket[bucket] = {"score": score, "box": box.tolist()}

    garments = []
    for label, pred in best_per_bucket.items():
        x1, y1, x2, y2 = pred["box"]
        crop = image.crop((x1, y1, x2, y2))
        if crop.width < 4 or crop.height < 4:
            crop_colors: list[str] = []
        else:
            crop_embed = embed_image(clip_model, clip_processor, crop)
            crop_colors, _ = classify(
                crop_embed, color_text_bank, COLORS, GARMENT_COLOR_THRESHOLD, 2, force_top1=True
            )
        garments.append(
            {
                "label": label,
                "bbox": [
                    round(x1 / width, 4),
                    round(y1 / height, 4),
                    round(x2 / width, 4),
                    round(y2 / height, 4),
                ],
                "colors": crop_colors,
                "detection_score": round(pred["score"], 4),
            }
        )
    return garments


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "unknown"


def convert_post_to_schema(post: dict) -> dict:
    detected_regions = [
        {"label": g["label"], "bbox": g["bbox"]}
        for g in post.get("garments", [])
        if g["label"] in ALLOWED_GARMENT_LABELS
    ]
    return {
        "post_id": post["post_id"],
        "creator_id": post["creator_id"],
        "image_url": post["image_url"],
        "caption": post["caption"],
        "styles": post["styles"],
        "colors": post["colors"],
        "occasion": post["occasion"],
        "tagged_products": [],
        "detected_regions": detected_regions,
        "source": post["source"],
        "source_checked_at": post["source_checked_at"],
        "is_demo": post["is_demo"],
        "created_at": post["created_at"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="只處理前 N 篇，先小量測試用")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if not RAW_POSTS_PATH.exists():
        raise SystemExit(f"找不到 {RAW_POSTS_PATH}，請先確認爬蟲套件已解壓縮")

    mastodon_posts = json.loads(RAW_POSTS_PATH.read_text(encoding="utf-8"))
    if args.limit:
        mastodon_posts = mastodon_posts[: args.limit]

    print("載入 FashionCLIP ...")
    clip_model = CLIPModel.from_pretrained(FASHION_CLIP_MODEL)
    clip_processor = CLIPProcessor.from_pretrained(FASHION_CLIP_MODEL)
    clip_model.eval()

    print("載入偵測模型 ...")
    detector_processor = AutoImageProcessor.from_pretrained(DETECTOR_MODEL)
    detector_model = AutoModelForObjectDetection.from_pretrained(DETECTOR_MODEL)
    detector_model.eval()

    print("預先計算詞彙表的文字 embedding ...")
    text_banks = {
        name: build_text_bank(clip_model, clip_processor, labels, template)
        for name, labels, template, *_ in CATEGORY_CONFIG
    }
    color_text_bank = text_banks["colors"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

    posts: list[dict] = []
    creators: dict[str, dict] = {}

    for i, raw in enumerate(mastodon_posts, start=1):
        print(f"[{i}/{len(mastodon_posts)}] 處理 {raw['seed_id']} ...")
        local_path = SEED_DIR / raw["local_image_path"]
        try:
            image = Image.open(local_path).convert("RGB")
        except Exception as exc:  # noqa: BLE001
            print(f"  跳過（讀圖失敗）：{exc}")
            continue

        image_embeds = embed_image(clip_model, clip_processor, image)
        np.save(EMBEDDINGS_DIR / f"{raw['seed_id']}.npy", image_embeds.squeeze(0).numpy())

        attrs: dict[str, list[str]] = {}
        unknown_fields: list[str] = []
        for name, labels, _template, threshold, max_k, force_top1 in CATEGORY_CONFIG:
            picked, ranked = classify(image_embeds, text_banks[name], labels, threshold, max_k, force_top1)
            attrs[name] = picked
            if not picked:
                unknown_fields.append(name)
            if args.debug:
                top3 = ", ".join(f"{l}={s:.3f}" for l, s in ranked[:3])
                print(f"    {name}: picked={picked} top3=({top3})")

        garments = detect_garments(
            detector_model, detector_processor, clip_model, clip_processor, color_text_bank, image
        )

        creator_id = f"creator-mastodon-{slugify(raw['author_handle'])}"
        creators.setdefault(
            creator_id,
            {
                "creator_id": creator_id,
                "display_name": raw["author_display_name"] or raw["author_handle"],
                "source": "mastodon_public_scrape",
                "source_url": raw["source_post_url"],
                "is_demo": True,
            },
        )

        posts.append(
            {
                "post_id": raw["seed_id"],
                "creator_id": creator_id,
                "image_url": raw["local_image_path"],  # 本地測試用相對路徑，非公開網址
                "caption": raw["caption"],
                "source_query": raw["source_query"],
                "styles": attrs["styles"],
                "colors": attrs["colors"],
                "occasion": attrs["occasion"],
                "fits": attrs["fits"],
                "materials": attrs["materials"],
                "unknown_fields": unknown_fields,
                "garments": garments,
                "image_embedding_id": raw["seed_id"],
                "tagged_products": [],
                "source": "mastodon_public_scrape",
                "source_checked_at": raw["fetched_at_utc"][:10],
                "is_demo": True,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

    POSTS_OUT_PATH.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    CREATORS_OUT_PATH.write_text(
        json.dumps(list(creators.values()), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    SCHEMA_OUT_PATH.write_text(
        json.dumps([convert_post_to_schema(p) for p in posts], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"完成：{len(posts)} 篇貼文 -> {POSTS_OUT_PATH}")
    print(f"完成：{len(creators)} 位創作者 -> {CREATORS_OUT_PATH}")
    print(f"完成：schema 提案版 -> {SCHEMA_OUT_PATH}")


if __name__ == "__main__":
    main()
