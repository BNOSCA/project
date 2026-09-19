# 貼文推薦系統：修改與新增功能說明

本文整理 `feature/post-feed-ranking` branch、commit `59ebc5a` 中的貼文推薦系統變更，供後端整合、schema 協調、測試與後續開發使用。

## 1. 這次完成的範圍

這次將原本的貼文推薦原型整理成可由後端匯入的獨立模組，並完成以下功能：

- 依使用者長期偏好、當次瀏覽意圖、社交關係、互動品質與內容新鮮度排序貼文。
- 按讚、收藏、停留、追蹤及負面回饋可更新使用者偏好。
- 已互動貼文只失去探索加分，不會直接從候選結果中移除。
- 加入 Google Trends 台灣地區資料，支援風格、顏色、場合與單品四種趨勢。
- 使用 SQLite 儲存外部趨勢，重複匯入相同資料時更新既有紀錄。
- 將新增欄位納入共用 Pydantic schema，並保留舊資料相容性。
- 新增單元測試，驗證 schema、按讚學習、探索邏輯、趨勢計算及 SQLite 寫入。

目前推薦模組尚未替換 `backend/main.py` 中 `/api/v1/feed` 的固定展示 feed。這是刻意保留的整合邊界，避免未和 E 後端負責人協調前直接修改共用入口。

## 2. 修改與新增的檔案

| 檔案 | 類型 | 功能 |
| --- | --- | --- |
| `backend/schemas.py` | 修改 | 擴充使用者、貼文、互動事件、Feed 分數及外部趨勢契約。 |
| `backend/db.py` | 修改 | 新增 Google Trends SQLite 資料表、upsert 與趨勢分數查詢。 |
| `backend/post_feed.py` | 新增 | 實作使用者偏好更新與貼文排序。 |
| `backend/post_trends.py` | 新增 | 解析 Google Trends CSV，轉換成共用趨勢 schema。 |
| `data/trend_keywords.json` | 新增 | 將中文搜尋詞對應到 style、color、occasion、item 標籤。 |
| `tests/test_post_feed.py` | 新增 | 測試 Feed schema、按讚、探索與四種趨勢。 |
| `tests/test_post_trends.py` | 新增 | 測試 Google Trends CSV、TW 地區及 SQLite 去重更新。 |
| `README.md` | 修改 | 說明推薦模組、趨勢權重與尚未接 API 的狀態。 |

## 3. 共用 schema 變更

### `UserProfile`

新增欄位：

- `gender`：選填，支援 `female`、`male`、`non_binary`、`unspecified`。
- `age_range`：選填，例如 `18-24`。
- `profile_version`：偏好每更新一次便遞增，預設為 `0`。

原有的 `preference_weights`、`creator_affinity`、`followed_creator_ids` 與 `trend_affinity` 保留。性別與年齡目前只建立資料契約，尚未直接參與排序，避免在沒有足夠資料及評估前對人口屬性給予武斷權重。

### `InteractionEvent`

除了原有 impression、dwell、post_open、like、dislike、save、product_click，新增：

- `follow`
- `not_interested`
- `hide`
- `quick_skip`

`quick_skip` 表示快速滑過；它是較弱的負向訊號，不等同資料被 rejected，也不會直接刪除貼文。

### `Post`

新增：

- `item_tags`：圖片 embedding API 或貼文分析所產生的單品標籤。
- `engagement`：包含 `like_count`、`save_count`、`comment_count`。

若同學的圖片 embedding API 已回傳共用標籤，推薦系統只需使用標籤，不需要自行管理圖片向量資料庫。

### `FeedItem` 與 `FeedScoreBreakdown`

`FeedItem` 新增頂層 `score`，並將原本未限制結構的 `score_breakdown` 改成明確 schema。拆解欄位包含：

- 偏好：`long_term_preference`、`session_intent`
- 社交與群體：`social`、`collaborative`
- 內容表現：`deep_engagement`、`quality`、`velocity`
- 探索：`exploration`
- 趨勢：`style_trend`、`color_trend`、`occasion_trend`、`item_trend`、`external_trend`
- 調整因子：`fatigue_multiplier`、`recency_multiplier`、`negative_penalty`
- 最終結果：`total_score`

舊 Feed fixture 沒有提供新欄位時會使用預設值，因此此次 schema 擴充不會強迫舊資料立即修改。

### `ExternalTrendSignal`

新增 Google Trends 共用資料契約：

- `source`
- `keyword`
- `attribute`
- `geo`
- `period_start`、`period_end`
- `raw_score`（0～100）
- `normalized_score`（0～1）

## 4. 推薦排序邏輯

`backend/post_feed.py` 提供兩個主要入口：

- `update_profile(...)`：根據互動更新偏好，回傳新的 profile。
- `rank_feed(...)`：將候選貼文排序並回傳符合 `FeedResponse` 的結果。

### 基礎排序訊號與權重

| 訊號 | 權重 |
| --- | ---: |
| 長期偏好 | 25% |
| 當次瀏覽意圖 | 15% |
| 社交關係 | 15% |
| 深度互動品質 | 12% |
| 內容品質 | 10% |
| 相似使用者偏好 | 8% |
| 近期互動成長 | 5% |
| 探索內容 | 10% |

