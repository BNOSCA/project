# Web implementation handoff

更新日期：2026-09-19  
交接 branch：`feature/frontend-ai-query`

## 1. 目前狀態

此 branch 已完成以下整合：

- React + Vite + TypeScript 社群穿搭前端與首頁 AI 詢問欄。
- 合併最新 `origin/main`，包含貼文推薦排序、Mastodon OOTD fixtures、多模態商品搜尋與 embedding pipeline。
- 前端首頁已接上本機 FastAPI `GET /api/v1/feed`。
- 首頁按讚會送至 `POST /api/v1/feedback`，更新本機推薦偏好。
- 首頁收藏會送至 `POST /api/v1/events/batch`，記錄互動事件。
- FastAPI 未啟動時，前端貼文會自動退回內建 mock，不會造成空白頁。
- Firebase Web SDK、Admin SDK、Firestore repositories、rules 與 seed script 已準備，但主流程尚未改為依賴 Firestore。

目前仍是本機整合版本，尚未正式部署。

## 2. 本機資料流程

```text
data/fixtures/posts.json
data/fixtures/creators.json
data/fixtures/products.json
        ↓
FastAPI mock services + post ranking
        ↓
GET /api/v1/feed
        ↓
frontend/src/services/feed.ts
        ↓
React homepage
        ↓
like → POST /api/v1/feedback
save → POST /api/v1/events/batch
        ↓
runtime/demo.sqlite3
```

測試身分固定使用 `anonymous-demo`。瀏覽器會在 `localStorage` 保存一個 feed session ID，使重新整理後仍可沿用同一個本機偏好 session。

## 3. 貼文與圖片來源

- 後端推薦資料：`data/fixtures/posts.json`。
- 創作者資料：`data/fixtures/creators.json`。
- 商品資料：`data/fixtures/products.json`。
- 貼文圖片主要使用 fixtures 內的 Mastodon 公開圖片 URL，並非從 Firebase Storage 讀取。
- 後端未啟動時，前端使用 `frontend/src/data/mockPosts.ts` 與 `mockUsers.ts`。
- 前端「發文」目前只建立 browser Object URL 與 React state；重新整理後會消失。

## 4. 重要檔案

### Frontend

- `frontend/src/App.tsx`：頁面狀態、按讚、收藏、本地發文與 feed 載入入口。
- `frontend/src/services/feed.ts`：後端 Feed schema 到前端 `OutfitPost` 的 mapping，以及 like/save API 呼叫。
- `frontend/src/services/recommendation.ts`：首頁 AI 詢問欄；可切換固定 mock 或本機 FastAPI。
- `frontend/src/pages/HomePage.tsx`：首頁 feed 與 AI query UI。
- `frontend/src/pages/CreatePostPage.tsx`：目前僅本機暫存的發文 UI。
- `frontend/src/lib/firebase.ts`：Firebase Web SDK 初始化。
- `frontend/.env.example`：前端環境變數範本。
- `frontend/vite.config.ts`：將 `/api` proxy 到 `http://127.0.0.1:8000`。

### Backend

- `backend/main.py`：FastAPI endpoints。
- `backend/schemas.py`：前後端整合時應遵循的正式 Pydantic schema。
- `backend/mock.py`：fixtures、feed、feedback 與本機互動服務。
- `backend/post_feed.py`：貼文排序與偏好更新。
- `backend/search.py`：多模態／文字商品搜尋。
- `backend/db.py`：本機 SQLite session 與互動資料。
- `backend/firebase.py`：Firebase Admin SDK 初始化。
- `backend/repositories/`：Firestore repository layer，目前尚未接管主流程。

### Firebase and data

- `firebase/firestore.rules`：Firestore rules 草案。
- `firebase/storage.rules`：Storage rules 草案。
- `scripts/seed_firestore.py`：將 fixtures 匯入 Firestore。
- `data/fixtures/`：目前 FastAPI mock mode 的正式本機測試資料。
- `data/mastodon_test/`：Mastodon pipeline 的中間資料與 QA 輸出，不是前端直接讀取的資料來源。

## 5. 建議環境

- Windows PowerShell
- Python virtual environment：`C:\Users\User\Desktop\hackathon\.venv`
- Node.js：專案要求 `>=22.18.0`
- 專案目錄：`C:\Users\User\Desktop\hackathon\project-repo`

更新 Python dependencies：

```powershell
cd C:\Users\User\Desktop\hackathon\project-repo
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

多模態 embedding 的完整額外依賴在 `requirements-embedding.txt`。一般 API 與既有單元測試不需要先執行模型下載。

更新 frontend dependencies：

```powershell
cd C:\Users\User\Desktop\hackathon\project-repo
npm --prefix frontend install
```

## 6. 本機啟動

開啟第一個 PowerShell，啟動 FastAPI：

```powershell
cd C:\Users\User\Desktop\hackathon\project-repo
..\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

後端文件：`http://127.0.0.1:8000/docs`  
健康檢查：`http://127.0.0.1:8000/health`

開啟第二個 PowerShell，啟動 frontend：

```powershell
cd C:\Users\User\Desktop\hackathon\project-repo
npm --prefix frontend run dev
```

前端：`http://127.0.0.1:5173`

