# 梅竹黑客松｜AI 穿搭推薦與社交靈感平台開發 Spec

> 文件用途：明日分工、介面凍結與整合驗收的唯一依據  
> 團隊：5 人（A–E）｜正式賽程：24 小時  
> 原則：先完成可穩定展示的 P0，再做 P1；P2 不得阻塞 P0/P1。

---

## 0. 開工前必須確認（30 分鐘內完成）

- [ ] 賽規是否允許賽前寫程式、建立資料集、準備 prompts／starter code。
  - 若不允許：明天只做系統設計、Schema、測試案例、資料來源盤點與 Demo 腳本，不提交正式功能程式。
- [ ] 商品資料來源、授權與可展示範圍。
- [ ] 穿搭貼文／創作者圖片的來源、授權與可展示範圍；無授權時使用自製、公開授權或明確標示的 Demo 素材。
- [ ] 商品目標族群與類別：MVP 暫定 `top`、`bottom`、`shoes`，是否加入外套／配件由團隊決定。
- [ ] 預算代表「整套總預算」，幣別固定 TWD；未填預算時不做價格硬篩選。
- [ ] 是否承諾真實庫存與即時價格。若沒有官方 API，一律標示「展示資料／價格可能變動」，不可聲稱即時可購買。
- [ ] 前端採 React；若 2 小時內無法跑通，立即降級 Streamlit。
- [ ] LLM API、部署平台與 API key 由誰提供，確認所有人可在本機啟動。
- [ ] 指定一位 Demo 決策者（建議 E）；發生 scope 爭議時由此人裁決。
- [ ] 好友功能採「真實帳號＋權限」或「固定 Demo 帳號」。24 小時版本預設固定 Demo 帳號，不處理公開個資與聯絡人匯入。
- [ ] 行為追蹤僅記錄產品所需事件，UI 必須提供說明與 reset；不得暗中蒐集裝置識別、精確位置或其他非必要個資。

## 1. 產品定義

### 1.1 一句話目標

使用者可在「商城」與「穿搭版 IG」（產品正式命名可用「穿搭探索」）兩個模組間切換：商城用文字、圖片或圖文混合搜尋可購買商品與完整穿搭；穿搭版 IG 以類似 Instagram 放大鏡的瀑布流呈現創作者穿搭，支援追蹤、好友與 Dress Code 互動，並以停留、點按、按讚等事件改善個人化 Feed。兩個模組共用同一份商品庫、偏好模型與回饋資料；匿名彙整結果提供設計端 Dashboard。

### 1.2 雙模組定位

| 模組 | 主要任務 | 主要輸入 | 主要輸出 |
|---|---|---|---|
| 商城 `shop` | 找商品、組完整穿搭、控制預算與硬限制 | 文字、圖片、文字＋圖片、篩選器 | 商品／穿搭、總價、推薦理由、購買連結 |
| 穿搭版 IG／穿搭探索 `explore` | 發現靈感、追蹤創作者、和好友玩 Dress Code | Feed 行為、追蹤關係、好友與挑戰 | 個人化貼文 Feed、貼文內同款／相似商品 |

兩個模組不得建立兩套互相獨立的推薦資料。使用者在穿搭探索按讚「深色寬鬆日系」貼文後，商城排序可提高相同屬性的商品；使用者在商城明確排除米色後，穿搭 Feed 也應降低米色內容，但明確當次需求只影響 session，除非使用者選擇「記住偏好」。

### 1.3 核心 Demo 劇本

1. 在「商城」輸入：「週末想戶外走走，整套預算 3000 元，想要日系寬鬆，不要太貼身。」
2. 系統顯示解析結果：場合、預算、風格、版型、禁止條件與保留的模糊語意，再推薦 1–3 套 `上衣＋下身＋鞋子`；每套總價不超過預算。
3. 使用者可再上傳參考圖並輸入「顏色改深一點」；系統以相同硬篩選條件執行圖文混合搜尋，重新排序而非讓 LLM 自行選商品。
4. 切換到「穿搭探索」，瀑布流顯示創作者與好友的類似穿搭；使用者停留、點進貼文、按讚並追蹤一位創作者。
5. 點進貼文可查看被標記的服裝部位、對應商品與相似可購買商品；商品卡回到共用商城詳情。
6. 使用者進入固定 Demo Dress Code 挑戰「週末戶外日系」，查看好友投稿，並以一套現有商品穿搭加入挑戰。
7. 系統記錄事件，更新深色、寬鬆、日系與該創作者的偏好；刷新 Feed 與商城時可看到排序改變，並顯示 before／after 證據。
8. Dashboard 顯示行為與明確回饋的匿名統計，清楚標示來源、時間、樣本數及 `real/demo/synthetic`。

## 2. 優先級

| 層級 | 範圍 | 完成門檻 |
|---|---|---|
| P0 核心 | 商城原流程、商城／探索切換、固定貼文 Feed、貼文商品標記、文字搜尋、硬篩選、完整穿搭、按讚／點按／停留事件、session 偏好、Dashboard、部署 | 兩個模組端到端 Demo 連跑 3 次成功 |
| P1 加分 | 圖搜／圖文混合搜、FashionCLIP／文字 embedding、可量化 rerank、個人化 Feed、追蹤、固定 Demo 好友與 Dress Code 挑戰 | 不降低 P0 穩定度，且能展示 Feed／商城排序真的改變 |
| P2 選配 | 真實帳號與好友邀請、使用者發文、通知、外部趨勢、服裝知識 RAG、Polyvore／共現相容性、更完整 Dashboard | 有可信資料、權限控制與清楚限制 |

## 3. 系統架構與責任邊界

