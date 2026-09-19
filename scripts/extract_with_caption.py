"""測試腳本：把貼文的文字（caption）跟圖片一起餵給多模態 LLM，
看「加入文字」跟純圖片版的 FashionCLIP/YOLOS 抽取結果差多少。

背景：extract_post_attributes.py 的 styles/colors/occasion/fits/materials
全部只看圖片，YOLOS-fashionpedia 的 bbox 也只看圖片，兩者都完全沒用到
caption。Pexels 那批本來就沒有像樣的 caption，所以這不是問題；但這批
Mastodon 貼文的 caption 是本人寫的，常常直接點名單品顏色/類型
（例如「黑色西裝外套搭配牛仔褲」），純圖片抽取沒有用到這個訊號。

這支腳本刻意不去動 bbox（YOLOS 的空間定位比 LLM 可靠，team 之前試過
Gemini 抓 bbox 是全部 [1,1,1,1] 的爛結果，見 extract_post_attributes.py
開頭說明），只讓 LLM 用「圖片 + caption」一起做兩件事：
    1. 重新判斷 styles/colors/occasion/fits/materials（跟 FashionCLIP
       用同一組受控詞彙表），可以跟純圖片版對照，看文字有沒有幫助。
    2. 抓 caption 裡有明確點名的單品（garment_mentions），拿去對應
       YOLOS 偵測到的同類別 bbox，等於用文字幫圖片偵測結果做「有沒有
       文字證據」的驗證標記（caption_confirmed）。

輸入：data/mastodon_test/posts.json（test_mastodon_pipeline.py 的輸出，
      已經有 YOLOS bbox 跟純圖片版 tags）
輸出：data/mastodon_test/posts_with_caption.json

主要走 Gemini（圖片+文字一起看）；Gemini 免費額度很小（5 requests/min），
連續失敗時自動退到 Groq 純文字版（只看 caption，看不到圖片，但一樣能抓
「牛仔褲」「西裝外套」這種明講的單品/顏色詞），保證這批資料還是能跑完，
每篇結果都會記錄實際是哪個來源（extraction_source）。

用法：
    python scripts/extract_with_caption.py [--limit N]
    需要 .env 裡的 GEMINI_API_KEY，選配 GROQ_API_KEY（fallback 用）
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import Groq

from vocab import COLORS, FITS, GARMENT_LABELS, MATERIALS, OCCASIONS, STYLES

load_dotenv()

SEED_DIR = Path(
    "黑客松爬蟲-20260919T071454Z-1-001/黑客松爬蟲/data/social_fashion_seed_chinese_ootd"
)
IN_PATH = Path("data/mastodon_test/posts.json")
OUT_PATH = Path("data/mastodon_test/posts_with_caption.json")

GEMINI_MODEL = "gemini-3.6-flash"
GROQ_MODEL = "openai/gpt-oss-120b"

PROMPT_TEMPLATE = """你是時尚圖文標註員。以下是一則社群貼文的圖片和文字說明（caption）。
請同時參考圖片內容和文字說明（兩者互相佐證，文字提到但圖片看不出來的也可以採用），
輸出這則貼文穿搭的屬性，欄位值必須是以下受控詞彙表裡的字（英文小寫），
看不出來的欄位就輸出空陣列，不要用力猜。

styles 候選：{styles}
colors 候選：{colors}
occasion 候選：{occasion}
fits 候選：{fits}
materials 候選：{materials}
garment 類別候選（garment_mentions 的 label 只能用這些）：{garments}

另外，如果 caption 文字裡有明確點名穿搭單品（例如「牛仔褲」「西裝外套」「小背心」），
列在 garment_mentions，每一項包含：
- label：對應到上面 garment 類別候選的其中一個
- phrase：從 caption 裡直接摘錄的原文詞語
- color：這個單品的顏色（用 colors 候選裡的字），看不出來就是 null

caption 全文：
「{caption}」

只回傳 JSON，格式：
{{"styles": [...], "colors": [...], "occasion": [...], "fits": [...], "materials": [...],
  "garment_mentions": [{{"label": "...", "phrase": "...", "color": "..."}}]}}
"""

# Groq fallback 只看得到文字，拿掉「圖片」相關措辭，避免它假裝有看圖。
TEXT_ONLY_PROMPT_TEMPLATE = """你是時尚文字標註員。以下是一則社群貼文的文字說明（caption），
你**看不到圖片**，只能根據文字本身判斷。
請輸出這則貼文穿搭的屬性，欄位值必須是以下受控詞彙表裡的字（英文小寫），
文字裡完全沒提到、看不出來的欄位就輸出空陣列，不要用力猜。

styles 候選：{styles}
colors 候選：{colors}
occasion 候選：{occasion}
fits 候選：{fits}
materials 候選：{materials}
garment 類別候選（garment_mentions 的 label 只能用這些）：{garments}

如果 caption 文字裡有明確點名穿搭單品（例如「牛仔褲」「西裝外套」「小背心」），
列在 garment_mentions，每一項包含：
- label：對應到上面 garment 類別候選的其中一個
- phrase：從 caption 裡直接摘錄的原文詞語
- color：這個單品的顏色（用 colors 候選裡的字），文字沒提到就是 null

caption 全文：
「{caption}」

只回傳 JSON，格式：
{{"styles": [...], "colors": [...], "occasion": [...], "fits": [...], "materials": [...],
  "garment_mentions": [{{"label": "...", "phrase": "...", "color": "..."}}]}}
