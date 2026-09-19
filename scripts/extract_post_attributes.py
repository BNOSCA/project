"""從純圖片（無配文、無 products.json）抽取「圖片版 Intent」。

改用 FashionCLIP + 開放詞彙偵測模型，不再呼叫 Gemini：

    - styles/colors/occasion/fits/materials：用 FashionCLIP 對受控詞彙表
      做 zero-shot 分類（圖片 embedding 跟每個詞的文字 embedding 算
      cosine similarity），deterministic、免費本地跑、不會撞 API 配額，
      而且是 fashion 領域訓練過的模型，準確度比通用 LLM 用猜的更可靠。
    - garments：用 YOLOS-fashionpedia（在 Fashionpedia 資料集上訓練的
      服裝偵測模型）抓出每件單品的真實 bbox 跟類別，再對裁切出來的區域
      跑一次 FashionCLIP 顏色分類，得到單品層級的顏色。這一步 LLM 完全
      做不到（LLM 不是為空間定位設計的，草稿版本的 Gemini bbox 全部是
      [1,1,1,1] 就是證據）；一開始改用通用開放詞彙偵測模型 OWL-ViT 效果
      也不好（同一張圖信心分數只有 0.04-0.17，鞋子/上衣常常抓不到），
      換成專門在服裝資料集訓練過的 YOLOS-fashionpedia 後分數普遍到
      0.6-0.97，明顯更可靠。
    - 不產生任何自由文字描述（visual_semantic_tag 已移除）。
    - unknown_fields：分數沒有任何一個超過門檻的欄位，留空並記錄在這裡，
      不強行選一個最高分但其實很不confident的標籤（比照 Intent 的規則）。

輸入：data/posts_raw.json（scripts/fetch_demo_posts.py 產生）
輸出：
    - data/posts.json               貼文屬性（tagged_products 留空，
                                     沒有 products.json 可比對）
    - data/creators.json            demo 創作者資料
    - data/embeddings/<post_id>.npy 該貼文的 FashionCLIP 圖片 embedding，
                                     供之後貼文相似度/貼文-商品比對使用
"""

from __future__ import annotations

import argparse
import json
import os
import time
from io import BytesIO
from pathlib import Path

import numpy as np
import requests
import torch
from dotenv import load_dotenv
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForObjectDetection, CLIPModel, CLIPProcessor

load_dotenv()
# 讓 huggingface_hub 用認證連線下載模型權重，速度快很多、也不會撞匿名限流。
if os.environ.get("HF_TOKEN"):
    os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", os.environ["HF_TOKEN"])

from vocab import (
    COLORS,
    FASHIONPEDIA_LABEL_TO_GARMENT,
    FITS,
    GARMENT_LABELS,
    MATERIALS,
    OCCASIONS,
    STYLES,
)

RAW_PATH = Path("data/posts_raw.json")
POSTS_OUT_PATH = Path("data/posts.json")
CREATORS_OUT_PATH = Path("data/creators.json")
EMBEDDINGS_DIR = Path("data/embeddings")

FASHION_CLIP_MODEL = "patrickjohncyh/fashion-clip"
DETECTOR_MODEL = "valentinafeve/yolos-fashionpedia"

# (詞彙表, prompt 模板, 相似度門檻, 最多選幾個, 沒有任何一個過門檻時是否強制選最高分一個)
#
# occasion 從 max_k=2 降成 1：實測發現 top1/top2 分數常常只差 0.001-0.01，
# 選第二名等於一半是雜訊（例如純休閒照被硬塞 "sport"）。
# materials 門檻拉高到 0.24 且只留 1 個：實測材質判斷常常是錯的
# （棉質工裝外套被判成 leather），寧可大部分留空也不要用力猜。
CATEGORY_CONFIG = [
    ("styles", STYLES, "a photo of an outfit in {} style", 0.21, 3, False),
    ("colors", COLORS, "an outfit that is mainly {} colored", 0.19, 3, True),
    ("occasion", OCCASIONS, "an outfit suitable for {}", 0.20, 1, False),
    ("fits", FITS, "clothing with a {} fit", 0.20, 2, False),
    ("materials", MATERIALS, "clothing made of {} material", 0.24, 1, False),
]

GARMENT_COLOR_THRESHOLD = 0.19
# YOLOS-fashionpedia 的信心分數普遍比通用開放詞彙偵測模型高很多
# （實測 0.6-0.97），門檻可以設得比 OWL-ViT 時保守很多。
GARMENT_DETECTION_SCORE_THRESHOLD = 0.35


def load_image(url: str) -> Image.Image:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return Image.open(BytesIO(resp.content)).convert("RGB")