```text
React UI (A)
   │ HTTP only
   ▼
FastAPI / orchestration (E)
   ├── Intent parser (B): text → Intent JSON
   ├── Search (C): filters + text/image vectors → ranked products
   ├── Recommender (C): Intent + Profile + Catalog → ranked outfits
   ├── Feed ranker (C/D): posts + events + social graph → ranked feed
   ├── Profile/events (D): explicit + implicit events → UserProfile
   ├── Social/Dress Code (D): follows + demo friends + challenges
   └── Explanation (E): evidence → text; template fallback
            │
            ▼
       SQLite / JSON fixtures + optional vector index
```

### 責任規則

- A 不直接 import B/C/D，也不讀資料庫；只呼叫 E 的 HTTP API。
- E 負責 request validation、流程協調與錯誤碼，不修改 C 的排序邏輯。
- B 只解析語言，不選商品、不編造商品屬性。
- C 是商品合法性、硬性限制、商品／穿搭搜尋與候選排序的唯一負責模組。
- D 維護 session／長期偏好、行為事件、Feed 個人化訊號與社交關係，不直接組穿搭。
- 所有人共同遵守 `backend/schemas.py`；Schema 變更需先通知並由 E 合併。
- 商城與探索模組只能透過共用 Product、UserProfile 與 InteractionEvent 串接，不得各自維護互相矛盾的偏好欄位。

## 4. Repo 結構

```text
project/
├── frontend/                    # A
│   ├── src/
│   └── README.md
├── backend/
│   ├── main.py                  # E: FastAPI / orchestration
│   ├── schemas.py               # E: 唯一共用契約
│   ├── intent.py                # B
│   ├── search.py                # C：文字／圖片／混合搜尋
│   ├── recommender.py           # C
│   ├── feed.py                  # C/D：Feed 候選與排序
│   ├── feedback.py              # D：偏好更新
│   ├── events.py                # D：impression/dwell/click/like
│   ├── social.py                # D：follow/friend/dresscode
│   ├── explanation.py           # E
│   ├── db.py                    # E
│   └── config.py                # E
├── data/
│   ├── products.json            # C
│   ├── posts.json               # C/D：穿搭貼文與商品標記
│   ├── creators.json            # D：Demo 創作者
│   ├── social_graph.json         # D：Demo follow/friend 關係
│   ├── dresscode_challenges.json # D：固定 Demo 挑戰
│   ├── trend_seed.json          # D；需標來源／日期／是否合成
│   └── fixtures/                # E：前後端共用 Mock
├── prompts/                     # B；system prompt / few-shot / version
├── tests/
│   ├── test_intent.py           # B
│   ├── test_recommender.py      # C
│   ├── test_search.py            # C
│   ├── test_feed.py              # C/D
│   ├── test_feedback.py         # D
│   └── test_api.py              # E
├── scripts/                     # 資料預處理、embedding 建立
├── .env.example
├── requirements.txt
└── README.md
```

## 5. 共用資料契約（開工後 1 小時內凍結）

所有 API 與 Python 函式都使用相同欄位。允許加 optional 欄位，但不得在未通知下改名、改型別或刪欄位。

### 5.1 Intent

```json
{
  "session_id": "demo-001",
  "occasion": ["outdoor", "casual"],
  "budget_total": 3000,
  "currency": "TWD",
  "required_categories": ["top", "bottom", "shoes"],
  "preferred": {
    "styles": ["japanese"],
    "colors": ["black", "charcoal"],
    "fits": ["relaxed"],
    "materials": []
  },
  "excluded": {
    "colors": ["beige"],
    "fits": ["slim"],
    "materials": []
  },
  "hard_constraints": ["budget_total", "excluded.colors", "excluded.fits"],
  "soft_constraints": ["preferred.styles", "preferred.colors"],
  "unknown_fields": ["size"],
  "needs_clarification": false,
  "clarifying_question": null,
  "semantic_query": "日系、清爽、適合戶外、不太正式",
  "source_text": "週末想戶外走走……"
}
```

規則：

- 明確的「不要／不能／最多」才進 `excluded` 或 `hard_constraints`。
- LLM 推測的隱含需求只能放 `soft_constraints`，不可當硬條件。
- 無法確定就填空陣列或 `null`，不得強行補齊。
- 可確定且可比對的欄位進 hard／soft constraints；難以正規化但有檢索價值的語意保留在 `semantic_query`，不得因沒有對應 enum 而丟失。
- 若需求矛盾且會導致無解，`needs_clarification=true`，先追問再推薦。
- 多輪更新採 patch semantics：新訊息只修改被提及欄位，其餘沿用 session intent。

### 5.2 Product

```json
{
  "product_id": "p-top-001",
  "name": "寬鬆牛津襯衫",
  "category": "top",
  "price": 990,
  "currency": "TWD",
  "colors": ["black"],
  "styles": ["japanese", "minimal"],
  "fit": "relaxed",
  "materials": ["cotton"],
  "sizes": ["S", "M", "L"],
  "image_url": "https://...",
  "product_url": "https://...",
  "source": "brand_or_dataset",
  "source_checked_at": "2026-09-18",
  "availability": "unknown",
  "search_text": "寬鬆牛津襯衫；黑色；日系；極簡；休閒；棉；非貼身",
  "image_embedding_id": null,
  "text_embedding_id": null
}
```

硬規則：

- `product_id` 唯一且全程不變。
- 缺少的屬性填 `null`／空陣列，不得由 LLM 補寫成事實。
- 遠端圖片失效時，前端顯示 placeholder，不讓整頁壞掉。
- 若沒有即時商品 API，`availability` 必須是 `unknown` 或 `demo_only`。

### 5.3 UserProfile 與 FeedbackEvent

