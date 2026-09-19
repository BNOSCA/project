# Outfit demo backend (E / P0)

依照 [draft2.md](draft2.md) 的 E 職責建立 FastAPI 入口、共用 Pydantic 契約、SQLite session 資料、固定展示 fixtures 與可替換 B/C/D 的整合點。預設 `BACKEND_MODE=mock`，並載入 GU／UNIQLO 官方品牌商品快照；這些是展示用快照，不代表即時價格或庫存。`/health` 會標示 fixture/live 狀態。

## 本機啟動

需要 Python 3.11+。在 repo 根目錄執行：

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

預設 `APP_DATA_DIR=./data/catalog/combined`，只含官方品牌商品快照，並保留官方 HTTPS 圖片與商品頁。若要回到原本 6 筆合成 fixture，可設定 `APP_DATA_DIR=./data/fixtures`。

另開終端：

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/api/v1/recommend \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-001","text":"週末想戶外走走，整套預算 3000 元，想要日系寬鬆，不要太貼身。"}'
```

API 文件：`http://127.0.0.1:8000/docs`。測試：`.venv/bin/python -m pip install -r requirements-dev.txt` 後執行 `.venv/bin/python -m pytest -q`。既有 `.venv` 若仍是 Python 3.8，須以 Python 3.11 重建。

## FashionCLIP 商品搜尋

`/api/v1/search` 會先套用類別、價格、庫存、尺寸、排除顏色／版型等硬條件，再只對合法候選做 FashionCLIP cosine similarity。商品向量在 `data/embeddings/products/`，索引 metadata 必須和 query model 的 backend 相同；不同 encoder 的 512 維向量不可混用。

本專案在 macOS/Python 3.11 使用 Transformers 版 `patrickjohncyh/fashion-clip`，而不是會因 `annoy` 原生擴充失敗的舊 `fashion-clip` PyPI 套件。第一次在有網路的機器設定模型快取時執行：

```bash
FASHIONCLIP_ALLOW_DOWNLOAD=true .venv/bin/python -c 'from scripts.build_embeddings import FashionCLIPWrapper; print(FashionCLIPWrapper(device="cpu").backend)'
```

預設只讀本機快取，不會讓 API 請求臨時下載模型。若模型或索引無法載入，文字搜尋會明示為 `metadata_text` 降級；圖片搜尋會回 `embedding_unavailable_image`，不會產生假的相似度分數。

## 前端啟動

前端位於 `frontend/`，使用 React、Vite 與 TypeScript。安裝 Node.js 22.18+ 後，在 repo 根目錄執行：

```bash
npm --prefix frontend ci
npm run dev
```

開啟 `http://127.0.0.1:5173`。開發模式預設連接本機 FastAPI：推薦、Feed、貼文商品及互動都使用同一 API 與 session。先啟動 port 8000 的後端；Vite 會將 `/api/*` 和 `/products/*` proxy 到後端。只有要單獨預覽前端推薦 UI 時，才設 `VITE_USE_MOCK_RECOMMENDATION=true`。

```bash
VITE_USE_MOCK_RECOMMENDATION=true npm run dev
```

Production build 不使用 Mock，並預期 `/api/v1/recommend` 與前端位於同網域。API 金鑰只能留在後端，不得放入 `VITE_*`。

若要啟用前端 Firebase JS SDK，複製 `frontend/.env.example` 為 `frontend/.env.local`，填入 Firebase Web App config。這組 config 只給前端初始化 Auth / Firestore / Storage，不可拿來初始化 Python backend。

前端建置與 contract 測試：

```bash
npm run build
npm test
```

## P0 端點

| Endpoint | 回應 |
| --- | --- |
| `GET /health` | 模式、資料庫、catalog 與 B/C/D 可用狀態 |
| `POST /api/v1/recommend` | Intent、完整穿搭、總價、證據理由；無解回 `NO_MATCHING_PRODUCTS` |
| `POST /api/v1/search` | 已接入 `backend.search`：文字、圖片與混合商品搜尋；依類別、顏色、價格硬篩選 |
| `GET /api/v1/feed?user_id=...&cursor=...` | 貼文排序使用 session 偏好、已儲存互動與可選趨勢分數，並提供穩定 cursor 分頁 |
| `GET /api/v1/posts/{post_id}` | 創作者、來源、標記與對應展示商品 |
| `POST /api/v1/events/batch` | 事件陣列，回 accepted/duplicate 數 |
| `POST /api/v1/feedback` | session 偏好與重新推薦；`remember_preference` 暫停用 |
| `GET /api/v1/profile/{user_id}?session_id=...` | session 偏好 |
| `POST /api/v1/session/{id}/reset` | 刪除 session 事件、偏好、Intent |
| `GET /api/v1/insights` | 匿名事件計數、樣本數、時間範圍、`source_type=demo` |

例如文字搜尋。商城頁目前使用這個模式；在未安裝 FashionCLIP 依賴時，回應會標示 `metadata_text`，以商品名稱、搜尋欄位、風格和色彩做可重現的文字排序：

```json
{"session_id":"demo-001","query_text":"日系","mode":"text","filters":{"categories":["top"],"excluded_colors":["beige"]}}
```

明確回饋：

```json
{"event_id":"feedback-001","session_id":"demo-001","event_type":"explicit","explicit_patch":{"excluded.colors":["beige"]}}
```

事件上報的 body 是陣列，每筆含 `event_id`、`session_id`、`event_type`、`target_type`、`target_id`。dwell 另需 `dwell_ms` 與 `is_foreground`。所有錯誤使用 `{"error":{"code", "message", "retryable", "details"}}` 格式。

