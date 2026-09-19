# Google Trends 貼文推薦計算

## 目的

趨勢分數用來反映台灣近期的整體穿搭需求，作為個人偏好、貼文品質與新鮮度以外的排序訊號。它不會取代使用者個人偏好，而是以 10% 的權重影響最後的貼文推薦。

## 資料來源與查詢設定

來源為 Google Trends Explore，查詢設定固定如下：

- 地區：台灣（`TW`）
- 搜尋類型：Google 網頁搜尋
- 查詢視窗：過去 90 天
- 取用資料：每個關鍵字最近最多 14 個完整日的每日搜尋熱度

Google Trends 的 `score` 是同一個查詢群組中的相對熱度，範圍為 0 到 100。`0` 表示低於 Google 可顯示門檻，不等於完全沒有人搜尋。不同查詢群組的原始分數不可直接比較。

## 關鍵字與貼文 tag 的對應

`data/trend_keywords.json` 將使用者可能搜尋的詞，映射到推薦系統使用的 attribute。例如：

```json
{
  "上班穿搭": "occasion:commute",
  "OL穿搭": "occasion:commute",
  "牛仔褲穿搭": "item:denim",
  "機能風穿搭": "style:outdoor",
  "芭蕾風穿搭": "style:balletcore"
}
```

同一個 attribute 可以有多個關鍵字。這能處理同義詞，例如「通勤穿搭」、「上班穿搭」與「OL穿搭」。若新增 attribute，例如 `style:balletcore`，圖片 embedding API 也必須能將貼文產生同樣的 tag，該貼文才會取得此趨勢分數。

## CSV 與匯入

資料檔是 `data/google_trends_tw_latest.csv`，採 long format：

```csv
date,keyword,score,geo,attribute
2026-09-18,牛仔褲穿搭,36,TW,item:denim
```

`backend/post_trends.py` 讀取 CSV；每筆資料會存進 SQLite 的 `external_trend_signals`：

- `raw_score = score`
- `normalized_score = score / 100`
- 相同 `source + keyword + geo + date` 會 upsert，不會重複累積。

建議每天匯入一次。每一個關鍵字需要至少 14 個完整日，14 日平均才會完全生效。

## 14 日趨勢分數

對每個 `keyword`，系統依日期由新到舊取最多 14 筆：

```text
keyword_average = average(normalized_score of latest 14 daily points)
```

若多個 keyword 指向同一個 attribute，取其中最高的 14 日平均：

```text
attribute_score = max(keyword_average for keywords mapped to the attribute)
```

接著在同一個維度內再次正規化，避免不同 Google Trends 查詢群組的原始比例混用：

```text
dimension_score(attribute) = attribute_score / max(attribute_score in same dimension)
```

四個維度為 `style`、`color`、`occasion`、`item`。若該維度沒有資料，貼文在該維度的趨勢分數為 0。

## 貼文如何取得趨勢分數

每篇貼文會使用圖片 embedding／貼文資料提供的 tags。例如：

```json
{
  "style": ["japanese", "minimal"],
  "color": ["black"],
  "occasion": ["commute"],
  "item": ["shirt", "denim"]
}
```

系統在每個維度取該貼文 tags 的最高趨勢值：

```text
style_trend    = max(score(style:<tag>) for post style tags)
color_trend    = max(score(color:<tag>) for post color tags)
occasion_trend = max(score(occasion:<tag>) for post occasion tags)
item_trend     = max(score(item:<tag>) for post item tags)
```

再依維度權重合成外部趨勢：

```text
external_trend =
    0.50 × style_trend +
    0.25 × color_trend +
    0.15 × occasion_trend +
    0.10 × item_trend
```

## 放入總推薦分數

推薦器先算出不含 Google Trends 的 `base_score`，其中包含長期偏好、短期行為、社交、品質、協同過濾、互動成長與探索。最後以 10% 權重混入趨勢：

```text
pre_adjustment_score =
    0.90 × base_score + 0.10 × external_trend

total_score = pre_adjustment_score × fatigue_multiplier × recency_multiplier - negative_penalty
```

- `fatigue_multiplier`：同一貼文被多次曝光時降低分數。
- `recency_multiplier`：新貼文獲得較高分數。
- `negative_penalty`：負面互動降低分數。

當 `external_trend >= 0.25`，Feed 的推薦理由會顯示「Google Trends 熱門趨勢」。

## 調整指南

| 想調整的項目 | 修改位置 | 注意事項 |
| --- | --- | --- |
| 新增搜尋詞或同義詞 | `data/trend_keywords.json` | 優先映射到既有 attribute，避免無對應貼文 tag。 |
| 新增真正的新風格 | mapping 與圖片 embedding tag | 兩邊 tag 必須完全相同。 |
| 更新每日資料 | `data/google_trends_tw_latest.csv` | 保留最近至少 14 個完整日。 |
| 趨勢影響整體排序的程度 | `backend/post_feed.py` 的 `EXTERNAL_TREND_WEIGHT` | 目前是 0.10。 |
| 各維度的重要性 | `TREND_DIMENSION_WEIGHTS` | 目前 style/color/occasion/item = 50/25/15/10。 |
| 平滑天數或聚合規則 | `backend/db.py` 的 `trend_scores()` | 目前使用最近最多 14 筆的平均。 |