```json
{
  "user_id": "anonymous-demo",
  "preference_weights": {
    "color:black": 0.4,
    "color:beige": -1.0,
    "fit:relaxed": 0.6,
    "style:japanese": 0.5
  },
  "creator_affinity": {
    "creator-001": 0.3
  },
  "followed_creator_ids": ["creator-001"],
  "trend_affinity": 0.2,
  "updated_at": "2026-09-18T12:00:00Z"
}
```

```json
{
  "event_id": "evt-view-001",
  "session_id": "demo-001",
  "user_id": "anonymous-demo",
  "event_type": "dwell",
  "target_type": "post",
  "target_id": "post-001",
  "dwell_ms": 8200,
  "surface": "explore_feed",
  "position": 4,
  "created_at": "2026-09-18T12:00:00Z"
}
```

```json
{
  "event_id": "evt-001",
  "session_id": "demo-001",
  "user_id": "anonymous-demo",
  "event_type": "dislike",
  "target_type": "product",
  "target_id": "p-top-001",
  "explicit_patch": {
    "excluded.colors": ["beige"],
    "preferred.colors": ["black"]
  },
  "created_at": "2026-09-18T12:00:00Z"
}
```

- P0 僅做匿名 ID，不收集姓名、Email 等個資。
- `current_session` 與 `persistent_profile` 必須分開；Demo 預設只更新 session，除非 UI 明確提供「記住偏好」。
- 使用者可 reset session/profile，避免錯誤偏好永久累積。
- `impression`、短暫滑過與網路重送不可直接視為喜歡；只有達門檻的停留、點進、按讚、收藏、追蹤、商品點擊等事件才進偏好更新。
- 同一事件以 `event_id` 去重；伺服器計算停留區間並設定上限，避免背景分頁或重複上報灌高權重。
- 社交關係只影響內容候選與社交訊號，不自動推論使用者喜歡好友的所有風格。

### 5.4 RecommendationResponse

```json
{
  "session_id": "demo-001",
  "intent": {},
  "outfits": [
    {
      "outfit_id": "outfit-001",
      "items": [],
      "total_price": 2880,
      "score": 0.82,
      "score_breakdown": {
        "relevance": 0.86,
        "preference": 0.75,
        "compatibility": 0.80,
        "trend": 0.20
      },
      "matched_constraints": ["budget_total", "style:japanese"],
      "warnings": ["availability_unknown"],
      "reason": "符合日系、寬鬆與整套預算限制。"
    }
  ],
  "fallback_used": false,
  "message": null
}
```

### 5.5 SearchRequest／SearchResponse

```json
{
  "session_id": "demo-001",
  "query_text": "深色日系，不要太正式",
  "query_image": null,
  "mode": "text",
  "image_weight": 0.5,
  "filters": {
    "categories": ["top"],
    "price_max": 1500,
    "available_only": true,
    "excluded_colors": ["beige"]
  },
  "limit": 30
}
```

```json
{
  "session_id": "demo-001",
  "mode": "mixed",
  "products": [
    {
      "product_id": "p-top-001",
      "score": 0.84,
      "score_breakdown": {
        "image_rank": 2,
        "text_rank": 5,
        "fusion": 0.74,
        "preference": 0.10
      },
      "matched_filters": ["category:top", "price_max:1500"],
      "warnings": []
    }
  ],
  "retrieval": {
    "prefilter_count": 86,
    "image_candidates": 30,
    "text_candidates": 30,
    "fusion_method": "rrf"
  }
}
```

`mode` 僅允許 `text`、`image`、`mixed`：

- `text`：使用 `semantic_query`／`query_text` 查商品文字向量。
- `image`：使用參考圖片查 FashionCLIP 商品圖片向量。
- `mixed`：文字與圖片分別檢索，在同一批 metadata filters 下取候選聯集，再做 rank fusion；不同模型的原始向量不得直接相加。
- `filters` 是 deterministic constraints；向量資料庫可作 payload filter，若不用向量 DB，則由 SQL／Pandas 先取合法 `product_id` 再計算相似度。

### 5.6 穿搭貼文與社交資料

```json
{
  "post_id": "post-001",
  "creator_id": "creator-001",
  "image_url": "https://...",
  "caption": "週末戶外日系穿搭",
  "styles": ["japanese", "outdoor", "relaxed"],
  "colors": ["black", "charcoal"],
  "occasion": ["casual", "outdoor"],
  "tagged_products": [
    {
      "product_id": "p-top-001",
      "label": "上衣",
      "bbox": [0.20, 0.12, 0.72, 0.55],
      "match_type": "exact"
    }
  ],
  "source": "licensed_demo_content",
  "source_checked_at": "2026-09-18",
  "is_demo": true,
  "created_at": "2026-09-18T10:00:00Z"
}
```

Feed 回應最少包含：

```json
{
  "user_id": "anonymous-demo",
  "items": [
    {
      "post_id": "post-001",
      "rank": 1,
      "ranking_reason": ["style:japanese", "followed_creator"],
      "score_breakdown": {
        "preference": 0.72,
        "social": 0.30,
        "exploration": 0.00
      }
    }
  ],
  "next_cursor": "cursor-002",
  "profile_version": 3
}
```

- `match_type` 為 `exact` 時才可稱「同款」；由視覺搜尋推得者一律標 `similar`。
- 貼文詳情必須顯示創作者、內容來源與標記商品；商品失效時仍保留貼文，但顯示「商品已失效」及相似替代品。
- P0 的創作者、好友與追蹤使用固定 Demo fixtures；真實好友邀請、封鎖、隱私與通知屬 P2。