基礎分數先由以上訊號加權，再和 Google Trends 合成：

```text
趨勢分數 = style × 50% + color × 25% + occasion × 15% + item × 10%

合成分數 = 基礎分數 × 90% + 趨勢分數 × 10%

最終分數 = 合成分數 × 重複曝光衰減 × 新鮮度 - 負面互動扣分
```

Feed 最後還會做簡單的創作者多樣性控制：避免同一創作者連續出現，且每次結果最多三篇同一創作者貼文。

### 探索與已互動內容

尚未互動的貼文可取得探索分數 `1.0`。使用者對貼文產生任何已記錄互動後，探索分數變為 `0.0`，但貼文仍保留在候選集合，可依偏好、品質、趨勢等其他訊號繼續入選。

因此目前邏輯符合「已互動只失去探索加分，不直接 rejected」。

## 5. 使用者偏好更新

互動會更新 `style:*`、`color:*`、`occasion:*`、`item:*` 等偏好權重。主要訊號如下：

| 訊號 | 偏好變化 |
| --- | ---: |
| 停留 2～8 秒 | +0.03 |
| 停留 8 秒以上 | +0.05 |
| 開啟貼文 | +0.03 |
| 按讚 | +0.15 |
| 收藏 | +0.20 |
| 追蹤創作者 | +0.30 創作者親和度 |
| 點擊商品 | +0.10 |
| 不喜歡 | -0.30 |
| 不感興趣 | -0.30 |
| 隱藏 | -0.40 |
| 快速滑過 | -0.08 |

偏好值限制在 `-1.0` 到 `1.0`。`update_profile` 每次更新會增加 `profile_version`，但事件去重與 profile 寫回資料庫仍由呼叫端負責。

## 6. Google Trends 與 SQLite

### 關鍵字維度

`data/trend_keywords.json` 目前收錄：

- style：日系、極簡、街頭、戶外、運動、復古、寬鬆、中性、女性、層次、休閒、正式。
- color：黑、白、米、灰、藍。
- occasion：約會、通勤、面試、婚禮、旅行。
- item：寬褲、襯衫、針織、丹寧、長裙。

Google Trends 應使用 `geo=TW` 且建議匯出最近 90 天資料。CSV 解析器支援：

- Google Trends 官方寬格式匯出檔，例如第一欄為「天」。
- `date,keyword,score` 長格式資料。
- UTF-8 BOM、`<1`、空值與無對應關鍵字。

### SQLite 資料

`external_trend_signals` 表使用以下組合避免重複資料：

```text
source + keyword + geo + period_start + period_end
```

再次匯入相同組合時會更新分數，不會新增重複列。查詢時會計算每個關鍵字最近 14 筆資料的平均，再於各自維度內正規化。這可避免顏色搜尋量天然較低時，永遠被高搜尋量的風格關鍵字壓過。

## 7. 測試範圍

新增測試共 6 項：

- 新 schema 的選填欄位與 FeedResponse 驗證。
- style、color、occasion、item 四維趨勢與 50/25/15/10 合成。
- 按讚後 profile 版本與偏好更新。
- 相似貼文在按讚後分數上升。
- 已互動貼文失去探索分數但不被移除。
- Google Trends CSV 解析、TW 地區、SQLite upsert 與維度內正規化。

另外，既有與新增後端測試共收集 17 項並跑到全部通過標記；Codex 內附 Python 在 OneDrive 專案路徑完成後未自動退出，但相同新增測試在暫存工作區可正常完成並退出。前端 contract 測試 2 項通過。

## 8. 尚未完成與後續整合

目前仍需和 E 後端或其他組員協調以下事項：

1. 在 `backend/main.py` 的 `/api/v1/feed` 由固定 fixture 改為呼叫 `rank_feed`。
2. 決定互動事件由哪一層負責去重、寫入及呼叫 `update_profile`。
3. 決定 Google Trends CSV 的排程、匯入入口及更新頻率。
4. 將同學圖片 embedding API 的輸出統一映射到 `styles`、`colors`、`occasion`、`item_tags`。
5. 若要做「特定年齡／性別客群趨勢」，需另外定義 cohort、最小樣本數及隱私規則；目前外部趨勢只有台灣整體趨勢，不會因人口屬性而改變。
6. 若要啟用 collaborative score，需由後端提供相似使用者或相似行為的分數；目前排序函式已保留輸入介面，但沒有自行訓練模型。

## 9. 相容性與影響

- 新增 schema 欄位皆有預設值或為選填，既有資料可繼續解析。
- `FeedItem.score_breakdown` 改為明確模型後，額外的未知欄位會被拒絕；其他組員若要新增分數欄位，應先更新共用 schema。
- SQLite 只新增資料表與索引，不改動既有 events 與 session_profiles。
- 推薦系統只使用圖片分析後的標籤，不直接依賴向量資料庫。
- `/api/v1/feed` 尚未接入新排序，因此目前前端畫面不會自動顯示新排序結果。
