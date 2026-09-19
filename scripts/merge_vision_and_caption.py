"""測試腳本：把「純圖片」跟「圖文並用」兩條線的結果做最終合併，
圖片端（FashionCLIP）當最後的仲裁者——文字這邊多講的東西，如果圖片
完全不支持，就不採用，維持以圖片為主。

背景：test_mastodon_pipeline.py 產生 vision_only（純圖片，FashionCLIP
门檻篩過的最終標籤），extract_with_caption.py 產生 caption_aware
（LLM 讀 caption ± 圖片，可能講出 vision_only 沒選到的標籤）。
兩邊是分開跑的，caption_aware 完全有可能講出圖片其實看不出來的東西
（LLM 幻覺、或純文字 fallback 沒看圖）。

合併規則（每個 styles/colors/occasion/fits/materials 欄位分別做）：
    1. vision_only 選到的，保留（vision 的門檻本來就篩過，相信它）。
    2. caption_aware 多講的標籤，如果 vision_only 沒選到，不是直接丟掉
       也不是直接採用，而是回頭問 FashionCLIP：這個標籤對這張圖片的
       cosine similarity 有沒有「差不多接近但沒過門檻」（relaxed
       threshold = 門檻 - 0.04）。
           - 有 → 圖片不反對，算文字幫忙補了圖片門檻卡掉的訊號，採用。
           - 沒有（分數明顯低）→ 圖片明確不支持，判定文字這邊講錯
             （fallback 沒看圖、或 LLM 幻覺），不採用，維持圖片為主。
    單品顏色（garment_mentions vs YOLOS crop 顏色）也用同一個邏輯，
    但直接比對已經算好的 crop 顏色（不用重新跑模型）：一致就採用，
    衝突就以 crop 的顏色為準。

輸入：data/mastodon_test/posts_with_caption.json
      data/mastodon_test/embeddings/<post_id>.npy（test_mastodon_pipeline.py 存的圖片 embedding）
輸出：data/mastodon_test/posts_merged.json

用法：
    python scripts/merge_vision_and_caption.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from transformers import CLIPModel, CLIPProcessor

from vocab import COLORS, FITS, MATERIALS, OCCASIONS, STYLES

IN_PATH = Path("data/mastodon_test/posts_with_caption.json")
EMBEDDINGS_DIR = Path("data/mastodon_test/embeddings")
OUT_PATH = Path("data/mastodon_test/posts_merged.json")

FASHION_CLIP_MODEL = "patrickjohncyh/fashion-clip"
RELAXED_MARGIN = 0.04

# 跟 test_mastodon_pipeline.py 用同一組門檻，只是這裡多算一個 relaxed_threshold。
CATEGORY_CONFIG = [
    ("styles", STYLES, "a photo of an outfit in {} style", 0.21),
    ("colors", COLORS, "an outfit that is mainly {} colored", 0.19),
    ("occasion", OCCASIONS, "an outfit suitable for {}", 0.20),
    ("fits", FITS, "clothing with a {} fit", 0.20),
    ("materials", MATERIALS, "clothing made of {} material", 0.24),
]


def build_text_bank(model, processor, labels, template):
    texts = [template.format(label) for label in labels]
    inputs = processor(text=texts, return_tensors="pt", padding=True)
    with torch.no_grad():
        text_embeds = model.get_text_features(**inputs).pooler_output
    return text_embeds / text_embeds.norm(dim=-1, keepdim=True)


def resolve_category(image_embed: torch.Tensor, text_bank: torch.Tensor, labels: list[str],
                      pick_threshold: float, vision_picks: list[str], caption_picks: list[str]):
    sims = (image_embed @ text_bank.T).squeeze(0)
    score_by_label = dict(zip(labels, sims.tolist()))
    relaxed_threshold = pick_threshold - RELAXED_MARGIN

    decisions = []
    final = list(vision_picks)
    for label in vision_picks:
        decisions.append({"label": label, "status": "vision_pick", "score": round(score_by_label.get(label, 0.0), 4)})

    for label in caption_picks:
        if label in vision_picks:
            for d in decisions:
                if d["label"] == label:
                    d["status"] = "agreed_both"
            continue
        score = score_by_label.get(label, 0.0)
        if score >= relaxed_threshold:
            decisions.append({"label": label, "status": "text_added_image_plausible", "score": round(score, 4)})
            final.append(label)
        else:
            decisions.append({"label": label, "status": "rejected_conflicts_with_image", "score": round(score, 4)})

    return list(dict.fromkeys(final)), decisions


def resolve_garments(garments: list[dict]) -> list[dict]:
    enriched = []
    for g in garments:
        vision_colors = g.get("colors", [])
        claimed_color = g.get("caption_color")
        if not g.get("caption_confirmed"):
            status, final_color = "no_caption_mention", (vision_colors[0] if vision_colors else None)
        elif not claimed_color:
            status, final_color = "text_confirmed_no_color_claim", (vision_colors[0] if vision_colors else None)
        elif claimed_color in vision_colors:
            status, final_color = "color_agreed", claimed_color
        else:
            status, final_color = "color_conflict_kept_vision", (vision_colors[0] if vision_colors else claimed_color)
        enriched.append({**g, "color_status": status, "final_color": final_color})
    return enriched


def main() -> None:
    posts = json.loads(IN_PATH.read_text(encoding="utf-8"))

    print("載入 FashionCLIP 文字端 ...")
    model = CLIPModel.from_pretrained(FASHION_CLIP_MODEL)
    processor = CLIPProcessor.from_pretrained(FASHION_CLIP_MODEL)
    model.eval()

    text_banks = {
        name: build_text_bank(model, processor, labels, template)
        for name, labels, template, _ in CATEGORY_CONFIG
    }

    results = []
    total_rejected = 0
    total_added = 0
    for post in posts:
        embed_path = EMBEDDINGS_DIR / f"{post['post_id']}.npy"
        image_embed = torch.from_numpy(np.load(embed_path)).unsqueeze(0)

        merged = {}
        decisions_by_category = {}
        for name, labels, _template, threshold in CATEGORY_CONFIG:
            final, decisions = resolve_category(
                image_embed, text_banks[name], labels, threshold,
                post["vision_only"][name], post["caption_aware"][name],
            )
            merged[name] = final
            decisions_by_category[name] = decisions
            total_rejected += sum(1 for d in decisions if d["status"] == "rejected_conflicts_with_image")
            total_added += sum(1 for d in decisions if d["status"] == "text_added_image_plausible")

        results.append(
            {
                **post,
                "merged": merged,
                "merge_decisions": decisions_by_category,
                "garments": resolve_garments(post["garments"]),
            }
        )

    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"完成：{len(results)} 篇 -> {OUT_PATH}")
    print(f"文字補上、圖片不反對而採用：{total_added} 個標籤")
    print(f"文字講了但圖片明確不支持、被拒絕：{total_rejected} 個標籤")


if __name__ == "__main__":
    main()