```json
{
  "challenge_id": "dc-001",
  "title": "週末戶外日系",
  "host_user_id": "demo-user-a",
  "participant_user_ids": ["demo-user-a", "demo-user-b"],
  "required_tags": ["outdoor", "japanese"],
  "starts_at": "2026-09-18T10:00:00Z",
  "ends_at": "2026-09-19T10:00:00Z",
  "visibility": "friends",
  "is_demo": true
}
```

## 6. API Spec

| Method | Endpoint | Request | Response | Owner |
|---|---|---|---|---|
| `GET` | `/health` | 無 | service / model / DB 狀態 | E |
| `POST` | `/api/v1/recommend` | `session_id`, `text`, optional `image`, optional filters | `RecommendationResponse` | E 串 B/C/D |
| `POST` | `/api/v1/search` | `SearchRequest` | ranked products + score evidence | E 串 B/C |
| `GET` | `/api/v1/feed` | `user_id`, cursor, optional surface/filter | ranked posts + next cursor | E 串 C/D |
| `GET` | `/api/v1/posts/{post_id}` | path | post、creator、tagged products、similar products | C/D/E |
| `POST` | `/api/v1/events/batch` | `InteractionEvent[]` | accepted／duplicate count | D/E |
| `POST` | `/api/v1/feedback` | `FeedbackEvent` 或自然語言 feedback | 更新後 profile + recommendation | E 串 B/C/D |
| `POST` | `/api/v1/social/follow` | user_id, creator_id, action | follow state + profile summary | D/E |
| `GET` | `/api/v1/friends` | user_id | Demo friend list | D/E |
| `GET` | `/api/v1/dresscodes` | user_id | visible challenges | D/E |
| `POST` | `/api/v1/dresscodes/{id}/submit` | user_id, outfit_id/post_id | submission result | C/D/E |
| `GET` | `/api/v1/profile/{user_id}` | path | `UserProfile` | D/E |
| `POST` | `/api/v1/session/{id}/reset` | 無 | reset result | D/E |
| `GET` | `/api/v1/insights` | optional date range | 統計、樣本數、來源與時間 | D/E |

### 統一錯誤格式

```json
{
  "error": {
    "code": "NO_MATCHING_PRODUCTS",
    "message": "目前沒有同時符合預算與排除條件的完整穿搭。",
    "retryable": false,
    "details": {"failed_constraints": ["budget_total"]}
  }
}
```

至少處理：`INVALID_INPUT`、`LLM_TIMEOUT`、`NO_MATCHING_PRODUCTS`、`DATA_UNAVAILABLE`、`INTERNAL_ERROR`。

## 7. 雙模組前端與互動規格

### 7.1 全域導覽

- 頂部／底部提供清楚的二選一切換：`商城`／`穿搭版 IG`（對外正式名稱可改 `穿搭探索`）；切換時保留登入狀態與 UserProfile，但不把商城當次 query 自動套成探索硬限制。
- 商城保留原本搜尋框、圖片上傳、篩選器、商品卡與完整穿搭結果。
- 穿搭探索採類似 Instagram 放大鏡的 responsive masonry/grid；手機預設 3 欄縮圖，桌面自適應 4–6 欄。
- 所有圖片需有 loading skeleton、失效 placeholder 與來源標示；不得直接複製 Instagram 商標、介面資產或未授權貼文。

### 7.2 穿搭探索 Feed

- Feed 卡片縮圖顯示穿搭圖；點入後才顯示創作者、caption、風格標籤、按讚／收藏／追蹤與服裝商品標記。
- Feed 必須混入三種候選：偏好相符、已追蹤／好友、探索／多樣性；不可只重複最高分風格。
- 首次使用沒有 profile 時使用編輯精選＋多樣化熱門貼文；完成 3–5 個互動後才提高個人化比重。
- 每次 Feed 回應回傳 `ranking_reason` 的內部 evidence，但前端只需以簡短文字顯示「因為你喜歡日系／來自已追蹤創作者」；不得捏造原因。

### 7.3 貼文詳情與商品資訊

- 點擊圖片上的標記點，顯示商品名稱、價格、庫存警告、來源及「查看商品」。
- `exact` 商品可直接連結商品頁；`similar` 必須標示「相似商品」，不可冒充網紅實穿同款。
- 若貼文沒有人工標記商品，才使用 FashionCLIP 以裁切區域／整張圖片檢索相似商品，結果仍受庫存、價格與類別等 filters 約束。
- 商品點擊事件回流同一個 UserProfile，讓探索行為可改善商城排序。

### 7.4 追蹤、好友與 Dress Code

- P1 追蹤僅需 follow／unfollow 創作者並影響 Feed；需顯示追蹤後排序的可觀察變化。
- P1 好友採固定 Demo graph，僅展示朋友清單、朋友投稿與一個 Dress Code 挑戰；不實作聯絡人匯入、私訊、推播或真實邀請。
- Dress Code 投稿必須引用既有 outfit／post，不在 24 小時內開發完整貼文編輯器。挑戰頁顯示主題、期限、參與者與投稿。
- 若升級真實帳號，必須先完成驗證、好友邀請同意、封鎖／移除、可見範圍與資料刪除；未完成前不得聲稱是真實社交功能。

## 8. 模組介面（避免最後接不起來）

```python
# B
parse_intent(text: str, previous_intent: Intent | None) -> Intent
parse_feedback(text: str, current_intent: Intent) -> IntentPatch

# C
search_products(request: SearchRequest, catalog: list[Product]) -> SearchResponse
recommend(intent: Intent, profile: UserProfile, catalog: list[Product]) -> list[Outfit]
rank_feed(user_id: str, posts: list[Post], profile: UserProfile) -> FeedResponse

# D
record_feedback(event: FeedbackEvent) -> UserProfile
record_interactions(events: list[InteractionEvent]) -> EventBatchResult
get_profile(user_id: str) -> UserProfile
get_insights() -> InsightsResponse
update_follow(user_id: str, creator_id: str, action: str) -> FollowState
submit_dresscode(challenge_id: str, user_id: str, target_id: str) -> Submission

# E
build_explanation(outfit: Outfit, intent: Intent) -> str
```

