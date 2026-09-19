"""一鍵跑完整條「亞洲穿搭樣本」pipeline：抓圖 → FashionCLIP/YOLOS 屬性抽取
（含單品 bbox）→ Groq 生成自然語氣中文配文 → 產生可直接用瀏覽器打開的 HTML 報告。

這支腳本把 fetch_asian_fashion_posts_v2.py / test_asian_fashion_pipeline_v2.py /
generate_captions_v2.py 三支腳本的邏輯合併成一次執行，模型只載入一次，
而且每個階段都可以中斷後重跑（已經處理過的照片會被跳過，不會重抓/重跑）。

用法：
    python scripts/run_asian_fashion_pipeline.py --count 500
    python scripts/run_asian_fashion_pipeline.py --count 500 --out-dir data/asian_fashion_batch_2

    # 中斷後重跑會自動跳過已完成的階段/照片：
    python scripts/run_asian_fashion_pipeline.py --count 500 --out-dir data/asian_fashion_batch_2

    # 只想重新生成 HTML（例如手動編輯過 posts_with_captions.json 之後）：
    python scripts/run_asian_fashion_pipeline.py --count 500 --out-dir data/asian_fashion_batch_2 --skip-fetch --skip-extract --skip-captions

    # 一次跑完所有階段，包含抓第二批（避開第一批）、附加進正式資料庫、重建 combined catalog：
    python scripts/run_asian_fashion_pipeline.py --count 500 \
        --out-dir data/asian_fashion_batch_2 --start-page 2 --exclude-dir data/asian_fashion_batch \
        --append-to-fixtures

需要 .env 裡的 PEXELS_API_KEY、GROQ_API_KEY。

--append-to-fixtures 這個階段只會「附加」進 data/fixtures/posts.json / creators.json，
發現 post_id / creator_id 跟現有資料衝突就直接中止、不寫入任何檔案，絕對不會覆蓋或刪掉舊資料。

輸出（在 --out-dir 底下）：
    posts_raw.json              抓到的 Pexels 候選（含 alt text、搜尋詞、人種傾向標記）
    images/<post_id>.jpg        下載的圖片
    posts.json                  加上 FashionCLIP/YOLOS 抽出的 styles/colors/occasion/garments
    posts_with_captions.json    加上 generated_caption
    report.html                 可直接用瀏覽器打開的最終報告（圖片走本地相對路徑，離線也能看）
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import Counter
from io import BytesIO
from pathlib import Path

import numpy as np
import requests
import torch
from dotenv import load_dotenv
from groq import Groq
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

load_dotenv()

# (查詢字串, 人種傾向標記) —— 沿用 fetch_asian_fashion_posts_v2.py 的清單：
# 原本 fetch_demo_posts.py 的 17 個「現代穿搭情境」關鍵字（通勤/運動/旅行/居家等，
# 不是傳統服飾/角色扮演），大部分加上 asian 讓亞洲臉孔為主，少數加 european 混入歐洲臉孔。
QUERIES: list[tuple[str, str]] = [
    ("asian streetwear outfit fashion", "asian"),
    ("japanese minimalist outfit fashion", "asian_implied"),
    ("asian office business casual outfit fashion", "asian"),
    ("asian outdoor hiking outfit fashion", "asian"),
    ("european elegant date night outfit fashion", "european"),
    ("asian sporty athleisure outfit fashion", "asian"),
    ("european vintage retro outfit fashion", "european"),
    ("asian preppy collegiate outfit fashion", "asian"),
    ("asian monochrome minimalist outfit fashion", "asian"),
    ("asian travel airport outfit fashion", "asian"),
    ("party night out outfit fashion", "neutral"),
    ("european formal cocktail outfit fashion", "european"),
    ("asian vintage denim outfit fashion", "asian"),
    ("asian preppy formal outfit fashion", "asian"),
    ("asian cozy loungewear at home fashion", "asian"),
    ("rainy day outfit fashion", "neutral"),
    ("asian beach summer outfit fashion", "asian"),
]

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
FASHION_CLIP_MODEL = "patrickjohncyh/fashion-clip"
DETECTOR_MODEL = "valentinafeve/yolos-fashionpedia"
GROQ_MODEL = "qwen/qwen3.8-27b"

CATEGORY_CONFIG = [
    ("styles", STYLES, "a photo of an outfit in {} style", 0.21, 3, False),
    ("colors", COLORS, "an outfit that is mainly {} colored", 0.19, 3, True),
    ("occasion", OCCASIONS, "an outfit suitable for {}", 0.20, 1, False),
    ("fits", FITS, "clothing with a {} fit", 0.20, 2, False),
    ("materials", MATERIALS, "clothing made of {} material", 0.24, 1, False),
]
GARMENT_COLOR_THRESHOLD = 0.19
GARMENT_DETECTION_SCORE_THRESHOLD = 0.35

GARMENT_COLOR_HEX = {
    "top": "#3b82f6", "bottom": "#22c55e", "shoes": "#f97316",
    "outerwear": "#a855f7", "accessory": "#ec4899", "dress": "#ef4444",
}
CAT_LABELS_ZH = {"styles": "風格", "colors": "顏色", "occasion": "場合", "fits": "版型", "materials": "材質"}
TILT_LABEL_ZH = {"asian": "亞洲", "asian_implied": "日系", "european": "歐洲", "neutral": "中性"}
TILT_COLOR_HEX = {"asian": "#a53e5c", "asian_implied": "#c2794a", "european": "#4a7ec2", "neutral": "#6b6480"}

CAPTION_PROMPT = """幫一張穿搭照片寫一句社群貼文風格的中文（繁體）caption，
像真人在 Instagram/Threads 隨手發的那種，不要像規格說明書。