## 已接入的 B/C/D 實作與外部 live 模組

預設流程已直接接入 repo 內已實作的功能：`backend.mock.MockServices` 的意圖、推薦、回饋、事件與 session profile；`backend.search.search_products` 的商品搜尋；`backend.post_feed.rank_feed` 的貼文排序；以及 `EventStore` 的互動與趨勢分數讀取。前端的「商城」頁已呼叫 `/api/v1/search`，商品點擊也會回寫事件。`backend/post_trends.py` 的趨勢分數會在匯入 Trends CSV 後自動參與排序；目前沒有匯入資料時該訊號為零。

`BACKEND_MODE=live` 保留給 [draft2.md](draft2.md) 第 8 節定義的獨立模組介面：`intent.parse_intent`、`recommender.recommend`、`feedback.get_profile`、`events.record_interactions` 等。這些 `backend/intent.py`、`backend/recommender.py`、`backend/feedback.py`、`backend/events.py` 檔案尚未交付，因此不能設定為 `live`；並非既有實作沒有被 API 呼叫。真實 catalog 可由 `APP_DATA_DIR` 指向包含 `products.json`、`posts.json`、`creators.json` 的目錄。

環境變數範例見 [.env.example](.env.example)。`CORS_ORIGINS` 以逗號分隔；預設只接受 `http://localhost:5173`。`APP_DB_PATH` 預設在被 Git 忽略的 `runtime/`。API key 僅由 B 模組讀取環境變數，不放進 repo。

## Firebase deployment prep

Firebase project ID: `bnosca-outfit-demo`。

前端使用 Firebase JS SDK：

- `frontend/src/lib/firebase.ts` 從 Vite env 初始化 `auth`、`db`、`storage`。
- `frontend/.env.local` 僅供本機使用，不提交；範本在 `frontend/.env.example`。
- 現有推薦 UI 仍保留 `VITE_USE_MOCK_RECOMMENDATION=true` fallback。

後端使用 Firebase Admin SDK：

- `backend/firebase.py` 透過 Application Default Credentials 初始化 Admin SDK。
- Cloud Run / Google Cloud 執行環境應由 IAM 提供 credentials，不要 commit service account JSON。
- 本機 seed 前可先執行 `gcloud auth application-default login`，或暫時設定 `GOOGLE_APPLICATION_CREDENTIALS` 指到本機 service account JSON。

Firestore repository layer 位於 `backend/repositories/`，目前先提供 `products`、`posts`、`creators`、`users`、`sessions`、`interactions` 封裝；主推薦流程尚未改成直接依賴 Firestore，避免破壞既有 mock demo。

匯入初始 fixture：

```bash
python scripts/seed_firestore.py
```

seed 會把 `data/fixtures/products.json`、`posts.json`、`creators.json` 寫入 Firestore collection，document id 分別使用 `product_id`、`post_id`、`creator_id`。

安全規則草案：

- Firestore: `firebase/firestore.rules`
- Storage: `firebase/storage.rules`

預期策略是 `products` / `posts` / `creators` 公開讀、client 不可寫；`users` 僅使用者本人可讀寫；`sessions` / `interactions` 必須登入且 `user_id == request.auth.uid`。後端 Admin SDK 由 Google Cloud IAM 控制，不受 Firestore rules 限制。

## 貼文推薦模組

`backend/post_feed.py` 提供不依賴 HTTP 的貼文排序與偏好更新函式，讓 E 後端可在後續整合時直接呼叫。排序訊號包含長期偏好、單次瀏覽意圖、社交關係、深度互動、內容品質、協同分數、近期成長、探索、新鮮度、重複曝光衰減及負面互動。

Google Trends 匯出檔由 `backend/post_trends.py` 解析，關鍵字對應表位於 `data/trend_keywords.json`，資料以 `geo=TW` 存入 SQLite。趨勢分為 `style`、`color`、`occasion`、`item`，合成權重依序為 50%、25%、15%、10%；外部趨勢占最終排序 10%。目前模組尚未替換 `/api/v1/feed` 的固定展示 feed，以避免在 E 的整合點未協調前修改 `backend/main.py`。

共用 schema 新增選填的使用者年齡區間／性別、profile 版本、貼文商品類別標籤、互動統計、明確的 feed 分數拆解及外部趨勢資料契約。新增欄位均有預設值，既有 fixtures 與前端契約可繼續使用。

## 部署與現況

可用 [Dockerfile](Dockerfile) 建立單一映像，包含 React build、FastAPI、合併商品庫與本機 Kaggle 圖片；容器的 `/` 提供前端，`/api/*` 提供 API。預設監聽 `8000`，也接受平台提供的 `PORT`。Docker daemon 未啟動時可先用本機雙服務驗收；部署平台、domain 與 credentials 待提供，因此尚未上線。容器內 SQLite 若未掛載持久磁碟，重啟後 session／事件會消失。

`draft2.md` 的 P0 目前是可跑通的整合展示：1012 件商品、20 篇貼文與相似商品標記、完整穿搭、互動事件及 session 偏好 API；商城頁已接入文字商品搜尋，API 也可接收圖片與混合搜尋。三次合併資料集 API 主流程已通過自動測試；瀏覽器已驗證推薦、貼文商品抽屜與商城查詢。Dashboard UI、session reset UI、獨立 B/C/D live 模組、線上部署與 FashionCLIP 依賴安裝仍待實作或驗收。貼文商品只標示 `similar` 展示配對，並非同款；資料來源與圖片展示權利尚須團隊確認。