每個 owner 必須同時提供：

1. 真實函式實作。
2. 一份固定 fixture。
3. 最少 3 個單元測試。
4. 失敗時的明確 exception／錯誤結果，不可回傳不定型 dict。

## 9. 五人分工與 Definition of Done

### A｜Frontend / UX

**負責**

- 商城／穿搭探索二選一切換與各自 routing；共用登入／匿名 session 與商品詳情元件。
- 文字輸入、解析標籤、商品卡、整套總價、推薦理由。
- 探索瀑布流、貼文詳情、服裝標記點、創作者頁、追蹤、Demo 好友與 Dress Code 頁。
- 正確上報 impression、visible dwell、post open、like、save、follow、product click；分頁不在前景時停止 dwell 計時。
- 喜歡／不喜歡、自然語言回饋、重新推薦、reset。
- 消費者頁與設計端 Dashboard。
- loading、empty、API error、圖片失效狀態。
- 先接 `data/fixtures/*.json`，不得等待後端。

**不負責**：解析語意、計分、直接讀 DB。

**最晚交付**

- T+2h：商城與探索 Mock UI 均可跑，貼文可點進並看到假商品標記。
- T+6h：接正式 `/recommend`、`/search`、`/feed`、`/events/batch`、`/feedback`、`/insights`。

**DoD**

- 390px 與桌面寬度皆可操作。
- 預算、商品來源、availability warning 可見。
- API 失敗可恢復，不白屏。
- Demo 主流程 2 分鐘內可完成。
- 模式切換不丟失 session；Feed 可使用 cursor 載入下一頁且不重複同一 post。

**Fallback**：React 整合連續卡 1 小時就切 Streamlit；圖表用簡單 bar chart，不做複雜互動。

### B｜LLM Intent / Feedback Parsing

**負責**

- Structured Outputs／JSON Schema、system prompt、5–10 組 few-shot。
- 正規化顏色、價格、風格、版型與場合。
- 區分 hard／soft／excluded／unknown；處理否定、矛盾與多輪 patch。
- 保留無法可靠正規化的原始偏好為 `semantic_query`，供文字向量搜尋；不可把所有語意硬塞成 enum。
- 將搜尋文字解析為 deterministic filters＋semantic query；圖片本身不交給 B 推測價格、庫存或尺寸。
- 解析自然語言回饋。
- 準備固定測試集與 prompt version。

**不負責**：訓練 LLM、搜尋商品、決定推薦排名。

**最晚交付**

- T+2h：`parse_intent()` 對 10 個案例輸出合法 Intent。
- T+5h：`parse_feedback()` 與多輪更新可用。

**DoD**

- Schema validity = 100%。
- 測試集至少含：正常、否定、模糊、矛盾、超低預算、修改偏好各 2 題。
- 明確欄位 exact match ≥ 80%；所有錯誤案例保留在測試報告。
- API timeout（建議 8 秒）時回 deterministic fallback，不阻塞 Demo。

**Fallback**：關鍵字／regex 解析預算、顏色與否定詞；理由使用模板。

### C｜Catalog / Recommendation

**負責**

- 建立並驗證商品庫；每類 P0 建議至少 15–30 件，屬性完整。
- 先硬篩選，再計算 soft score；產生完整穿搭並檢查整套總價。
- 建立 `Post → tagged_products → Product` 關係與 validator；每篇 P0 貼文至少有 1 件人工對應商品或明確標示相似商品。
- 實作文字搜、圖片搜與圖文混合搜；同一組 deterministic filters 必須套用在所有 retrieval branch。
- 與 D 定義 Feed 候選與排序介面；C 提供內容／商品相似度，D 提供使用者／社交特徵。
- 傳回 score breakdown、matched constraints 與 explanation evidence。
- P1 才加入 FashionCLIP 圖片向量、E5 類文字向量、混合 rank fusion 與 rerank。

**排序基線**

```text
先移除違反 hard constraints 的商品
S_item = 0.60 * relevance + 0.35 * preference + 0.05 * trend
S_outfit = 0.75 * mean(S_item) + 0.25 * compatibility
```

- 所有 component 先正規化到 `[0, 1]`。
- 權重集中定義於 config，禁止散落在程式內。
- trend 永遠不能推翻 hard constraints；沒有可信趨勢資料時設為 0。
- 避免組合爆炸：每類先取 top 10，再用 beam search／最多檢查 1000 組。

**最晚交付**

- T+2h：`products.json`、`posts.json` + validator + 至少 1 組可用 outfit／post fixture。
- T+5h：規則式推薦與無解處理。
- T+8h：貼文詳情可取得 tagged／similar products。
- T+10h：若 P0 穩定，再加入圖片／文字 embedding 與 mixed search。

**DoD**

- hard constraint violation rate = 0%。
- 測試 20 組 query；回傳 latency（不含 LLM）目標 < 1 秒。
- 每套必含 required categories，且 `total_price` 計算正確。
- 無解時回報失敗條件，不偷偷放寬使用者明確限制。
- 混合搜尋不得直接相加不同模型向量；必須用候選聯集＋score normalization／rank fusion。

**Fallback**：純 metadata filter + weighted rules；不用向量 DB，embedding 可存 `.npy`／記憶體。

### D｜Feedback / Personalization / Insights

**負責**