這張照片的風格關鍵字大致是：{styles}；主色系大致是：{colors}；
圖片英文描述（僅供你想像畫面用，不用照翻）：{alt}

寫法：
- 自由發揮語氣和內容——可以講心情、天氣、旅行、跟朋友出門、單純曬照，
  什麼都可以，不需要每一句都在講衣服
- 不要違背上面的主色系（不能講出完全相反的顏色），風格關鍵字只是氛圍參考，
  不用逐字提到
- 第一人稱、輕鬆自然，可以加 0-2 個 hashtag，也可以完全不加
- 長度像正常社群貼文，不用刻意寫長
- 只回傳 caption 文字本身，不要加引號或其他說明
- 每次寫法都不一樣，避免固定句型（不要每篇都是「今天穿了...超適合...」這種套路）
"""


# ---------- 階段 1：抓圖 ----------

def fetch_posts(target_count: int, out_dir: Path, start_page: int = 1, exclude_dirs: list[Path] | None = None) -> list[dict]:
    raw_path = out_dir / "posts_raw.json"
    if raw_path.exists():
        existing = json.loads(raw_path.read_text(encoding="utf-8"))
        if len(existing) >= target_count:
            print(f"[抓圖] {raw_path} 已經有 {len(existing)} 篇（>= 目標 {target_count}），跳過重抓")
            return existing[:target_count]
        print(f"[抓圖] 已有 {len(existing)} 篇，不足目標 {target_count}，重新抓一次完整批次")

    pexels_key = os.environ.get("PEXELS_API_KEY")
    if not pexels_key:
        raise SystemExit("請先在 .env 設定 PEXELS_API_KEY")

    per_query = min(80, math.ceil(target_count / len(QUERIES) * 1.2) + 1)
    print(f"[抓圖] 目標 {target_count} 篇，{len(QUERIES)} 個關鍵字，每個關鍵字抓 {per_query} 張"
          f"（從第 {start_page} 頁開始，避免跟之前抓過的重複）")

    excluded_ids: set[int] = set()
    for exclude_dir in exclude_dirs or []:
        prior_path = exclude_dir / "posts_raw.json"
        if prior_path.exists():
            prior = json.loads(prior_path.read_text(encoding="utf-8"))
            excluded_ids.update(int(p["post_id"].rsplit("-", 1)[-1]) for p in prior)
    if excluded_ids:
        print(f"[抓圖] 從 {len(exclude_dirs or [])} 個舊批次載入 {len(excluded_ids)} 個要排除的 ID")

    raw_posts: list[dict] = []
    seen_ids: set[int] = set(excluded_ids)
    skipped_dupes = 0
    for query, tilt in QUERIES:
        page = start_page
        # 同一個關鍵字最多翻 3 頁，把被排除掉的重複補回來，避免總數明顯不足。
        for _ in range(3):
            if len(raw_posts) >= target_count:
                break
            resp = requests.get(
                PEXELS_SEARCH_URL,
                headers={"Authorization": pexels_key},
                params={"query": query, "per_page": per_query, "page": page, "orientation": "portrait"},
                timeout=15,
            )
            resp.raise_for_status()
            photos = resp.json().get("photos", [])
            if not photos:
                break
            new_this_page = 0
            for photo in photos:
                if photo["id"] in seen_ids or len(raw_posts) >= target_count:
                    if photo["id"] in excluded_ids:
                        skipped_dupes += 1
                    continue
                seen_ids.add(photo["id"])
                new_this_page += 1
                raw_posts.append(
                    {
                        "post_id": f"post-pexels-batch-{photo['id']}",
                        "image_url": photo["src"]["large"],
                        "photographer": photo["photographer"],
                        "photographer_url": photo["photographer_url"],
                        "pexels_url": photo["url"],
                        "alt_description": photo.get("alt") or "",
                        "search_query": query,
                        "ethnicity_tilt": tilt,
                        "source": "pexels_licensed",
                        "source_checked_at": time.strftime("%Y-%m-%d"),
                    }
                )
            page += 1
            if new_this_page == 0:
                # 這一頁整頁都被排除掉了（都跟舊批次重複），繼續翻下一頁補足。
                continue
        print(f"  \"{query}\" -> 累計 {len(raw_posts)}/{target_count}")
        time.sleep(1)
        if len(raw_posts) >= target_count:
            break
    if skipped_dupes:
        print(f"[抓圖] 跳過了 {skipped_dupes} 個跟舊批次重複的 ID")

    if len(raw_posts) < target_count:
        print(f"[抓圖] 警告：只抓到 {len(raw_posts)} 篇，不到目標 {target_count} 篇"
              f"（Pexels 這幾個關鍵字的候選量有限，可以加更多關鍵字或提高 per_query）")

    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(raw_posts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[抓圖] 完成，{len(raw_posts)} 篇 -> {raw_path}")
    return raw_posts


def download_images(raw_posts: list[dict], out_dir: Path) -> None:
    image_dir = out_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    downloaded = skipped = failed = 0
    for i, post in enumerate(raw_posts, start=1):
        fpath = image_dir / f"{post['post_id']}.jpg"
        if fpath.exists():
            skipped += 1
            continue
        try:
            resp = requests.get(post["image_url"], timeout=20)
            resp.raise_for_status()
            fpath.write_bytes(resp.content)
            downloaded += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{len(raw_posts)}] 下載失敗 {post['post_id']}：{exc}")
            failed += 1
        if i % 50 == 0:
            print(f"  下載進度 {i}/{len(raw_posts)}")
    print(f"[下載圖片] 新下載 {downloaded}、已存在跳過 {skipped}、失敗 {failed}")


# ---------- 階段 2：FashionCLIP + YOLOS 屬性抽取 ----------

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
    return picked


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
            crop_colors = classify(crop_embed, color_text_bank, COLORS, GARMENT_COLOR_THRESHOLD, 2, force_top1=True)
        garments.append(
            {
                "label": label,
                "bbox": [round(x1 / width, 4), round(y1 / height, 4), round(x2 / width, 4), round(y2 / height, 4)],
                "colors": crop_colors,
                "detection_score": round(pred["score"], 4),
            }
        )
    return garments


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "unknown"


def extract_attributes(raw_posts: list[dict], out_dir: Path) -> list[dict]:
    posts_path = out_dir / "posts.json"
    creators_path = out_dir / "creators.json"
    image_dir = out_dir / "images"

    posts: list[dict] = json.loads(posts_path.read_text(encoding="utf-8")) if posts_path.exists() else []
    creators: dict[str, dict] = (
        {c["creator_id"]: c for c in json.loads(creators_path.read_text(encoding="utf-8"))}
        if creators_path.exists() else {}
    )
    done_ids = {p["post_id"] for p in posts}
    todo = [p for p in raw_posts if p["post_id"] not in done_ids]
    if not todo:
        print(f"[屬性抽取] 全部 {len(posts)} 篇都已經處理過，跳過")
        return posts
    print(f"[屬性抽取] {len(done_ids)} 篇已完成、{len(todo)} 篇待處理")

    print("  載入 FashionCLIP ...")
    clip_model = CLIPModel.from_pretrained(FASHION_CLIP_MODEL)
    clip_processor = CLIPProcessor.from_pretrained(FASHION_CLIP_MODEL)
    clip_model.eval()
    print("  載入偵測模型 ...")
    detector_processor = AutoImageProcessor.from_pretrained(DETECTOR_MODEL)
    detector_model = AutoModelForObjectDetection.from_pretrained(DETECTOR_MODEL)
    detector_model.eval()

    text_banks = {
        name: build_text_bank(clip_model, clip_processor, labels, template)
        for name, labels, template, *_ in CATEGORY_CONFIG
    }
    color_text_bank = text_banks["colors"]

    for i, raw in enumerate(todo, start=1):
        print(f"  [{i}/{len(todo)}] {raw['post_id']} ...")
        image_path = image_dir / f"{raw['post_id']}.jpg"
        if not image_path.exists():
            print("    跳過（圖片不存在，可能下載失敗）")
            continue
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as exc:  # noqa: BLE001
            print(f"    跳過（讀圖失敗）：{exc}")
            continue

        image_embeds = embed_image(clip_model, clip_processor, image)
        attrs: dict[str, list[str]] = {}
        unknown_fields: list[str] = []
        for name, labels, _t, threshold, max_k, force_top1 in CATEGORY_CONFIG:
            picked = classify(image_embeds, text_banks[name], labels, threshold, max_k, force_top1)
            attrs[name] = picked
            if not picked:
                unknown_fields.append(name)

        garments = detect_garments(detector_model, detector_processor, clip_model, clip_processor, color_text_bank, image)

        creator_id = f"creator-demo-{slugify(raw['photographer'])}"
        creators.setdefault(
            creator_id,
            {
                "creator_id": creator_id,
                "display_name": raw["photographer"],
                "source": "pexels_licensed",
                "source_url": raw["photographer_url"],
                "is_demo": True,
            },
        )

        posts.append(
            {
                "post_id": raw["post_id"],
                "creator_id": creator_id,
                "image_url": raw["image_url"],
                "alt_description": raw["alt_description"],
                "search_query": raw["search_query"],
                "ethnicity_tilt": raw["ethnicity_tilt"],
                "styles": attrs["styles"],
                "colors": attrs["colors"],
                "occasion": attrs["occasion"],
                "fits": attrs["fits"],
                "materials": attrs["materials"],
                "unknown_fields": unknown_fields,
                "garments": garments,
                "tagged_products": [],
                "source": raw["source"],
                "source_checked_at": raw["source_checked_at"],
                "is_demo": True,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

        if i % 25 == 0:
            posts_path.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
            creators_path.write_text(json.dumps(list(creators.values()), ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"    （已存檔進度：{len(posts)} 篇）")

    posts_path.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    creators_path.write_text(json.dumps(list(creators.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[屬性抽取] 完成，共 {len(posts)} 篇 -> {posts_path}")
    return posts


# ---------- 階段 3：生成配文 ----------

def build_caption_prompt(post: dict) -> str:
    return CAPTION_PROMPT.format(
        styles="、".join(post["styles"]) or "沒有特別明顯",
        colors="、".join(post["colors"]) or "沒有特別明顯",
        alt=post.get("alt_description") or "無",
    )


def call_groq_with_retry(client: Groq, prompt: str, attempts: int = 4) -> str:
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=1.0,
                max_tokens=150,
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            wait = 5 * (attempt + 1)
            print(f"    重試 {attempt + 1}/{attempts}（等 {wait}s）：{exc}")
            time.sleep(wait)
    print(f"    放棄：{last_exc}")
    return ""


def generate_captions(posts: list[dict], out_dir: Path) -> list[dict]:
    out_path = out_dir / "posts_with_captions.json"
    results: list[dict] = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else []
    done_ids = {p["post_id"] for p in results if p.get("generated_caption")}
    todo = [p for p in posts if p["post_id"] not in done_ids]
    if not todo:
        print(f"[生成配文] 全部 {len(results)} 篇都已經有配文，跳過")
        return results
    print(f"[生成配文] {len(done_ids)} 篇已完成、{len(todo)} 篇待處理")

    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        raise SystemExit("請先在 .env 設定 GROQ_API_KEY")
    client = Groq(api_key=groq_key)

    by_id = {p["post_id"]: p for p in results}
    for i, post in enumerate(todo, start=1):
        print(f"  [{i}/{len(todo)}] {post['post_id']} ...")
        caption = call_groq_with_retry(client, build_caption_prompt(post))
        by_id[post["post_id"]] = {**post, "generated_caption": caption}
        time.sleep(2)  # 8000 tokens/min 額度，保守間隔避免撞到

        if i % 25 == 0:
            out_path.write_text(json.dumps(list(by_id.values()), ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"    （已存檔進度：{len(by_id)} 篇）")

    final = list(by_id.values())
    out_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[生成配文] 完成，共 {len(final)} 篇 -> {out_path}")
    return final


# ---------- 階段 4：產生 HTML 報告 ----------

def esc(s: str | None) -> str:
    return html.escape(s or "", quote=True)


def boxes_html(garments: list[dict]) -> str:
    out = []
    for g in garments:
        x1, y1, x2, y2 = g["bbox"]
        color = GARMENT_COLOR_HEX.get(g["label"], "#999")
        out.append(
            f'<div class="box" style="left:{x1*100:.2f}%;top:{y1*100:.2f}%;'
            f'width:{(x2-x1)*100:.2f}%;height:{(y2-y1)*100:.2f}%;border-color:{color}">'
            f'<span class="box-label" style="background:{color}">{esc(g["label"])} {g["detection_score"]:.2f}</span></div>'
        )
    return "".join(out)


def tag_row(values: list[str]) -> str:
    if not values:
        return '<span class="tag tag--empty">（無）</span>'
    return "".join(f'<span class="tag">{esc(v)}</span>' for v in values)


def build_report(posts: list[dict], out_dir: Path) -> None:
    cards = []
    for p in posts:
        tilt = p.get("ethnicity_tilt", "neutral")
        badge = f'<span class="badge" style="background:{TILT_COLOR_HEX.get(tilt, "#6b6480")}">{esc(TILT_LABEL_ZH.get(tilt, tilt))}</span>'
        attr_rows = "".join(
            f'<div class="attr-row"><span class="attr-label">{CAT_LABELS_ZH[name]}</span>'
            f'<span class="attr-values">{tag_row(p.get(name, []))}</span></div>'
            for name in ["styles", "colors", "occasion", "fits", "materials"]
        )
        cards.append(f"""
    <article class="card">
      <div class="card__media">
        <img src="images/{esc(p['post_id'])}.jpg" alt="" loading="lazy">
        {boxes_html(p.get('garments', []))}
        {badge}
      </div>
      <div class="card__body">
        <p class="card__caption">{esc(p.get('generated_caption') or '（未生成）')}</p>
        <div class="attrs">{attr_rows}</div>
        <div class="card__meta">
          <span>{esc(p.get('search_query', ''))}</span>
          <span>Pexels · {esc(p.get('creator_id', '').replace('creator-demo-',''))}</span>
        </div>
      </div>
    </article>""")

    total = len(posts)
    no_caption = sum(1 for p in posts if not p.get("generated_caption"))
    garment_counts = Counter(g["label"] for p in posts for g in p.get("garments", []))
    tilt_counts = Counter(p.get("ethnicity_tilt", "neutral") for p in posts)
    legend = "".join(
        f'<span class="legend-item"><span class="dot" style="background:{c}"></span>{l}（{garment_counts.get(l,0)}）</span>'
        for l, c in GARMENT_COLOR_HEX.items()
    )
    tilt_summary = " · ".join(f"{TILT_LABEL_ZH[k]} {v}" for k, v in tilt_counts.items())

    page = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>亞洲穿搭樣本批次</title>
<style>
:root {{ color-scheme: light dark;
  --bg: #f4f3f6; --surface: #ffffff; --surface-2: #ebe9f0; --border: #dcd9e4;
  --ink: #201c2b; --ink-dim: #5b5668; --accent: #a53e5c; --accent-ink: #ffffff;
  --tag-bg: #ebe6f5; --tag-ink: #4a3f66;
  --font-display: Georgia, "Noto Serif TC", serif;
  --font-body: system-ui, "Noto Sans TC", sans-serif;
  --font-mono: ui-monospace, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #17151d; --surface: #201d29; --surface-2: #2a2634; --border: #38334a;
    --ink: #eeecf3; --ink-dim: #a9a3ba; --accent: #e8879e; --accent-ink: #201121;
    --tag-bg: #322c47; --tag-ink: #d8d0ec;
  }}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font-family: var(--font-body); padding-inline: 20px; }}
main {{ max-width: 1220px; margin: 0 auto; padding-block: 32px 56px; }}
header.hero {{ padding-block: 8px 24px; border-bottom: 1px solid var(--border); margin-bottom: 24px; }}
h1 {{ font-family: var(--font-display); font-size: clamp(24px,4vw,36px); font-weight: 600; margin: 0 0 10px; }}
.hero p {{ color: var(--ink-dim); font-size: 14px; line-height: 1.6; max-width: 72ch; margin: 0; }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap: 1px; background: var(--border); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; margin-block: 20px; }}
.stat {{ background: var(--surface); padding: 14px 16px; }}
.stat__value {{ font-family: var(--font-display); font-size: 22px; font-weight: 600; }}
.stat__label {{ font-size: 11.5px; color: var(--ink-dim); margin-top: 2px; }}
.panel {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 14px 18px; margin-bottom: 24px; font-size: 13px; }}
.legend-row {{ display: flex; flex-wrap: wrap; gap: 4px 16px; }}
.legend-item {{ color: var(--ink-dim); }}
.dot {{ display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 5px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill,minmax(240px,1fr)); gap: 16px; }}
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; display: flex; flex-direction: column; }}
.card__media {{ position: relative; aspect-ratio: 3/4; background: var(--surface-2); }}
.card__media img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.box {{ position: absolute; border: 2px solid; border-radius: 3px; }}
.box-label {{ position: absolute; top: -17px; left: -2px; font-size: 9.5px; font-family: var(--font-mono); color: #fff; padding: 1px 5px; border-radius: 3px; white-space: nowrap; }}
.badge {{ position: absolute; top: 10px; left: 10px; font-size: 10.5px; font-family: var(--font-mono); padding: 2px 8px; border-radius: 999px; color: #fff; }}
.card__body {{ padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 8px; }}
.card__caption {{ font-size: 13.5px; line-height: 1.55; margin: 0; font-weight: 500; }}
.attrs {{ display: flex; flex-direction: column; gap: 4px; border-top: 1px solid var(--border); padding-top: 8px; }}
.attr-row {{ display: grid; grid-template-columns: 40px 1fr; gap: 8px; font-size: 11px; }}
.attr-label {{ color: var(--ink-dim); font-family: var(--font-mono); }}
.attr-values {{ display: flex; flex-wrap: wrap; gap: 4px; }}
.tag {{ background: var(--tag-bg); color: var(--tag-ink); padding: 1px 8px; border-radius: 999px; font-size: 10.5px; }}
.tag--empty {{ background: transparent; color: var(--ink-dim); padding: 0; }}
.card__meta {{ display: flex; justify-content: space-between; font-size: 10px; color: var(--ink-dim); border-top: 1px solid var(--border); padding-top: 8px; }}
</style>
</head>
<body>
<main>
  <header class="hero">
    <h1>亞洲穿搭樣本批次（{total} 篇）</h1>
    <p>Pexels 合法授權照片 → FashionCLIP + YOLOS-fashionpedia 屬性抽取 → Groq 生成自然語氣中文配文。人種比例：{esc(tilt_summary)}。</p>
  </header>
  <div class="stats">
    <div class="stat"><div class="stat__value">{total}</div><div class="stat__label">照片數</div></div>
    <div class="stat"><div class="stat__value">{total-no_caption}</div><div class="stat__label">成功生成配文</div></div>
    <div class="stat"><div class="stat__value">{sum(garment_counts.values())}</div><div class="stat__label">偵測到的單品總數</div></div>
  </div>
  <div class="panel">
    <div class="legend-row">{legend}</div>
  </div>
  <div class="grid">
    {"".join(cards)}
  </div>
</main>
</body>
</html>
"""
    report_path = out_dir / "report.html"
    report_path.write_text(page, encoding="utf-8")
    print(f"[HTML 報告] 完成 -> {report_path}")


