# LOOP｜穿搭靈感、商品搜尋與個人化貼文推薦

LOOP 是一個以 React 前端和 FastAPI 後端組成的穿搭展示專案。使用者可以用文字、圖片或兩者一起搜尋商品；後端解析穿搭需求、組合完整穿搭，並依互動與偏好排序穿搭貼文。商品是 GU／UNIQLO 的資料快照，價格與庫存狀態不會即時更新。

這份 README 描述目前程式與隨附資料實際提供的功能。預設採 `BACKEND_MODE=mock`、`STORAGE_BACKEND=sqlite`：`mock` 指本地推薦與回饋服務，商品搜尋仍會嘗試載入真正的 FashionCLIP 模型；沒有模型時會明確降級。Firebase 帳號與發文功能則需要另行設定 Firestore 模式。

## 快速開始

需求：Python 3.11、Node.js 22.18+，以及首次安裝套件所需的網路連線。以下指令都從專案根目錄執行。

終端機一，啟動 API：

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
STORAGE_BACKEND=sqlite BACKEND_MODE=mock .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

終端機二，啟動前端：

```bash
npm --prefix frontend ci
npm run dev
```

開啟 <http://127.0.0.1:5173>；API 健康檢查在 <http://127.0.0.1:8000/health>，互動式 API 文件在 <http://127.0.0.1:8000/docs>。Vite 會把 `/api/*` 與 `/products/*` 轉送到本機的 8000 埠。

不用 Firebase 設定也能試首頁的商品搜尋、穿搭結果與商城。登入、個人檔案、收藏及發文需要 Firebase 設定；前端目前僅在登入後載入貼文 Feed，因此未登入時不會自動顯示貼文。若根目錄已有 `.env`，其中的設定可能覆蓋預設值；上述啟動指令明確指定 SQLite 與 mock 模式。