- 定義 FeedbackEvent、UserProfile；記錄 before/after。
- 定義 InteractionEvent、Creator、Follow、Friend、DressCodeChallenge 與 submission fixture。
- 用確定性規則更新權重，區分 session 與 persistent profile。
- 實作事件去重、dwell 門檻／上限、前景頁面檢查與 implicit signal 降權。
- 與 C 共同完成 Feed ranker：偏好、follow/friend、內容品質、新鮮度與多樣性；避免單一風格洗版。
- P1 實作 follow/unfollow、固定 Demo 好友與 Dress Code submission。
- 提供 `/insights` 所需匿名統計、樣本數、日期與資料來源。
- 建立回饋前後評估與 reset。

**P0 更新規則範例**

```text
like(item):    該商品屬性 +0.2，上限 +1.0
dislike(item): 該商品屬性 -0.3，下限 -1.0
explicit "不要 X": X = -1.0，並加入 session hard exclusion
explicit "偏好 X": X +0.4
post open:     貼文屬性 +0.03
dwell >= 8s:   貼文屬性 +0.05；單貼文單 session 最多一次
like(post):    貼文屬性 +0.15
save(post):    貼文屬性 +0.20
follow:        creator affinity +0.30；風格屬性只加 +0.05
product click: 商品屬性 +0.10
```

**最晚交付**

- T+2h：Schema + in-memory/SQLite 儲存 + fixture。
- T+5h：回饋更新後可使指定屬性排名改變。
- T+7h：Feed 會依事件改變，且仍保有至少 20% 探索／多樣性內容。
- T+8h：insights aggregation、Demo follow／friend／dresscode 完成。

**DoD**

- 同一 feedback 重送時不重複加權（`event_id` idempotent）。
- 明確排除商品移除率 = 100%。
- 至少用 5 個情境展示 before/after；記錄目標屬性的平均順位變化與 Top-K 命中率。
- Dashboard 資料必含 `sample_size`、`time_range`、`source_type`（real/demo/synthetic）。
- 短於 2 秒 dwell、背景分頁與重複 event 不更新偏好；單一 implicit event 不得變成 hard exclusion。

**Fallback**：只做 session memory + 固定種子 demo events；UI 明確標「Demo data」。

### E｜Backend / Integration / Delivery

**負責**

- Repo、`schemas.py`、FastAPI、CORS、DB、環境變數與部署。
- 在 T+1h 發布 API 契約與 Mock endpoints。
- 串商城：B → deterministic filters → C search/recommend → D/Profile → Explanation → A。
- 串探索：D/Profile/Social → C/D feed → Post/Product mapping → A；事件由 A → E → D 回流。
- 統一 timeout、error format、logging 與健康檢查。
- PR 合併、端到端測試、README、部署、Demo 錄影與提交確認。

**最晚交付**

- T+1h：Repo／branch／Schema／fixtures。
- T+2h：前端可打 Mock `/recommend`、`/feed`、`/posts/{id}`。
- T+6h：第一版完整串接。
- T+10h：P0 部署且可重複 Demo。

**DoD**

- `curl /health` 成功，啟動命令寫入 README。
- API key 只在環境變數；`.env`、資料庫、cache 不進 Git。
- LLM timeout、資料空缺與 C 無解都有可展示回應。
- 在乾淨環境重建並完成 3 次 smoke test。

**Fallback**：部署失敗時準備本機錄影與本機雙服務啟動腳本；LLM explanation 改模板。

## 10. 搜尋、Feed 與偏好演算法

### 10.1 共用搜尋順序

```text
文字／圖片／UI filters
    │
    ├── B：文字 → hard filters + soft fields + semantic_query
    │
    ▼
deterministic pre-filter
庫存、類別、價格、排除色／版型、尺寸等
    │
    ▼
vector retrieval（僅在合法候選中）
    ├── text：query text → E5；比對 product.text vector
    ├── image：query image → FashionCLIP；比對 product.image vector
    └── mixed：兩路各自取 Top-K → 候選聯集 → rank fusion
    │
    ▼
optional rerank Top 20–50
    │
    ▼
profile／trend soft score → 商品排序 → 完整穿搭組合與整套預算檢查
```

- Vector database 不會自行猜應排除哪些商品；每個商品必須同時存 metadata／payload，由 SearchRequest 的 filters 限制搜尋範圍。
- 若使用 Qdrant 類工具，一個 Product point 可存 `fashionclip_image`、`text_e5` 等 named vectors 與 price／stock／category payload。
- 若商品少於約 3,000 件，P0 直接用 SQL／Pandas 取得合法 IDs，再以 NumPy 對相應向量計算 cosine similarity；不為展示而強制導入 vector DB。
- metadata 缺值時不得假裝符合。明確 hard constraint 所需欄位若為 unknown，預設排除或回 warning，由 config 決定並在 UI 說明。

### 10.2 文字、圖片與混合搜尋

**文字搜尋**

- 可判定的預算、類別、排除色等走 deterministic filters。
- 使用者原始文字與 `semantic_query` 轉成文字向量；商品的名稱、正規化屬性與描述組成 `search_text` 後預先建向量。
- Embedding 只處理「日系但不要太文青」等模糊相關性，不負責保證庫存、價格或排除條件。

**圖片搜尋**

- 使用 FashionCLIP 將參考圖片與商品圖片放入同一向量空間。
- 圖片本身沒有預算／庫存語意；使用者需透過 UI filters 或文字補充 deterministic constraints。
- 若圖片含多件服裝，P1 先讓使用者點選／裁切目標區域；不要在 24 小時內承諾完整服裝偵測與精準同款辨識。

**圖文混合搜尋**

