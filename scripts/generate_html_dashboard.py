import json
import os

with open(r'C:\Users\Eric Yu\.gemini\antigravity\brain\b3c7eeb9-853a-4830-9691-227367107bae\top_hits_b64.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

html = '''<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FashionCLIP 多模態檢索最高分圖片看板</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    .tab-btn.active {
      background-color: #2563eb !important;
      color: #ffffff !important;
      border-color: transparent !important;
    }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 antialiased p-6 min-h-screen">
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-800 pb-5 gap-4">
      <div>
        <div class="flex items-center gap-2">
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            Role C / F Data & Multi-Modal Embeddings
          </span>
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">
            FashionCLIP 512d
          </span>
        </div>
        <h1 class="text-2xl md:text-3xl font-bold mt-2 tracking-tight">👗 多模態 Retrieval 最高分實體商品檢索展示</h1>
        <p class="text-sm text-slate-400 mt-1">
          本機 FashionCLIP 實體模型計算 512 件商品型錄之 Relevance 分數，展示每種檢索方式得分最高之商品實體照片。
        </p>
      </div>

      <!-- Quick Method Switcher Tabs -->
      <div class="inline-flex p-1 bg-slate-900 rounded-xl border border-slate-800 self-start md:self-auto">
        <button onclick="showTab('image')" id="btn-image" class="tab-btn active px-4 py-2 text-sm font-medium rounded-lg transition-all text-white">
          🖼️ 以圖搜圖 (Image)
        </button>
        <button onclick="showTab('text')" id="btn-text" class="tab-btn px-4 py-2 text-sm font-medium rounded-lg transition-all text-slate-400 hover:text-white">
          🔍 文字檢索 (Text)
        </button>
        <button onclick="showTab('mixed')" id="btn-mixed" class="tab-btn px-4 py-2 text-sm font-medium rounded-lg transition-all text-slate-400 hover:text-white">
          ⚡ 圖文混合 (RRF)
        </button>
      </div>
    </div>
'''

def render_section(sec_id, title, desc, query_badge, items, is_visible):
    disp = 'block' if is_visible else 'none'
    res = f'<div id="sec-{sec_id}" style="display: {disp};" class="space-y-4">'
    res += f'''
      <div class="bg-slate-900 p-4 rounded-xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
        <div>
          <h2 class="text-lg font-semibold text-slate-100 flex items-center gap-2">{title}</h2>
          <p class="text-xs text-slate-400 mt-0.5">{desc}</p>
        </div>
        <div class="bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-xs font-mono text-slate-300">
          {query_badge}
        </div>
      </div>

      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
    '''
    for item in items:
        rank = item['rank']
        score = item['score']
        name = item['name']
        cat = item['cat']
        price = item['price']
        pid = item['id']
        b64 = item.get('b64', '')
        score_pct = int(score * 100)
        
        rank_badge = 'bg-amber-400 text-black font-bold' if rank == 1 else ('bg-slate-300 text-slate-900 font-semibold' if rank == 2 else ('bg-amber-600 text-white font-semibold' if rank == 3 else 'bg-slate-800 text-slate-300 border border-slate-700'))

        res += f'''
        <div class="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden shadow hover:border-blue-500/50 transition-all flex flex-col group">
          <div class="relative aspect-[3/4] bg-slate-950 overflow-hidden flex items-center justify-center">
            <img src="{b64}" alt="{name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300">
            <span class="absolute top-2 left-2 px-2 py-0.5 rounded text-xs shadow-md {rank_badge}">
              #{rank}
            </span>
            <span class="absolute bottom-2 right-2 px-2 py-0.5 rounded text-xs font-mono font-bold bg-slate-950/80 backdrop-blur text-emerald-400 border border-emerald-500/30">
              {score:.4f}
            </span>
          </div>
          <div class="p-3 flex flex-col flex-grow justify-between gap-2">
            <div>
              <div class="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                <span class="uppercase tracking-wider font-semibold text-slate-400">{cat}</span>
                <span class="font-semibold text-emerald-400">NT$ {price}</span>
              </div>
              <h3 class="text-xs font-medium line-clamp-2 text-slate-200 group-hover:text-blue-400 transition-colors" title="{name}">
                {name}
              </h3>
            </div>
            <div class="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-400">
              <span class="font-mono">{pid}</span>
              <span class="text-blue-400 font-medium">{score_pct}% match</span>
            </div>
          </div>
        </div>
        '''
    res += '</div></div>'
    return res

html += render_section(
    'image',
    '🖼️ 純以圖搜圖 (Visual Search) 前 6 名最高分結果',
    '輸入米色印花短T照片，比對全型錄 512 件商品視覺特徵 (L2-norm Cosine Similarity)',
    'Query: 54933.jpg (米色短T照片)',
    data['image_search'],
    True
)

html += render_section(
    'text',
    '🔍 文字語意檢索 (Text Search) 前 6 名最高分結果',
    '輸入字串「Blue printed T-shirt」，比對商品 search_text 語意特徵',
    'Query: "Blue printed T-shirt"',
    data['text_search'],
    False
)

html += render_section(
    'mixed',
    '⚡ 圖文混合檢索 (Mixed RRF Search) 前 6 名最高分結果',
    '結合短T照片版型與「Blue casual」文字，採用倒數排名融合演算法 (Reciprocal Rank Fusion)',
    'Query: Image(54933.jpg) + "Blue casual"',
    data['mixed_search'],
    False
)

html += '''
    <!-- Footer Note -->
    <div class="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300 space-y-1">
      <p class="font-semibold flex items-center gap-1.5 text-blue-200">
        <span>💡</span> 後續管線對接說明 (Role C / F 交付物)：
      </p>
      <p>
        本模組產出之 <code>relevance</code> 分數已完全規格化在 [0.0, 1.0] 範圍內。
        下游推薦模組只需直接代入既定加權公式：<code>S_item = 0.60 * relevance + 0.35 * preference + 0.05 * trend</code>，即可完成最終排序！
      </p>
    </div>
  </div>

  <script>
    function showTab(type) {
      ['image', 'text', 'mixed'].forEach(t => {
        document.getElementById('sec-' + t).style.display = (t === type) ? 'block' : 'none';
        const btn = document.getElementById('btn-' + t);
        if (t === type) {
          btn.className = 'tab-btn active px-4 py-2 text-sm font-medium rounded-lg transition-all text-white';
        } else {
          btn.className = 'tab-btn px-4 py-2 text-sm font-medium rounded-lg transition-all text-slate-400 hover:text-white';
        }
      });
    }
  </script>
</body>
</html>
'''

target_path = r'C:\Users\Eric Yu\.gemini\antigravity\brain\b3c7eeb9-853a-4830-9691-227367107bae\retrieval_dashboard.html'
with open(target_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Successfully wrote HTML dashboard to {target_path} (size: {len(html)} bytes)')