# ---------- 階段 5：附加進正式資料庫 + 重建 combined catalog ----------

ALLOWED_GARMENT_LABELS = {"top", "bottom", "shoes", "outerwear", "dress"}
FIXTURES_POSTS = Path("data/fixtures/posts.json")
FIXTURES_CREATORS = Path("data/fixtures/creators.json")


def _to_compliant_post(p: dict) -> dict:
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


def _to_compliant_creator(c: dict) -> dict:
    return {"creator_id": c["creator_id"], "display_name": c["display_name"], "is_demo": c["is_demo"]}


def append_to_fixtures_and_rebuild(posts: list[dict], out_dir: Path) -> None:
    """只會「附加」進 data/fixtures/。發現 id 衝突就中止、不寫入任何檔案。"""
    sys.path.insert(0, ".")
    from backend.schemas import Creator, Post  # noqa: PLC0415

    creators_path = out_dir / "creators.json"
    raw_creators = json.loads(creators_path.read_text(encoding="utf-8"))

    missing_captions = [p["post_id"] for p in posts if not p.get("generated_caption")]
    if missing_captions:
        raise SystemExit(f"[附加進資料庫] 中止：{len(missing_captions)} 篇還沒有配文，例如：{missing_captions[:5]}")

    new_posts = [_to_compliant_post(p) for p in posts]
    new_creators = [_to_compliant_creator(c) for c in raw_creators]

    for post in new_posts:
        Post(**post)
    for creator in new_creators:
        Creator(**creator)
    print(f"[附加進資料庫] 驗證通過：{len(new_posts)} 篇貼文、{len(new_creators)} 位創作者符合 schema")

    existing_posts = json.loads(FIXTURES_POSTS.read_text(encoding="utf-8"))
    existing_creators = json.loads(FIXTURES_CREATORS.read_text(encoding="utf-8"))
    existing_post_ids = {p["post_id"] for p in existing_posts}
    existing_creator_ids = {c["creator_id"] for c in existing_creators}
    new_post_ids = {p["post_id"] for p in new_posts}

    # 貼文 id 重複才是真的問題（代表同一篇貼文被加了兩次），直接中止。
    post_collisions = existing_post_ids & new_post_ids
    if post_collisions:
        raise SystemExit(
            f"[附加進資料庫] 中止，發現 post_id 衝突，沒有動任何檔案：{list(post_collisions)[:5]}"
        )

    # 同一個攝影師／創作者出現在多個批次很正常，不是衝突；只加入真的沒見過的創作者。
    creators_to_add = [c for c in new_creators if c["creator_id"] not in existing_creator_ids]
    skipped_creators = len(new_creators) - len(creators_to_add)

    combined_posts = existing_posts + new_posts
    combined_creators = existing_creators + creators_to_add
    FIXTURES_POSTS.write_text(json.dumps(combined_posts, ensure_ascii=False, indent=2), encoding="utf-8")
    FIXTURES_CREATORS.write_text(json.dumps(combined_creators, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[附加進資料庫] posts.json {len(existing_posts)} -> {len(combined_posts)}（附加，非覆蓋）")
    print(f"[附加進資料庫] creators.json {len(existing_creators)} -> {len(combined_creators)}"
          f"（附加 {len(creators_to_add)} 位新創作者，{skipped_creators} 位已存在故跳過，非覆蓋）")

    print("[重建 catalog] 執行 scripts/build_combined_catalog.py ...")
    subprocess.run([sys.executable, "scripts/build_combined_catalog.py"], check=True)


# ---------- 主流程 ----------

def main() -> None:
    parser = argparse.ArgumentParser(description="抓圖 -> 屬性抽取 -> 生成配文 -> HTML 報告，一次跑完")
    parser.add_argument("--count", type=int, default=500, help="目標照片數量")
    parser.add_argument("--out-dir", type=str, default="data/asian_fashion_batch", help="輸出資料夾")
    parser.add_argument("--start-page", type=int, default=1,
                        help="Pexels 搜尋結果從第幾頁開始抓；抓第二批時設 2 才不會跟第一批重複")
    parser.add_argument("--exclude-dir", action="append", default=[],
                        help="排除這個資料夾裡 posts_raw.json 已經抓過的 ID，可重複指定多個；抓第二批時指向第一批的資料夾")
    parser.add_argument("--skip-fetch", action="store_true", help="跳過抓圖/下載階段")
    parser.add_argument("--skip-extract", action="store_true", help="跳過 FashionCLIP/YOLOS 屬性抽取階段")
    parser.add_argument("--skip-captions", action="store_true", help="跳過配文生成階段")
    parser.add_argument("--append-to-fixtures", action="store_true",
                        help="最後把這批資料附加進 data/fixtures/posts.json、creators.json 並重建 combined catalog；"
                             "只會附加，發現 id 衝突會中止、不寫入任何檔案")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.skip_fetch:
        raw_posts = json.loads((out_dir / "posts_raw.json").read_text(encoding="utf-8"))
        print(f"[抓圖] 跳過，讀取既有 {len(raw_posts)} 篇")
    else:
        raw_posts = fetch_posts(args.count, out_dir, start_page=args.start_page,
                                exclude_dirs=[Path(d) for d in args.exclude_dir])
        download_images(raw_posts, out_dir)

    if args.skip_extract:
        posts = json.loads((out_dir / "posts.json").read_text(encoding="utf-8"))
        print(f"[屬性抽取] 跳過，讀取既有 {len(posts)} 篇")
    else:
        posts = extract_attributes(raw_posts, out_dir)

    if args.skip_captions:
        posts = json.loads((out_dir / "posts_with_captions.json").read_text(encoding="utf-8"))
        print(f"[生成配文] 跳過，讀取既有 {len(posts)} 篇")
    else:
        posts = generate_captions(posts, out_dir)

    build_report(posts, out_dir)
    print(f"[HTML 報告] 用瀏覽器打開：{(out_dir / 'report.html').resolve()}")

    if args.append_to_fixtures:
        append_to_fixtures_and_rebuild(posts, out_dir)

    print("\n全部完成！")


if __name__ == "__main__":
    main()
