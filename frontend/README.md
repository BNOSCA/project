# Frontend — A

在此資料夾中執行 `npm ci`、`npm run dev`；或依根目錄 README 使用捷徑指令。

## 修改入口

- `src/App.tsx`：社交頁面導覽、收藏、按讚與相似商品抽屜。
- `src/pages/HomePage.tsx`：AI 需求入口、推薦結果與原始社交 Feed。
- `src/components/search/`：查詢欄、建議 chips、意圖 chips 與推薦卡。
- `src/services/recommendation.ts`：`POST /api/v1/recommend` 的唯一前端入口與型別。
- `src/data/mockRecommendation.ts`：僅供前端開發模式使用的固定示範回應。
- `src/styles.css`：全站配色、間距、桌面與手機版響應式樣式。

收藏只存 ID 到 localStorage，遇到壞資料或無法寫入時可繼續使用。只有此瀏覽器保留收藏；使用者需求不存到 localStorage。清除全部收藏可在「收藏」頁逐一取消。

## Recommendation API 與 Mock

`npm run dev` 預設使用固定的開發 Mock，方便在後端尚未啟動時驗收完整互動。設定 `VITE_USE_MOCK_RECOMMENDATION=false` 後，前端會改呼叫同網域的 `POST /api/v1/recommend`。Production build 永遠呼叫正式 API，不會在錯誤時悄悄 fallback 到 Mock。

API 金鑰應留在後端，不能放進任何 `VITE_*` 變數或瀏覽器程式碼。

人工驗收：空白需求不可送出；建議 chips 只填入欄位、不直接送出；Enter 與箭頭皆可送出；送出時顯示局部 skeleton；成功後顯示 backend 回傳的 intent 與 outfits；錯誤、無結果及 needs clarification 有獨立狀態；390px 不得水平溢位；下方原始社交 Feed、收藏與發文仍可使用。