## 7. 如何手動驗證

1. 同時啟動 FastAPI 與 Vite。
2. 打開首頁，確認出現來自 Mastodon fixtures 的貼文，而不是只有原始六篇 frontend mock。
3. 點一篇貼文的按讚，確認 UI 立即切換。
4. 點收藏，確認 UI 顯示收藏提示。
5. 重新整理頁面，session ID、按讚與收藏 ID 應由 `localStorage` 保留。
6. 再次呼叫 feed 時，後端會依該 session 的互動偏好重新計分。
7. 關閉 FastAPI、重新整理前端，應自動退回 frontend mock，不應白屏。
8. AI 詢問欄目前預設可使用固定 recommendation mock；若要測本機 API，在啟動 Vite 前執行：

```powershell
$env:VITE_USE_MOCK_RECOMMENDATION='false'
npm --prefix frontend run dev
```

## 8. 自動測試

從外層 workspace 執行後端測試：

```powershell
cd C:\Users\User\Desktop\hackathon
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

預期結果：

```text
21 passed, 2 warnings
```

兩個 warning 是 FastAPI／Starlette 測試相依套件的 deprecation warning，目前不影響測試結果。

前端 domain tests：

```powershell
cd C:\Users\User\Desktop\hackathon
npm --prefix project-repo test
```

預期：`2 passed`。

前端 production build：

```powershell
cd C:\Users\User\Desktop\hackathon
npm --prefix project-repo\frontend run build
```

預期：TypeScript 與 Vite build 成功。

## 9. 主要 API

| Method | Path | 用途 |
| --- | --- | --- |
| `GET` | `/health` | backend／fixture 狀態 |
| `POST` | `/api/v1/recommend` | AI 文字需求與穿搭推薦 |
| `POST` | `/api/v1/search` | 商品文字／圖片／混合搜尋 |
| `GET` | `/api/v1/feed` | 個人化貼文 feed |
| `GET` | `/api/v1/posts/{post_id}` | 貼文、創作者與商品細節 |
| `POST` | `/api/v1/events/batch` | impression、dwell、save、click 等互動 |
| `POST` | `/api/v1/feedback` | like、dislike、明確文字回饋 |
| `GET` | `/api/v1/profile/{user_id}` | 測試使用者偏好 profile |
| `POST` | `/api/v1/session/{session_id}/reset` | 清除本機 session |
| `GET` | `/api/v1/insights` | demo event 統計 |

正式 request／response schema 請以 `backend/schemas.py` 為準，不要從 UI 型別反推後端 contract。

## 10. Firebase 狀態

已完成程式碼預備：

- Firebase Web SDK initialization。
- Firebase Admin SDK initialization。
- products、posts、creators、users、sessions、interactions repositories。
- Firestore／Storage rules 草案。
- fixtures seed script。

尚未完成：

- 主推薦流程改讀 Firestore。
- Firebase Authentication 與 frontend current user 串接。
- 真實發文寫入 Firestore。
- 圖片上傳 Firebase Storage。
- 正式環境 credentials 與 Hosting／backend deployment。

`frontend/.env.local` 與 service-account JSON 不得 commit。前端 Firebase public config 應放在 `.env.local`；後端 credential 應使用 Application Default Credentials 或未納入 Git 的 service-account file。

## 11. 後續實作優先順序

1. 補 frontend feed 的 loading／error／empty state，並顯示真實 creator 資訊，而不是由 `creator_id` 暫時轉換名稱。
2. 上報 impression、post open、dwell、product click、not interested 等事件。
3. 提供明確的「不喜歡／減少此類內容」Feedback UI。
4. 決定 feed 在互動後是立即 refetch、局部重排，或下一次進入頁面才重排。
5. 將 Create Post 從 React memory 改為 Firebase Storage + Firestore。
6. 將 Firebase Auth user UID 映射到 API `user_id`，移除固定 `anonymous-demo`。
7. 商城推薦模組交付後，對齊 `backend/schemas.py` 並完成 AI query → 商品／貼文雙結果整合。
8. 全模組完成後再做 staging Firebase seed、整合測試與正式部署。

## 12. 已知限制

- 前端貼文圖片依賴外部 Mastodon URL，離線或來源失效時可能無法顯示。
- 前端發文重新整理後消失。
- Like／save 目前只有新增事件，取消 like／save 尚未建立對應後端事件。
- Feed API 回應沒有直接附完整 Creator，因此 frontend 暫時由 `creator_id` 產生顯示名稱。
- AI recommendation 的 frontend mock 與 backend feed 是兩條不同 fallback；測試時要確認 `VITE_USE_MOCK_RECOMMENDATION`。
- Firebase rules 尚未在 emulator／staging project 完成 end-to-end 驗證。
- 尚未完成正式部署，現階段網址只在 localhost。

## 13. Git 注意事項

- 目前開發 branch：`feature/frontend-ai-query`。
- 本 branch 已合併 `origin/main`，不要再直接合併舊的 `post` branch；該 branch 的歷史狀態不包含完整 frontend。
- 接手前先執行 `git pull --ff-only origin feature/frontend-ai-query`。
- 不要 commit `.env.local`、service-account JSON、`runtime/demo.sqlite3`、`node_modules` 或 frontend build output。