- FashionCLIP 圖向量與 E5 文字向量維度與語意空間不同，禁止直接相加。
- 兩路使用相同 filters 各取 Top-K，再將候選取聯集。P1 優先採 Reciprocal Rank Fusion，避免不同模型分數尺度不一致：

```text
RRF(product) = w_img / (k + rank_img) + w_text / (k + rank_text)
```

- `k` 可先固定 60；預設 `w_img = w_text = 0.5`。若 UI 提供「更像圖片／更符合描述」滑桿，才讓使用者調權重。
- 若要用 weighted score，必須先在各 retrieval branch 內校正／正規化，並以固定測試集確認權重；不得直接相加原始 cosine scores。

### 10.3 商品、完整穿搭與貼文商品映射

```text
S_product = 0.55 * search_relevance
          + 0.30 * profile_preference
          + 0.10 * quality_or_popularity
          + 0.05 * trend

S_outfit = 0.70 * mean(S_product)
         + 0.30 * compatibility
```

- hard constraints 永遠先於分數，不能用高相似度或高人氣抵銷。
- 貼文人工標記的 `exact` 商品優先；失效或未標記時，以貼文／服裝裁切圖做圖片搜尋並回傳 `similar` 商品。
- 先取得各類 Top 10，再做 outfit composition；最後再次驗證 required categories、整套總價、重複商品與庫存。

### 10.4 Feed 候選與排序

Feed 不是單純將商品搜尋結果換成貼文。候選來源至少分成：

1. 與 UserProfile 風格／顏色／場合相符的貼文。
2. 已追蹤創作者與 Demo 好友貼文。
3. 編輯精選、近期內容與少量探索內容。
4. 活躍 Dress Code 挑戰投稿。

```text
S_feed = 0.40 * preference_match
       + 0.20 * social_affinity
       + 0.15 * content_quality
       + 0.10 * recency
       + 0.05 * trend
       + 0.10 * exploration_bonus
```

- 排序後加 diversity pass：相鄰內容避免同一創作者、同一主色或同一風格連續出現；保留至少 20% 非最高偏好內容，避免 filter bubble。
- explicit feedback 權重高於 implicit event；單次 dwell／click 只能小幅更新 soft preference，不能建立 hard exclusion。
- Demo 必須保存 `before_rank`、`after_rank`、觸發事件與主要 score component，才能量化證明 Feed 確實變好。

### 10.5 事件處理與資料最小化

- `impression`：卡片至少 50% 可見並持續 1 秒才上報；只用於曝光與 CTR 分母，不直接增加偏好。
- `dwell`：貼文詳情前景停留 2–8 秒為弱訊號，8 秒以上為較強訊號；上限 30 秒，避免背景掛頁。
- `like/save/follow/dislike`：明確行為，權重高於 dwell；取消動作需回復相應權重，不能再加一次反向權重造成漂移。
- 事件採 batch 上報、`event_id` 去重；Demo 使用匿名 ID，並提供「重設偏好」與「停止個人化／不記錄長期偏好」。

## 11. 測試與驗收

### 固定 E2E 案例

| Case | 輸入 | 預期 |
|---|---|---|
| Happy path | 日系、寬鬆、預算 3000 | 完整穿搭且總價 ≤ 3000 |
| 明確排除 | 不要米色 | 回傳商品無米色 |
| 多輪修改 | 改成黑色、預算提高到 4000 | 只更新指定欄位 |
| 圖搜 | 上傳參考穿搭圖＋類別 top | 回傳視覺相似且類別正確商品 |
| 圖文混合 | 圖片＋「改深色、1500 以下」 | 視覺相近，且所有商品符合深色與價格硬限制 |
| 搜尋前篩選 | 庫存 true、排除 beige | vector candidates／最終結果皆不含違規商品 |
| 探索貼文 | 點入 Feed 貼文 | 顯示 creator、tagged products 與 exact/similar 標示 |
| 行為個人化 | 連續按讚深色日系貼文 | 對應內容 after rank 上升，但仍保留探索內容 |
| 短暫滑過 | dwell < 2 秒 | 不更新偏好 |
| 背景停留 | 分頁切到背景 30 秒 | 不計入有效 dwell |
| 追蹤 | follow creator-001 後刷新 | 該 creator 候選提高，但不壟斷 Feed |
| Dress Code | Demo friend 加入 dc-001 | 朋友投稿可見，且商品連結可開啟 |
| 矛盾需求 | 全黑但不要深色 | 追問，不直接猜 |
| 無解 | 整套 200 元 | `NO_MATCHING_PRODUCTS` + 原因 |
| LLM failure | timeout／invalid JSON | fallback 生效，頁面不壞 |
| 圖片失效 | 無效 image URL | placeholder 顯示 |
| 重複回饋 | 同 event_id 傳兩次 | 只更新一次 |

### 最低指標

- Intent Schema validity：100%。
- 明確硬限制符合率：100%。
- 完整穿搭類別完整率：100%。
- Search hard-filter violation rate：0%。
- 貼文商品映射可解析率：100%；`exact`／`similar` 標示正確率 100%。
- Feedback 明確排除移除率：100%。
- InteractionEvent 去重率：100%；無效 dwell 不更新偏好。
- Feed diversity：Top 10 同一創作者不超過 3 篇，且至少 2 種主要風格（可依資料量調整並寫入 config）。
- 個人化測試：至少 5 個固定情境中，目標風格／創作者平均順位有可重現改善。
- 推薦 API P0 latency：目標 p95 < 10 秒（含一次 LLM）；fallback < 2 秒。
- Demo 主流程成功率：連續 3 次成功。

## 12. LLM、FashionCLIP、RAG 的正確定位