"""


def call_gemini_with_retry(client: genai.Client, image_path: Path, caption: str, attempts: int = 3) -> dict:
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return call_gemini(client, image_path, caption)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            wait = 10 * (attempt + 1)
            print(f"  Gemini 重試 {attempt + 1}/{attempts}（等 {wait}s）：{exc}")
            time.sleep(wait)
    raise last_exc  # type: ignore[misc]


def call_gemini(client: genai.Client, image_path: Path, caption: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        styles=", ".join(STYLES),
        colors=", ".join(COLORS),
        occasion=", ".join(OCCASIONS),
        fits=", ".join(FITS),
        materials=", ".join(MATERIALS),
        garments=", ".join(GARMENT_LABELS),
        caption=caption.replace("\n", " ") or "（無文字）",
    )
    image_bytes = image_path.read_bytes()
    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime),
            prompt,
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)


def call_groq_text_only(client: Groq, caption: str) -> dict:
    prompt = TEXT_ONLY_PROMPT_TEMPLATE.format(
        styles=", ".join(STYLES),
        colors=", ".join(COLORS),
        occasion=", ".join(OCCASIONS),
        fits=", ".join(FITS),
        materials=", ".join(MATERIALS),
        garments=", ".join(GARMENT_LABELS),
        caption=caption.replace("\n", " ") or "（無文字）",
    )
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def extract_attributes(gemini_client: genai.Client, groq_client: Groq | None, image_path: Path, caption: str) -> tuple[dict, str]:
    try:
        return call_gemini_with_retry(gemini_client, image_path, caption), "gemini_multimodal"
    except Exception as exc:  # noqa: BLE001
        print(f"  Gemini 放棄，改用 Groq 純文字 fallback：{exc}")
    if groq_client is None:
        return {"styles": [], "colors": [], "occasion": [], "fits": [], "materials": [], "garment_mentions": []}, "failed"
    try:
        return call_groq_text_only(groq_client, caption), "groq_text_only"
    except Exception as exc:  # noqa: BLE001
        print(f"  Groq fallback 也失敗：{exc}")
        return {"styles": [], "colors": [], "occasion": [], "fits": [], "materials": [], "garment_mentions": []}, "failed"


def match_garments_to_captions(garments: list[dict], mentions: list[dict]) -> list[dict]:
    mentions_by_label: dict[str, list[dict]] = {}
    for m in mentions:
        mentions_by_label.setdefault(m.get("label"), []).append(m)

    enriched = []
    for g in garments:
        candidates = mentions_by_label.get(g["label"], [])
        match = candidates.pop(0) if candidates else None
        enriched.append(
            {
                **g,
                "caption_confirmed": match is not None,
                "caption_phrase": match["phrase"] if match else None,
                "caption_color": match.get("color") if match else None,
            }
        )
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only", type=str, default=None, help="逗號分隔的 post_id，只重跑這幾篇並合併回既有輸出")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("請先在 .env 設定 GEMINI_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")
    groq_client = Groq(api_key=groq_key) if groq_key else None
    if groq_client is None:
        print("警告：沒有設定 GROQ_API_KEY，Gemini 失敗時不會有 fallback")

    if not IN_PATH.exists():
        raise SystemExit(f"找不到 {IN_PATH}，請先跑 scripts/test_mastodon_pipeline.py")

    posts = json.loads(IN_PATH.read_text(encoding="utf-8"))
    if args.limit:
        posts = posts[: args.limit]

    only_ids = set(args.only.split(",")) if args.only else None
    if only_ids:
        posts = [p for p in posts if p["post_id"] in only_ids]

    gemini_client = genai.Client(api_key=api_key)

    fresh_results = {}
    for i, post in enumerate(posts, start=1):
        print(f"[{i}/{len(posts)}] {post['post_id']} ...")
        image_path = SEED_DIR / post["image_url"]
        llm_out, source = extract_attributes(gemini_client, groq_client, image_path, post["caption"])
        print(f"  來源：{source}")
        time.sleep(2)  # 客氣地限速，避免撞免費額度

        mentions = llm_out.get("garment_mentions", []) or []
        fresh_results[post["post_id"]] = {
            **post,
            "vision_only": {
                "styles": post["styles"],
                "colors": post["colors"],
                "occasion": post["occasion"],
                "fits": post["fits"],
                "materials": post["materials"],
            },
            "caption_aware": {
                "styles": llm_out.get("styles", []),
                "colors": llm_out.get("colors", []),
                "occasion": llm_out.get("occasion", []),
                "fits": llm_out.get("fits", []),
                "materials": llm_out.get("materials", []),
            },
            "extraction_source": source,
            "garment_mentions": mentions,
            "garments": match_garments_to_captions(post["garments"], mentions),
        }

    if only_ids and OUT_PATH.exists():
        existing = {p["post_id"]: p for p in json.loads(OUT_PATH.read_text(encoding="utf-8"))}
        existing.update(fresh_results)
        results = list(existing.values())
    else:
        results = list(fresh_results.values())

    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    confirmed = sum(1 for r in results for g in r["garments"] if g["caption_confirmed"])
    total_garments = sum(len(r["garments"]) for r in results)
    print(f"完成：{len(results)} 篇 -> {OUT_PATH}")
    print(f"單品偵測共 {total_garments} 件，其中 {confirmed} 件有 caption 文字佐證")


if __name__ == "__main__":
    main()
