# Outfit demo backend (E / P0)

依照 [draft2.md](draft2.md) 的 E 職責建立 FastAPI 入口、共用 Pydantic 契約、SQLite session 資料、固定展示 fixtures 與可替換 B/C/D 的整合點。預設 `BACKEND_MODE=mock`，所有展示商品與貼文都是合成資料，無真實圖片、購買連結或即時庫存。`/health` 會標示 fixture/live 狀態。

## 本機啟動

需要 Python 3.11+。在 repo 根目錄執行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

另開終端：

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/api/v1/recommend \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-001","text":"週末想戶外走走，整套預算 3000 元，想要日系寬鬆，不要太貼身。"}'
```

API 文件：`http://127.0.0.1:8000/docs`。測試：`.venv/bin/python -m pip install -r requirements-dev.txt` 後執行 `.venv/bin/python -m pytest -q`。

## 前端啟動

前端位於 `frontend/`，使用 React、Vite 與 TypeScript。安裝 Node.js 22.18+ 後，在 repo 根目錄執行：

```bash
npm --prefix frontend ci
npm run dev
```

開啟 `http://127.0.0.1:5173`。開發模式預設使用固定 Recommendation Mock，以便在後端未啟動時檢查 AI Query、loading、結果與錯誤畫面。若要串接本機 FastAPI，先啟動 port 8000 的後端，再設定 `VITE_USE_MOCK_RECOMMENDATION=false`；Vite 會將 `/api/*` proxy 到 `http://127.0.0.1:8000`。

```bash
VITE_USE_MOCK_RECOMMENDATION=false npm run dev
```

Windows PowerShell 可使用 `$env:VITE_USE_MOCK_RECOMMENDATION='false'; npm run dev`。Production build 不使用 Mock，並預期 `/api/v1/recommend` 與前端位於同網域。API 金鑰只能留在後端，不得放入 `VITE_*`。

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
| `POST /api/v1/search` | 文字搜尋與確定性 metadata 篩選；圖片／混合搜尋留到 P1 |
| `GET /api/v1/feed?user_id=...&cursor=...` | 固定展示貼文，穩定 cursor 分頁 |
| `GET /api/v1/posts/{post_id}` | 創作者、來源、標記與對應展示商品 |
| `POST /api/v1/events/batch` | 事件陣列，回 accepted/duplicate 數 |
| `POST /api/v1/feedback` | session 偏好與重新推薦；`remember_preference` 暫停用 |
| `GET /api/v1/profile/{user_id}?session_id=...` | session 偏好 |
| `POST /api/v1/session/{id}/reset` | 刪除 session 事件、偏好、Intent |
| `GET /api/v1/insights` | 匿名事件計數、樣本數、時間範圍、`source_type=demo` |

例如文字搜尋：

```json
{"session_id":"demo-001","query_text":"日系","mode":"text","filters":{"categories":["top"],"excluded_colors":["beige"]}}
```

明確回饋：

```json
{"event_id":"feedback-001","session_id":"demo-001","event_type":"explicit","explicit_patch":{"excluded.colors":["beige"]}}
```

事件上報的 body 是陣列，每筆含 `event_id`、`session_id`、`event_type`、`target_type`、`target_id`。dwell 另需 `dwell_ms` 與 `is_foreground`。所有錯誤使用 `{"error":{"code", "message", "retryable", "details"}}` 格式。

## 接入 B/C/D

設定 `BACKEND_MODE=live`。E 將呼叫 [draft2.md](draft2.md) 第 8 節所列函式：`intent.parse_intent(text, previous_intent)`、`intent.parse_feedback(text, current_intent)`、`search.search_products(request, catalog)`、`recommender.recommend(intent, profile, catalog)`、`feedback.get_profile(user_id)`、`feedback.record_feedback(event)`、`events.record_interactions(events)`、`feedback.get_insights()`。Session reset 另需 D 提供 `feedback.reset_session(session_id)`。Feed P0 仍用固定貼文。B 超時或無法取得時，E 使用可觀察的規則 fallback；缺少 C/D 則回 `DATA_UNAVAILABLE`。真實 catalog 可由 `APP_DATA_DIR` 指向包含 `products.json`、`posts.json`、`creators.json` 的目錄。

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

## 部署與現況

可用 [Dockerfile](Dockerfile) 建立映像，預設對外監聽 `8000`，也接受平台提供的 `PORT`；部署平台、domain 與 credentials 尚未提供，因此尚未部署。B/C/D、前端與正式商品授權資料尚未在 repo 中，完整雙模組真實 Demo、三次乾淨環境連跑及錄影／提交須待這些模組完成。此 repo 的 mock 路徑可先提供 A 串接與契約檢查。