可用以下請求快速確認 API：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-001","query_text":"日系寬鬆襯衫","mode":"text","filters":{"available_only":true}}'
```

## 使用者功能與資料流

| 入口 | 目前行為 |
| --- | --- |
| 今天想穿什麼 | 接受文字、圖片或圖文混合查詢，搜尋可購買單品；有文字且意圖可解讀時，也回傳完整穿搭。 |
| 商城 | 文字搜尋或純條件瀏覽；可指定類別、最高單價、尺寸、排除顏色／版型、僅顯示有庫存。 |
| 首頁／探索貼文 | 登入後取得個人化 Feed；探索頁在已載入貼文上做前端關鍵字與標籤篩選。 |
| 貼文相似商品 | 已標記商品可在貼文詳情顯示；有相容模型及圖片索引時，會依貼文衣物區域做視覺搜尋。前端在查詢失敗時可能顯示明確標示的展示商品。 |
| 帳號與發文 | Firestore 模式提供 Firebase 登入後的 onboarding、個人檔案、按讚／收藏、個人貼文、Storage 圖片上傳。 |
| 公司洞察 | 管理員 UID 可查看 Firestore 聚合的使用者與互動統計。 |

### 搜尋與穿搭怎麼算

`POST /api/v1/search` 會先依商品 metadata 篩選候選，再計算搜尋相關度。文字中的明確排除、預算與衣物品類可轉成硬條件；例如「不要米色」會排除米色商品，而不是只扣分。原始查詢文字則送入搜尋模型。若 FashionCLIP 和索引可用，文字模式融合「查詢文字對商品文字」65% 與「查詢文字對商品圖片」35% 的相似度；純圖片模式比圖片向量，圖文混合模式用 RRF 融合排名。只用條件瀏覽時不載入模型。

查詢會由 `backend/intent/` 解析為 `Intent`。有 `GROQ_API_KEY` 或 `LLM_API_KEY` 時嘗試 Groq 結構化解析，否則使用規則解析。解析出的硬條件作用於候選篩選；風格、顏色、版型與場合等偏好則用於完整穿搭的組合與評分。目前沒有將 LLM 推出的軟標籤另外加權到單品搜尋分數；單品的語意分數仍以原始查詢文字為主。

完整穿搭由符合條件的上衣、下身及可用時的鞋款組合，檢查總預算，並綜合需求標籤和使用者偏好排序。搜尋回應的 `products` 是單品；`outfits` 是另外計算的穿搭，兩種分數不要直接比較。

若模型無法使用，文字搜尋標示 `metadata_text` 並以商品文字欄位排序；圖片搜尋標示 `embedding_unavailable_image`，不會宣稱取得有效視覺相似度。搜尋分數與前端百分比都是排序訊號，不是購買機率或已校準的相似百分比。

### 貼文推薦怎麼算

`backend/post_feed.py` 使用長期偏好、本次 session 意圖、最近的穿搭需求、社交關係、互動深度、貼文品質、協同訊號、成長速度、探索性與可選的 Google Trends 訊號排序；還會考慮新鮮度、重複曝光及負面互動。若有最近的穿搭需求，該需求標籤在推薦模式的基礎權重為 60%。貼文卡的 `Match%` 是後端綜合 Feed 分數乘以 100 並取整，不是文字或圖片的相似機率。Google Trends CSV 需先匯入，未匯入時其訊號為零。

## 隨附資料與模型

| 路徑 | 內容與用途 |
| --- | --- |
| `data/catalog/combined/` | 預設商品庫：512 件官方品牌商品快照（GU 509、UNIQLO 3）；其中 488 件標記 `available`。`posts.json`、`creators.json` 是空陣列。 |
| `data/fixtures/` | 本地展示資料：6 件合成商品、1,000 篇貼文及 437 位創作者。預設 combined catalog 的貼文為空時，後端自動載入此處的貼文和創作者；商品仍來自 combined。 |
| `data/embeddings/official_products/` | 官方商品的圖片與文字向量索引，含 509 件商品；3 件 UNIQLO 商品因圖片取得失敗未進索引。 |
| `data/catalog/official_brands/` | 合併 catalog 的官方商品來源資料。 |
| `data/catalog/kaggle_500/` | 500 件 Kaggle 展示商品及本機圖片；不屬於預設商城商品庫。 |
| `data/posts.json`、`data/creators.json` | 其他資料處理產物；預設 API 不會直接讀取。 |

預設首頁與商城開啟「僅有庫存」時，官方商品中同時標記 `available` 且具有索引的目前是 485 件。這是匯入時的快照狀態，不代表品牌網站現在仍有貨。主要 `category` 為 `top`、`bottom`、`outerwear`、`shoes`、`accessory`；商品 schema 另外包含價格、顏色、風格、版型、材質、尺寸、品牌、來源、圖片／購買連結與細分類路徑，見 [`backend/schemas.py`](backend/schemas.py)。

要重新生成合併商品庫：

```bash
.venv/bin/python scripts/build_combined_catalog.py
```

要重新建立正式商品向量索引，先讓模型下載至本機快取，再執行：

```bash
FASHIONCLIP_ALLOW_DOWNLOAD=true .venv/bin/python -c 'from scripts.build_embeddings import FashionCLIPWrapper; print(FashionCLIPWrapper(device="cpu").backend)'
.venv/bin/python scripts/build_embeddings.py --input data/catalog/combined/products.json --output-dir data/embeddings/official_products --skip-failed-images --download-workers 6 --batch-size 16
```

執行前請確認模型回傳的 backend 與索引 `id_mapping.json` 中的 `backend` 相同；不同 encoder 產生的向量不能混用。API 啟動後預設只讀本機模型快取，不會在請求中偷偷下載。這個建索引步驟會覆寫指定輸出目錄的既有索引，請在需要更新時才執行。更多資料管線選項見 [`scripts/README.md`](scripts/README.md)。

## 設定與儲存模式

後端讀取根目錄的 `.env`（範本為 [`.env.example`](.env.example)）。主要設定如下：

| 變數 | 用途／程式預設值 |
| --- | --- |
| `BACKEND_MODE` | `mock`：本地推薦與回饋；`live`：呼叫尚未完整接入的獨立模組，不適合一般啟動。預設 `mock`。 |
| `STORAGE_BACKEND` | `sqlite` 或 `firestore`，程式預設 `sqlite`。注意 `.env.example` 目前示範值是 `firestore`，直接複製前須按需求修改。 |
| `APP_DATA_DIR` | SQLite 模式的 catalog 目錄，預設 `./data/catalog/combined`；須有 `products.json`、`posts.json`、`creators.json`。 |
| `APP_DB_PATH` | SQLite 檔案，預設 `./runtime/demo.sqlite3`。 |
| `GROQ_API_KEY`、`GROQ_MODEL` | 選用的需求解析與搜尋說明 LLM；未設定 key 時使用 fallback。 |
| `CORS_ORIGINS` | 允許的前端 origin，以逗號分隔；預設 `http://localhost:5173`。 |
| `ADMIN_UIDS` | 可查看公司洞察的 Firebase UID，逗號分隔。 |
| `FIREBASE_AUTH_REQUIRED` | SQLite API 是否強制檢查 Firebase token；預設 `false`。 |
| `GOOGLE_CLOUD_PROJECT`、`FIREBASE_STORAGE_BUCKET` | Firestore 模式使用的 Firebase 專案與 Storage bucket。 |