def build_text_bank(
    model: CLIPModel, processor: CLIPProcessor, labels: list[str], template: str
) -> torch.Tensor:
    texts = [template.format(label) for label in labels]
    inputs = processor(text=texts, return_tensors="pt", padding=True)
    with torch.no_grad():
        # 新版 transformers 的 get_text_features 回傳整個 BaseModelOutputWithPooling，
        # 投影後的 embedding 放在 .pooler_output（見 CLIPModel.get_text_features 原始碼）。
        text_embeds = model.get_text_features(**inputs).pooler_output
    return text_embeds / text_embeds.norm(dim=-1, keepdim=True)


def embed_image(model: CLIPModel, processor: CLIPProcessor, image: Image.Image) -> torch.Tensor:
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        image_embeds = model.get_image_features(**inputs).pooler_output
    return image_embeds / image_embeds.norm(dim=-1, keepdim=True)


def classify(
    image_embeds: torch.Tensor,
    text_embeds: torch.Tensor,
    labels: list[str],
    threshold: float,
    max_k: int,
    force_top1: bool,
) -> tuple[list[str], list[tuple[str, float]]]:
    sims = (image_embeds @ text_embeds.T).squeeze(0)
    ranked = sorted(zip(labels, sims.tolist()), key=lambda x: -x[1])
    picked = [label for label, score in ranked if score >= threshold][:max_k]
    if not picked and force_top1 and ranked:
        picked = [ranked[0][0]]
    return picked, ranked


def detect_garments(
    detector_model: AutoModelForObjectDetection,
    detector_processor: AutoImageProcessor,
    clip_model: CLIPModel,
    clip_processor: CLIPProcessor,
    color_text_bank: torch.Tensor,
    image: Image.Image,
) -> list[dict]:
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
            continue  # 忽略 collar/sleeve/pocket 這類服裝局部細節
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
                crop_embed, color_text_bank, COLORS,
                GARMENT_COLOR_THRESHOLD, 2, force_top1=True,
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
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="只處理前 N 張，先小量測試用")
    parser.add_argument("--debug", action="store_true", help="印出每個類別的完整相似度分數")
    args = parser.parse_args()

    if not RAW_PATH.exists():
        raise SystemExit(f"找不到 {RAW_PATH}，請先跑 fetch_demo_posts.py")

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

    raw_posts = json.loads(RAW_PATH.read_text(encoding="utf-8"))

    posts: list[dict] = []
    creators: dict[str, dict] = {}
    already_done: set[str] = set()
    if POSTS_OUT_PATH.exists():
        posts = json.loads(POSTS_OUT_PATH.read_text(encoding="utf-8"))
        already_done = {p["post_id"] for p in posts}
    if CREATORS_OUT_PATH.exists():
        for c in json.loads(CREATORS_OUT_PATH.read_text(encoding="utf-8")):
            creators[c["creator_id"]] = c

    raw_posts = [r for r in raw_posts if r["post_id"] not in already_done]
    if args.limit:
        raw_posts = raw_posts[: args.limit]
    if already_done:
        print(f"略過 {len(already_done)} 篇已抽取過的貼文，本次處理 {len(raw_posts)} 篇")

    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

    for i, raw in enumerate(raw_posts, start=1):
        print(f"[{i}/{len(raw_posts)}] 處理 {raw['post_id']} ...")
        try:
            image = load_image(raw["image_url"])
        except Exception as exc:  # noqa: BLE001
            print(f"  跳過（下載失敗）：{exc}")
            continue

        image_embeds = embed_image(clip_model, clip_processor, image)
        np.save(EMBEDDINGS_DIR / f"{raw['post_id']}.npy", image_embeds.squeeze(0).numpy())

        attrs: dict[str, list[str]] = {}
        unknown_fields: list[str] = []
        for name, labels, _template, threshold, max_k, force_top1 in CATEGORY_CONFIG:
            picked, ranked = classify(
                image_embeds, text_banks[name], labels, threshold, max_k, force_top1
            )
            attrs[name] = picked
            if not picked:
                unknown_fields.append(name)
            if args.debug:
                top3 = ", ".join(f"{l}={s:.3f}" for l, s in ranked[:3])
                print(f"    {name}: picked={picked} top3=({top3})")

        garments = detect_garments(
            detector_model, detector_processor, clip_model, clip_processor, color_text_bank, image
        )

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
                "styles": attrs["styles"],
                "colors": attrs["colors"],
                "occasion": attrs["occasion"],
                "fits": attrs["fits"],
                "materials": attrs["materials"],
                "unknown_fields": unknown_fields,
                "garments": garments,
                "image_embedding_id": raw["post_id"],
                "tagged_products": [],  # 沒有 products.json 可比對，先留空
                "source": "pexels_licensed_demo_content",
                "source_checked_at": raw["source_checked_at"],
                "is_demo": True,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

    POSTS_OUT_PATH.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    CREATORS_OUT_PATH.write_text(
        json.dumps(list(creators.values()), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"完成：{len(posts)} 篇貼文 -> {POSTS_OUT_PATH}")
    print(f"完成：{len(creators)} 位 demo 創作者 -> {CREATORS_OUT_PATH}")


if __name__ == "__main__":
    main()
