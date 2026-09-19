"""把 data/posts.json 產生成一份本地 HTML 報告，方便人工檢查抽取品質。

每張貼文顯示：原圖（疊上 YOLOS-fashionpedia 偵測到的單品框）、
FashionCLIP 判斷出來的 styles/colors/occasion/fits/materials 標籤、
以及被判定「看不準留空」的 unknown_fields。

用法：
    python scripts/generate_qa_report.py
    打開 data/qa_report.html 用瀏覽器看
"""

from __future__ import annotations

import json
from pathlib import Path

POSTS_PATH = Path("data/posts.json")
OUT_PATH = Path("data/qa_report.html")

GARMENT_COLORS = {
    "top": "#3b82f6",
    "bottom": "#22c55e",
    "shoes": "#f97316",
    "outerwear": "#a855f7",
    "accessory": "#ec4899",
    "dress": "#ef4444",
}


def render_boxes(garments: list[dict]) -> str:
    boxes = []
    for g in garments:
        x1, y1, x2, y2 = g["bbox"]
        color = GARMENT_COLORS.get(g["label"], "#999")
        boxes.append(
            f'<div class="box" style="'
            f"left:{x1*100:.2f}%; top:{y1*100:.2f}%; "
            f"width:{(x2-x1)*100:.2f}%; height:{(y2-y1)*100:.2f}%; "
            f'border-color:{color};">'
            f'<span class="box-label" style="background:{color};">'
            f'{g["label"]} {g["detection_score"]:.2f}</span></div>'
        )
    return "".join(boxes)


def render_tags(values: list[str], cls: str) -> str:
    if not values:
        return '<span class="tag empty">（無）</span>'
    return "".join(f'<span class="tag {cls}">{v}</span>' for v in values)


def render_card(post: dict) -> str:
    unknown = ", ".join(post.get("unknown_fields", [])) or "無"
    return f"""
    <div class="card">
      <div class="img-wrap">
        <img src="{post['image_url']}" loading="lazy" />
        {render_boxes(post.get("garments", []))}
      </div>
      <div class="meta">
        <div class="post-id">{post['post_id']}</div>
        <div class="row"><b>styles</b> {render_tags(post['styles'], 'style')}</div>
        <div class="row"><b>colors</b> {render_tags(post['colors'], 'color')}</div>
        <div class="row"><b>occasion</b> {render_tags(post['occasion'], 'occasion')}</div>
        <div class="row"><b>fits</b> {render_tags(post['fits'], 'fit')}</div>
        <div class="row"><b>materials</b> {render_tags(post['materials'], 'material')}</div>
        <div class="row unknown"><b>unknown_fields</b> {unknown}</div>
        <div class="row creator">creator: {post['creator_id']}</div>
      </div>
    </div>
    """


def main() -> None:
    posts = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    cards = "\n".join(render_card(p) for p in posts)

    legend = "".join(
        f'<span class="legend-item"><span class="dot" style="background:{c}"></span>{label}</span>'
        for label, c in GARMENT_COLORS.items()
    )

    html = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8" />
<title>貼文抽取結果 QA</title>
<style>
  body {{ font-family: -apple-system, "Noto Sans TC", sans-serif; background:#111; color:#eee; margin:0; padding:24px; }}
  h1 {{ font-size:18px; margin-bottom:4px; }}
  .sub {{ color:#999; font-size:13px; margin-bottom:16px; }}
  .legend {{ margin-bottom:20px; font-size:13px; }}
  .legend-item {{ margin-right:16px; }}
  .dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:4px; }}
  .grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap:20px; }}
  .card {{ background:#1c1c1c; border-radius:8px; overflow:hidden; }}
  .img-wrap {{ position:relative; width:100%; aspect-ratio: 3/4; background:#000; }}
  .img-wrap img {{ width:100%; height:100%; object-fit:cover; display:block; }}
  .box {{ position:absolute; border:2px solid; box-sizing:border-box; }}
  .box-label {{ position:absolute; top:-18px; left:-2px; font-size:10px; color:#fff; padding:1px 4px; border-radius:3px; white-space:nowrap; }}
  .meta {{ padding:10px 12px; font-size:12px; }}
  .post-id {{ font-weight:bold; margin-bottom:6px; color:#aaa; }}
  .row {{ margin-bottom:4px; }}
  .tag {{ display:inline-block; padding:1px 6px; border-radius:10px; margin:1px; font-size:11px; }}
  .tag.style {{ background:#1e3a5f; }}
  .tag.color {{ background:#3f2f1e; }}
  .tag.occasion {{ background:#1e3f2a; }}
  .tag.fit {{ background:#3f1e3a; }}
  .tag.material {{ background:#3f3a1e; }}
  .tag.empty {{ background:#333; color:#777; }}
  .unknown {{ color:#f87171; }}
  .creator {{ color:#666; margin-top:4px; }}
</style>
</head>
<body>
  <h1>貼文抽取結果 QA（{len(posts)} 篇）</h1>
  <div class="sub">FashionCLIP 分類 + YOLOS-fashionpedia 偵測；框線顏色 = 單品類別</div>
  <div class="legend">{legend}</div>
  <div class="grid">
    {cards}
  </div>
</body>
</html>
"""
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"產生 {OUT_PATH}（{len(posts)} 篇），用瀏覽器打開即可")


if __name__ == "__main__":
    main()