- **LLM 不需要訓練。** P0 使用 system prompt + Structured Outputs + few-shot + 測試集；時間充裕才考慮其他方法。
- **LLM input** 是使用者文字、舊 Intent 與允許的 enum；**output** 是 Intent／IntentPatch，不是商品清單。
- **商品推薦由 C 決定。** LLM 最多根據已選商品的 evidence 產生理由，不得自行新增商品。
- **FashionCLIP** 主要用於參考圖片／貼文圖片與商品圖片的視覺相似度；**E5 類文字 embedding** 用於中文需求與商品 `search_text`。兩者分開檢索後做 rank fusion，不能直接相加原始向量。
- **商品 RAG** 若加入，只是從商品庫 retrieval；商品欄位仍以 catalog 為準。
- **服裝知識 RAG** 是 P2，用於解釋風格／場合，不得污染商品事實。
- P0 不一定需要 vector DB；小型商品庫可用 numpy cosine similarity，降低整合風險。
- **向量搜尋不取代 Intent JSON。** JSON 提供 deterministic filters、對話狀態與可解釋限制；`semantic_query` 才交給 embedding 處理模糊語意。
- **Feed 個人化不是 LLM 工作。** P0/P1 使用可重現的事件權重、候選來源與排序公式；LLM 不根據行為紀錄自由生成貼文或偏好。

## 13. 主要風險與處理

| 風險 | 嚴重度 | 早期訊號 | 處理／降級 |
|---|---:|---|---|
| 商品資料太少或欄位不完整 | 高 | 無法組三類穿搭 | 優先補 catalog；P1 全停 |
| 貼文圖片無授權或來源不明 | 高 | 不知能否公開展示 | 使用自製／公開授權／主辦方素材；保存 attribution |
| 貼文找不到真實商品 | 高 | 商品連結大量失效 | 人工 exact mapping 優先；其餘明確標 similar |
| 資料授權或連結不明 | 高 | 不知能否展示／購買 | 改合法公開資料或明確 demo-only |
| 前後端 Schema 漂移 | 高 | 同欄位多種名稱 | E 凍結 schema + fixtures + PR gate |
| LLM JSON 不穩／延遲 | 高 | parse error、>8s | Structured Outputs、timeout、fallback |
| 組穿搭組合爆炸 | 中 | C latency 快速上升 | 每類 top 10 + beam/cap |
| 偏好與當次需求互相污染 | 高 | reset 後仍殘留 | 分 session/profile，提供 reset |
| implicit feedback 誤判 | 高 | 滑過一次就洗版 | 弱權重、門檻、上限、時間衰減、多樣性與 reset |
| 行為追蹤涉及隱私 | 高 | 無說明即記錄或收集多餘欄位 | 匿名 ID、資料最小化、UI 說明、停止個人化與刪除 |
| Feed filter bubble | 中 | Top 10 都同風格／創作者 | 20% exploration + diversity pass + per-creator cap |
| 好友權限不完整 | 高 | 可看到非好友內容或冒用帳號 | P1 固定 Demo graph；真實社交延至完成 auth/ACL 後 |
| 圖文分數不可直接比較 | 中 | 混合結果被單一路徑壟斷 | RRF 或 branch normalization；固定測試集調權重 |
| 趨勢資料缺乏證據 | 高 | 無日期、來源、樣本數 | trend=0 或標 synthetic；不做強結論 |
| Dashboard 過度宣稱 | 高 | 幾筆 demo 被稱市場洞察 | 顯示 sample size/source/time range |
| 遠端圖片／商品頁失效 | 中 | UI broken image | placeholder + link validator |
| 部署/CORS 最後才處理 | 高 | 本機可用、線上失敗 | T+6h 前部署第一版；保留本機 Demo |
| E 成為單點瓶頸 | 高 | PR 全卡 E | fixtures 先行；review 可由第二人處理 |
| 明天預作違反賽規 | 極高 | 規章限制賽前 coding | 先確認，只準備允許的設計與資料 |

## 14. 目前仍需團隊拍板的 TBD

- [ ] 明天允許做到「設計」還是「可執行程式」？
- [ ] 商品資料來源與授權是什麼？預計每類多少件？
- [ ] 穿搭貼文與創作者素材從哪裡取得？每篇是否可展示、是否有人工作品到商品的 exact mapping？
- [ ] 目標使用者／性別／尺寸要不要納入？若納入，尺寸是 hard constraint 嗎？
- [ ] P0 前端 React 或 Streamlit？切換的明確 deadline？
- [ ] 使用哪個 LLM API／model？Structured Outputs 是否可用？
- [ ] 圖搜是整張穿搭、單件商品，還是允許使用者裁切服裝區域？P1 建議要求裁切／點選目標。
- [ ] 圖文混合搜尋預設權重與 Top-K 各是多少？先用 RRF 還是 calibrated weighted score？
- [ ] 使用 in-memory vectors／FAISS／Qdrant？商品少於約 3,000 件預設不用獨立 vector DB。
- [ ] 穿搭探索 P0 要做到固定 Feed，還是 P1 才啟用個人化 Feed？建議 P0 固定內容＋事件記錄，P1 再改排序。
- [ ] 追蹤、好友與 Dress Code 使用固定 Demo 帳號還是真實登入？24 小時版本建議固定 Demo graph。
- [ ] 哪些 InteractionEvent 會持久化？UI 如何說明個人化、reset 與停止長期記錄？
- [ ] Dashboard 面向誰，最核心的 3 個指標是什麼？
- [ ] 外部趨勢資料的來源、更新日期與使用許可？若沒有，P0 trend score 固定為 0。
- [ ] 部署平台與最終提交截止時間？
- [ ] A–E 對應到哪五位成員、誰是第二整合者？
