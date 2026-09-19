"""
Generate search results showcase with 30 items across 3 methods (Text, Image, Mixed).
Encodes thumbnails to base64 and outputs a rich interactive HTML artifact.
"""

import base64
import json
import sys
from io import BytesIO
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.schemas import Product, SearchRequest
from backend.search import search_products


def image_to_base64_thumbnail(img_path_or_url: str, max_size=(180, 240)) -> str:
    """Convert local image to base64 jpeg thumbnail."""
    try:
        p = Path(img_path_or_url)
        if p.is_file():
            with Image.open(p) as img:
                img = img.convert("RGB")
                img.thumbnail(max_size)
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=80)
                return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        pass

    # SVG Placeholder fallback
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="180" height="240" viewBox="0 0 180 240">
        <rect width="180" height="240" fill="#333"/>
        <text x="50%" y="50%" fill="#aaa" font-size="14" text-anchor="middle" dominant-baseline="middle">No Image</text>
    </svg>'''
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("utf-8")


def find_image_for_product(product_id: str, catalog_images_dir: Path) -> str:
    # Check kaggle image
    clean_id = product_id.replace("kaggle-", "").replace("gu-", "")
    for ext in [".jpg", ".jpeg", ".png"]:
        f = catalog_images_dir / f"{clean_id}{ext}"
        if f.is_file():
            return str(f)
    return ""


def main():
    catalog_file = Path("data/products.json")
    with open(catalog_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    catalog = [Product.model_validate(x) for x in data]
    catalog_img_dir = Path("data/catalog/kaggle_500/images")

    # -------------------------------------------------------------
    # 1. Method 1: Text Search (10 items)
    # -------------------------------------------------------------
    q1_text = "黑色 寬鬆 休閒 襯衫"
    req1 = SearchRequest(session_id="showcase-01", query_text=q1_text, mode="text", limit=10)
    resp1 = search_products(req1, catalog)

    # -------------------------------------------------------------
    # 2. Method 2: Image Search (10 items)
    # -------------------------------------------------------------
    q2_img_file = "data/catalog/kaggle_500/images/54933.jpg" # Beige Boys T-shirt
    req2 = SearchRequest(session_id="showcase-02", query_image=q2_img_file, mode="image", limit=10)
    resp2 = search_products(req2, catalog)

    # -------------------------------------------------------------
    # 3. Method 3: Mixed Search (10 items)
    # -------------------------------------------------------------
    q3_text = "休閒 短袖 運動 印花"
    req3 = SearchRequest(
        session_id="showcase-03",
        query_text=q3_text,
        query_image=q2_img_file,
        mode="mixed",
        image_weight=0.6,
        limit=10
    )
    resp3 = search_products(req3, catalog)

    # Prepare data dict for HTML
    methods_data = [
        {
            "id": "method-text",
            "name": "方法一：文字語意檢索 (Text Search)",
            "icon": "🔍",
            "query": f"文字輸入：「{q1_text}」",
            "desc": "以 FashionCLIP Text Encoder 抽取語意向量，與 512 件商品文字特徵比對 Cosine Similarity",
            "hits": []
        },
        {
            "id": "method-image",
            "name": "方法二：純以圖搜圖 (Image Search)",
            "icon": "🖼️",
            "query": "參考圖片：米色印花短T (images/54933.jpg)",
            "query_img_b64": image_to_base64_thumbnail(q2_img_file),
            "desc": "以 FashionCLIP Image Encoder 抽取視覺特徵，比對 512 件商品圖檔視覺相似度（第 1 名精確命中原圖 1.0000）",
            "hits": []
        },
        {
            "id": "method-mixed",
            "name": "方法三：圖文混合檢索 (Mixed RRF Search)",
            "icon": "⚡",
            "query": f"參考圖 + 需求「{q3_text}」（圖片權重 0.6 / 文字權重 0.4）",
            "query_img_b64": image_to_base64_thumbnail(q2_img_file),
            "desc": "利用倒數排名融合（RRF）同時考量圖片版型相似度與文字屬性標籤，融合成最終 relevance 分數",
            "hits": []
        }
    ]

    for resp, method_info in zip([resp1, resp2, resp3], methods_data):
        for idx, hit in enumerate(resp.products, 1):
            p = hit.product
            img_path = find_image_for_product(hit.product_id, catalog_img_dir)
            b64_img = image_to_base64_thumbnail(img_path)
            method_info["hits"].append({
                "rank": idx,
                "product_id": hit.product_id,
                "name": p.name if p else "n/a",
                "category": p.category if p else "n/a",
                "price": p.price if p else 0,
                "colors": p.colors if p else [],
                "styles": p.styles if p else [],
                "score": round(hit.score, 4),
                "image_b64": b64_img,
            })

    # Generate HTML Artifact
    artifact_dir = Path("C:/Users/Eric Yu/.gemini/antigravity/brain/b3c7eeb9-853a-4830-9691-227367107bae")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    html_file = artifact_dir / "search_results_showcase.html"

    json_str = json.dumps(methods_data, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>FashionCLIP 檢索 30 筆成果展示</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      margin: 0;
      padding: 16px;
      background: var(--background, #0f172a);
      color: var(--foreground, #f8fafc);
    }}
    .tab-btn.active {{
      background: var(--primary, #3b82f6);
      color: #fff;
      font-weight: 600;
    }}
  </style>
</head>
<body class="min-h-screen">
  <div class="max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <header class="flex flex-col md:flex-row justify-between items-start md:items-center pb-4 border-b border-[var(--border,#334155)] gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-[var(--foreground,#f8fafc)] flex items-center gap-2">
          <span>✨</span> FashionCLIP 多模態檢索 30 筆成果展示
        </h1>
        <p class="text-sm text-[var(--muted-foreground,#94a3b8)] mt-1">
          涵蓋三種檢索模式（文字、以圖搜圖、圖文混合 RRF），全館 512 件真實商品實體比對
        </p>
      </div>
      <div class="flex items-center gap-2 text-xs bg-[var(--card,#1e293b)] px-3 py-1.5 rounded-full border border-[var(--border,#334155)]">
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <span>FashionCLIP Cosine Relevance</span>
      </div>
    </header>

    <!-- Method Tabs -->
    <nav class="flex flex-wrap gap-2 p-1.5 bg-[var(--card,#1e293b)] rounded-xl border border-[var(--border,#334155)]" id="tabs">
      <!-- Generated via JS -->
    </nav>

    <!-- Query Info Card -->
    <div id="query-card" class="p-4 rounded-xl bg-[var(--card,#1e293b)] border border-[var(--border,#334155)] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
      <!-- Generated via JS -->
    </div>

    <!-- Product Grid (10 items) -->
    <main>
      <div id="products-grid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        <!-- Generated via JS -->
      </div>
    </main>
  </div>

  <script>
    const data = {json_str};
    let activeIndex = 0;

    function renderTabs() {{
      const tabsEl = document.getElementById("tabs");
      tabsEl.innerHTML = data.map((m, idx) => `
        <button 
          onclick="switchTab(${{idx}})" 
          class="tab-btn px-4 py-2 rounded-lg text-sm transition-all flex items-center gap-2 ${{idx === activeIndex ? 'active shadow-sm' : 'text-[var(--muted-foreground,#94a3b8)] hover:bg-[var(--border,#334155)]'}}"
        >
          <span>${{m.icon}}</span>
          <span>${{m.name}}</span>
          <span class="text-xs opacity-75 px-1.5 py-0.5 rounded-full bg-black/20">10筆</span>
        </button>
      `).join("");
    }}

    function renderActiveMethod() {{
      const m = data[activeIndex];
      const queryCard = document.getElementById("query-card");
      
      let queryImgHtml = "";
      if (m.query_img_b64) {{
        queryImgHtml = `
          <div class="flex items-center gap-3 bg-[var(--background,#0f172a)] p-2 rounded-lg border border-[var(--border,#334155)]">
            <img src="${{m.query_img_b64}}" class="w-12 h-16 object-cover rounded shadow" alt="Query Image"/>
            <div class="text-xs text-[var(--muted-foreground,#94a3b8)]">參考輸入圖</div>
          </div>
        `;
      }}

      queryCard.innerHTML = `
        <div class="space-y-1">
          <div class="text-xs font-semibold uppercase tracking-wider text-[var(--primary,#3b82f6)]">當前搜尋情境</div>
          <div class="text-base font-bold text-[var(--foreground,#f8fafc)]">${{m.query}}</div>
          <div class="text-xs text-[var(--muted-foreground,#94a3b8)]">${{m.desc}}</div>
        </div>
        ${{queryImgHtml}}
      `;

      const gridEl = document.getElementById("products-grid");
      gridEl.innerHTML = m.hits.map(item => `
        <div class="group relative bg-[var(--card,#1e293b)] rounded-xl border border-[var(--border,#334155)] overflow-hidden shadow-sm hover:border-[var(--primary,#3b82f6)] hover:shadow-md transition-all flex flex-col">
          <!-- Rank Badge -->
          <div class="absolute top-2 left-2 z-10 px-2 py-0.5 rounded-md text-xs font-bold bg-black/70 text-white backdrop-blur-sm border border-white/10">
            #${{item.rank}}
          </div>
          
          <!-- Score Badge -->
          <div class="absolute top-2 right-2 z-10 px-2 py-0.5 rounded-md text-xs font-semibold bg-emerald-500/90 text-white backdrop-blur-sm shadow">
            ${{(item.score * 100).toFixed(1)}}%
          </div>

          <!-- Product Image -->
          <div class="w-full aspect-[3/4] bg-slate-950 flex items-center justify-center overflow-hidden">
            <img 
              src="${{item.image_b64}}" 
              alt="${{item.name}}" 
              class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              loading="lazy"
            />
          </div>

          <!-- Details -->
          <div class="p-3 flex-1 flex flex-col justify-between space-y-2">
            <div>
              <div class="flex items-center justify-between text-[11px] text-[var(--muted-foreground,#94a3b8)]">
                <span class="uppercase tracking-wider font-semibold">${{item.category}}</span>
                <span class="font-mono text-emerald-400 font-bold">$${{item.price}}</span>
              </div>
              <h3 class="text-xs font-medium text-[var(--foreground,#f8fafc)] line-clamp-2 mt-1 leading-snug" title="${{item.name}}">
                ${{item.name}}
              </h3>
            </div>

            <!-- Tags -->
            <div class="flex flex-wrap gap-1 pt-1 border-t border-[var(--border,#334155)]/50 text-[10px]">
              ${{item.colors.slice(0, 2).map(c => `<span class="px-1.5 py-0.5 rounded bg-[var(--background,#0f172a)] text-[var(--muted-foreground,#94a3b8)]">${{c}}</span>`).join("")}}
              <span class="text-[10px] text-slate-500 font-mono ml-auto">ID: ${{item.product_id.split('-').pop()}}</span>
            </div>
          </div>
        </div>
      `).join("");
    }}

    function switchTab(index) {{
      activeIndex = index;
      renderTabs();
      renderActiveMethod();
    }}

    renderTabs();
    renderActiveMethod();
  </script>
</body>
</html>
"""

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n[SUCCESS] Generated Interactive 30-item Showcase HTML artifact at:")
    print(f"  {html_file}")


if __name__ == "__main__":
    main()

