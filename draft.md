# Project draft

## Structure
```
project/
├── frontend/           # A
│
├── backend/
│   ├── intent.py       # B
│   ├── recommender.py  # C
│   ├── feedback.py     # D
│   └── main.py         # E
│
├── data/               # C
├── tests/
├── .env.example
└── README.md
```

## Data flow
```
Image: A/frontend (React) -> E/Backend (main.py) ->  C/FashionCLIP(recommender.py) -> E/(main.py) -> A/Frontend
Words: A/frontend (React) -> E/Backend (main.py) -> B/LLM API (intent.py) -> C/E5(recommender.py) -> E/(main.py) -> A/Frontend
D/Personalized feedback only fetched when C recommend
```

## A 前端、使用者
- 實作方式：React
- 使用者可輸入文字或圖片，也可以直接針對商品attribute篩選

## B 需求理解
- Input: 一段自然語言
- 實作：
  - LLM API理解（不要求 LLM 填滿所有資料）
  - 盡量能聽出使用者隱含需求的skill，但需區分硬性與隱晦需求
  - few shot prompting: 在 skill 放入 5–10 組輸入與理想輸出
  - optional: knowledge rag
  - 需測試LLM萃取效果

- Output: 結構化的偏好資料(JSON)

## C 商品推薦、推薦系統
- Input: 結構化的偏好資料(from B)
- 實作：
  - 排序依據：分數 S = S_base(+ lambda*S_trend), S_base = S_relevance + S_preference + S_compatibility(暫定)
    - optional: S_trend，lambda應保持較小，避免流行趨勢蓋過使用者的明確偏好。如果使用者明確說不喜歡，再流行也不應該推薦
  - 1. 硬篩選 filtering
  - 2. Embedding / FashionCLIP
  - 3. Retrieval: Recall, Rerank
  - 4. 交給LLM生成原因（skill 必須明確限制它只能使用商品資料中提供的資訊，不能自行編造庫存、價格或材質）
  - optional:用Polyvore組穿搭
  ```參考共現分數
    compatibility(A, B)
    = A 與 B 出現在同一套穿搭的次數
    / sqrt(A 出現次數 × B 出現次數)
  ```
- Output: 推薦商品列表(JSON)

## D 個人化回饋

- 實作：
  - type 1偏好更新: input 自然語言/圖片
  - type 2偏好更新: 感興趣/不感興趣
```json
{
  "action": "update_preference",
  "scope": "current_session",
  "avoid_colors": ["beige"],
  "preferred_colors": ["black"]
}
```
 - 只要儲存與維護 Profile，C 每次計算分數時讀取即可
 - 回饋前後差異：
   - 使用者明確偏好的商品在 Top-K 推薦中的比例
   - 明確排除的商品是否被正確移除
   - 穿搭結果前後對照畫面
 - 給設計師看的 Dashboard，
   - 所有使用者偏好、購買記錄統計/與趨勢的交集、差異

## E 後端、系統整合
- 接受 HTTP 請求、驗證輸入、協調模組，以及將結果回傳前端
- 實作：
 - FastAPI(Python)
 - 用Pydantic定義好商品規格（Schema）
 - 輸入驗證、錯誤處理、LLM API timeout、API key 保護及找不到商品時的回應


## F 資料處理
- 多模態混合檢索：商品照片＋文字 -> FashionCLIP Image Encoder -> Vector Database

## G 影片、簡報