Firebase 前端設定放在 `frontend/.env.local`（欄位見 [`frontend/.env.example`](frontend/.env.example)），不能將後端金鑰放進 `VITE_*`。Firestore 模式需 Google Application Default Credentials 或 `GOOGLE_APPLICATION_CREDENTIALS`，以及可用的 Firebase Authentication、Firestore 與 Storage。以 `STORAGE_BACKEND=firestore` 啟動時，`backend/main.py` 會改用 `backend/cloud_api.py`；這個 API 要求正式登入 token，沒有 SQLite 帳號資料 fallback。可用 `python scripts/seed_firestore.py` 匯入 fixtures 的商品、貼文和創作者；此指令不是匯入 512 件官方商品。寫入真實 Firestore 前先確認目標專案。

SQLite 模式記錄 session、意圖、回饋與事件；重啟伺服器資料仍留在 `APP_DB_PATH`。可用 `FIRESTORE_SYNC_ENABLED=true` 額外同步互動事件，前提是 Firebase 權限已就緒。Firestore 模式則以雲端帳號資料為主，提供 `/api/v1/me/*` 和使用者發文 API。兩種模式的端點並不完全相同，切換前請先確認所需功能。

## API 摘要

兩種儲存模式都有 `/health`、`/api/v1/search`、`/api/v1/recommend`、`/api/v1/feed`、`/api/v1/posts/{post_id}`、`/api/v1/events/batch`、`/api/v1/feedback`、`/api/v1/profile/{user_id}`、`/api/v1/session/{session_id}/reset` 與受保護的 `/api/v1/admin/*`，但驗證要求和部分請求限制不同；以目前啟動模式的 `/docs` 為準。Firestore 模式另有登入帳號、個人貼文狀態和發文端點；SQLite 模式另有 `/api/v1/insights` 與搜尋除錯路由。

常用請求：

```bash
# 文字搜尋並套用硬條件
curl -X POST http://127.0.0.1:8000/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-001","query_text":"日系襯衫，不要米色","mode":"text","filters":{"categories":["top"],"available_only":true}}'

# 只按條件瀏覽商品（SQLite 模式）
curl -X POST http://127.0.0.1:8000/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-001","mode":"text","filters":{"categories":["shoes"],"price_max":2000,"available_only":true}}'

# 產生完整穿搭
curl -X POST http://127.0.0.1:8000/api/v1/recommend \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-001","text":"週末想穿日系寬鬆，整套預算 3000 元，不要米色"}'
```

圖片搜尋時以 `query_image` 傳入圖片 data URL 或後端可讀取的圖片 URL，並將 `mode` 設為 `image`；圖文混合搜尋設為 `mixed`。`/api/v1/recommend` 本身目前只收文字需求；首頁的圖片查詢走 `/api/v1/search`。搜尋回應含 `products`、`retrieval.fusion_method`、解析後的 `intent`，有文字時可含 `outfits`。錯誤詳情依模式而異，SQLite API 使用 `error.code`、`error.message` 等欄位。

## 開發、測試與部署現況

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
npm run build
npm test
```

Python 測試涵蓋 API、意圖解析、搜尋、穿搭、貼文排序與雲端持久化。目前測試套件尚未全綠：`tests/test_api.py` 有兩項預期完整穿搭的測試收到 `NO_MATCHING_PRODUCTS`。根目錄的 `npm test` 是前端契約測試指令，但目前 Node 原生 TS 執行器無法解析 `frontend/src/services/feed.ts` 的無副檔名相對匯入，會以 `ERR_MODULE_NOT_FOUND` 失敗；`npm run build` 可正常完成。前端 build 產生 `frontend/dist/` 後，本機 FastAPI 會在 `/` 提供靜態頁面。

[`Dockerfile`](Dockerfile) 是部署草案，目前沒有複製 `scripts/`、`prompts/` 與官方向量索引，而搜尋模組在啟動時依賴其中的程式；尚不能視為可直接部署並完整使用搜尋的映像。若容器使用 SQLite，也須另外掛載持久儲存，否則重建容器會失去事件與 session。Firebase 規則草案見 [`firebase/firestore.rules`](firebase/firestore.rules) 與 [`firebase/storage.rules`](firebase/storage.rules)。

主要程式位置：`frontend/src/` 為 UI、`backend/main.py` 為 SQLite API、`backend/cloud_api.py` 為 Firestore API、`backend/search.py` 為商品檢索、`backend/intent/` 為需求解析、`backend/mock.py` 為本地穿搭與回饋服務、`backend/post_feed.py` 為貼文排序、`backend/schemas.py` 為共用資料契約。產品方向與原始分工可參考 [`draft2.md`](draft2.md)，但功能現況以本 README 與程式碼為準。
