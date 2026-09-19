"""Local-only debug dashboard for verifying the post-feed x mastodon-ootd-fixtures
integration: does /api/v1/feed actually run rank_feed(), how much of the fixture
catalog survives the diversity cap, and which posts are missing product info.

Not part of the product API contract. Mount only behind a debug flag / locally.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from .mock import MockServices


def build_debug_router(get_service) -> APIRouter:
    router = APIRouter()

    @router.get("/debug/catalog-summary")
    def catalog_summary() -> dict:
        service: MockServices = get_service()
        catalog = service.catalog
        posts = []
        for post in catalog.posts:
            posts.append({
                "post_id": post.post_id,
                "creator_id": post.creator_id,
                "source": post.source,
                "tagged_products_count": len(post.tagged_products),
                "detected_regions_count": len(post.detected_regions),
                "like_count": post.engagement.like_count,
                "save_count": post.engagement.save_count,
            })
        creators = {}
        for post in catalog.posts:
            creators[post.creator_id] = creators.get(post.creator_id, 0) + 1
        return {
            "total_posts": len(catalog.posts),
            "creators": creators,
            "posts": posts,
        }

    @router.get("/debug/feed-dashboard", response_class=HTMLResponse)
    def feed_dashboard() -> str:
        return _DASHBOARD_HTML

    return router


_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8" />
<title>post-feed x mastodon-ootd 整合測試儀表板</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: -apple-system, "Noto Sans TC", sans-serif; margin: 0; padding: 24px; background: #0b0d12; color: #e6e8ec; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  .sub { color: #9aa3af; font-size: 13px; margin-bottom: 20px; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 24px; }
  .card { background: #161a22; border: 1px solid #262c38; border-radius: 10px; padding: 14px 16px; }
  .card .num { font-size: 26px; font-weight: 700; }
  .card .label { font-size: 12px; color: #9aa3af; margin-top: 2px; }
  .card.warn { border-color: #7a4a1e; background: #201409; }
  .card.warn .num { color: #f0a84e; }
  .card.bad { border-color: #7a2020; background: #200909; }
  .card.bad .num { color: #f05a5a; }
  .card.ok .num { color: #57c97a; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
  th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid #22262f; }
  th { color: #9aa3af; font-weight: 600; position: sticky; top: 0; background: #0b0d12; }
  tr.missing-post { background: #200909; }
  tr.no-products { color: #f0a84e; }
  .pill { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 11px; }
  .pill.mastodon { background: #1e3a5f; color: #7db8ff; }
  .pill.demo { background: #333; color: #ccc; }
  .badge-ok { color: #57c97a; }
  .badge-bad { color: #f05a5a; }
  section { margin-bottom: 28px; }
  h2 { font-size: 15px; margin: 0 0 8px; }
  #status { color: #9aa3af; font-size: 13px; }
</style>
</head>
<body>
  <h1>post-feed &times; mastodon-ootd-fixtures 整合測試儀表板</h1>
  <div class="sub">直接打本機 API,不經過前端。只反映目前 fixtures + rank_feed() 的真實行為。</div>
  <div id="status">載入中…</div>

  <div class="cards" id="cards"></div>

  <section>
    <h2>Feed 排序結果(依 rank_feed 實際分數,完整翻頁)</h2>
    <table>
      <thead><tr><th>Rank</th><th>Post ID</th><th>來源</th><th>Creator</th><th>Score</th><th>Tagged Products</th><th>Detected Regions</th><th>Ranking Reason</th></tr></thead>
      <tbody id="feed-rows"></tbody>
    </table>
  </section>

  <section>
    <h2>從未出現在 feed 中的貼文(fixtures 有,但 rank_feed 多樣性上限把它擋掉)</h2>
    <table>
      <thead><tr><th>Post ID</th><th>來源</th><th>Creator</th><th>Tagged Products</th><th>Detected Regions</th></tr></thead>
      <tbody id="missing-rows"></tbody>
    </table>
  </section>

<script>
async function main() {
  const statusEl = document.getElementById('status');
  const summary = await (await fetch('/debug/catalog-summary')).json();

  // 翻頁把 rank_feed 完整結果收集起來
  let items = [];
  let cursor = null;
  let guard = 0;
  while (guard++ < 50) {
    const params = new URLSearchParams({ user_id: 'anonymous-demo', limit: '20' });
    if (cursor) params.set('cursor', cursor);
    const page = await (await fetch('/api/v1/feed?' + params.toString())).json();
    items = items.concat(page.items);
    if (!page.next_cursor || page.next_cursor === cursor) break;
    cursor = page.next_cursor;
  }

  const byId = Object.fromEntries(summary.posts.map(p => [p.post_id, p]));
  const seen = new Set(items.map(i => i.post_id));
  const missing = summary.posts.filter(p => !seen.has(p.post_id));
  const noProductInfo = items.filter(i => {
    const p = byId[i.post_id];
    return p && p.tagged_products_count === 0 && p.detected_regions_count === 0;
  });

  statusEl.textContent = `fixtures 共 ${summary.total_posts} 篇貼文 · rank_feed 完整翻頁後回傳 ${items.length} 篇`;

  const cards = document.getElementById('cards');
  const card = (num, label, cls) => `<div class="card ${cls||''}"><div class="num">${num}</div><div class="label">${label}</div></div>`;
  cards.innerHTML = [
    card(summary.total_posts, 'fixtures 總貼文數', ''),
    card(items.length, 'feed 實際可翻到的貼文數', items.length < summary.total_posts ? 'warn' : 'ok'),
    card(missing.length, '被多樣性上限永久擋掉', missing.length > 0 ? 'bad' : 'ok'),
    card(Object.keys(summary.creators).length, '不同創作者數'),
  ].join('');

  const feedRows = document.getElementById('feed-rows');
  feedRows.innerHTML = items.map(i => {
    const p = byId[i.post_id] || {};
    const src = (p.source || '').includes('mastodon') ? 'mastodon' : 'demo';
    const noInfo = p.tagged_products_count === 0 && p.detected_regions_count === 0;
    return `<tr class="${noInfo ? '' : ''}">
      <td>${i.rank}</td>
      <td>${i.post_id}</td>
      <td><span class="pill ${src}">${src}</span></td>
      <td>${p.creator_id || ''}</td>
      <td>${i.score.toFixed(3)}</td>
      <td class="${p.tagged_products_count ? 'badge-ok' : 'badge-bad'}">${p.tagged_products_count ?? '-'}</td>
      <td>${p.detected_regions_count ?? '-'}</td>
      <td>${(i.ranking_reason || []).join(', ')}</td>
    </tr>`;
  }).join('');

  const missingRows = document.getElementById('missing-rows');
  missingRows.innerHTML = missing.map(p => {
    const src = (p.source || '').includes('mastodon') ? 'mastodon' : 'demo';
    return `<tr class="missing-post">
      <td>${p.post_id}</td>
      <td><span class="pill ${src}">${src}</span></td>
      <td>${p.creator_id}</td>
      <td>${p.tagged_products_count}</td>
      <td>${p.detected_regions_count}</td>
    </tr>`;
  }).join('') || '<tr><td colspan="5">(無)</td></tr>';
}
main().catch(e => { document.getElementById('status').textContent = '載入失敗: ' + e; });
</script>
</body>
</html>"""
