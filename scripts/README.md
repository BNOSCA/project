# FashionCLIP 資料轉 Embedding 管線使用說明

本工具專為梅竹黑客松 **資料處理與向量轉換（Role C / F）** 設計，負責將 JSON 商品或穿搭貼文資料批次轉換為 **FashionCLIP** 高維向量（圖片特徵與文字特徵），並產出標準 `.npy` 檔案與 ID 映射供隊友的搜尋/推薦演算法直接調用。

---

## 快速開始 (Quick Start)

### 1. 安裝環境依賴

```bash
pip install -r requirements.txt
```

> **注意**：
> - 若本機/雲端有 GPU (CUDA)，PyTorch 會自動使用 GPU 加速。
> - 若尚未下載模型或希望快速離線測試流程，可加上 `--mock` 參數。

---

### 2. 生成測試資料 (可選)

如果目前手邊還沒有完整的 `products.json`，可先執行此腳本生成符合規格的商品與圖片：

```bash
python scripts/sample_data.py
```
執行後會在 `data/` 產生：
- `data/products.json`（8 件商品，含 local placeholder 圖片）
- `data/posts.json`（穿搭貼文資料）

---

### 3. 執行 Embedding 轉換

#### 轉換商品資料（預設）：
```bash
python scripts/build_embeddings.py --input data/products.json --output-dir data/embeddings/products
```

#### 轉換穿搭貼文資料（以 post_id 為鍵值）：
```bash
python scripts/build_embeddings.py \
  --input data/posts.json \
  --output-dir data/embeddings/posts \
  --id-field post_id \
  --image-field image_url \
  --text-field caption
```

#### 快速 Mock 測試模式（不下載大模型，驗證整體流程）：
```bash
python scripts/build_embeddings.py --input data/products.json --output-dir data/embeddings/products --mock
```

---

## 輸出檔案說明

執行完成後，在指定的 `--output-dir` 中會產出以下檔案：

| 檔案名稱 | 格式 | 說明 |
|---|---|---|
| `image_embeddings.npy` | NumPy `float32 (N, 512)` | 所有圖片的 FashionCLIP 向量（已完成 **L2 正規化**） |
| `text_embeddings.npy` | NumPy `float32 (N, 512)` | 所有文本的 FashionCLIP 向量（已完成 **L2 正規化**） |
| `id_mapping.json` | JSON | 索引 `0 ~ N-1` 與商品 `product_id` 的對應表、維度及異常清單 |

---

## 交接給隊友使用 (Hand-off to Teammates)

負責查找或推薦演算法（`backend/search.py` / `backend/recommender.py`）的隊友，只需在程式碼中引入 `EmbeddingStore`，即可在 2 行內載入向量並完成檢索：

```python
from scripts.embedding_store import EmbeddingStore

# 1. 載入向量庫 (幾毫秒內載入完畢)
store = EmbeddingStore.load("data/embeddings/products")

# 2. 取得單件商品向量
vec = store.get_image_vector("p-top-001")

# 3. 快速相似度比對 (由於向量已 L2 正規化，底層使用矩陣內積 dot product，極速完成)
# 支援 candidate_ids 傳入（例如：先依價格/類別做 hard-filter 過濾後，再針對剩餘候選做相似度排序）
results = store.search(
    query_vector=vec,
    modality="image", # 或 "text"
    top_k=5,
    candidate_ids=["p-top-001", "p-top-002", "p-bottom-001"] # 選填，候選白名單
)

for product_id, sim in results:
    print(f"商品 {product_id} 相似度: {sim:.4f}")
```

---

## 命令列完整參數表

| 參數 | 簡寫 | 預設值 | 說明 |
|---|---|---|---|
| `--input` | `-i` | `data/products.json` | 輸入的 JSON 檔案路徑 |
| `--output-dir` | `-o` | `data/embeddings` | 向量與映射檔案輸出資料夾 |
| `--id-field` | | `product_id` | JSON 中識別 ID 的欄位名稱（貼文可改 `post_id`） |
| `--image-field` | | `image_url` | 圖片路徑或 URL 欄位名稱 |
| `--text-field` | | `search_text` | 文本欄位名稱（若無則自動由 name/category/colors/styles 組成） |
| `--batch-size` | `-b` | `32` | 批次處理大小（GPU 建議 32~64，CPU 建議 16） |
| `--device` | | `auto` | 運算裝置 (`auto` / `cuda` / `cpu`) |
| `--modality` | | `all` | 抽取模態 (`all` / `image` / `text`) |
| `--cache-dir` | | `.cache_images` | 遠端圖片快取資料夾（避免重覆下載） |
| `--mock` | | `False` | 啟用模擬模式，快速產出合法向量以供測試 |

