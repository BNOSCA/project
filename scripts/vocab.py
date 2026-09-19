"""共用受控詞彙表。

對齊 draft2.md 5.1 Intent 與 5.2 Product 範例中出現的欄位值，
確保貼文抽取出來的 styles/colors/occasion 跟 B（intent parser）、
C（商品庫）用的是同一組詞，才能互相比對排序。

若 B 或 C 之後擴充詞彙，這裡要同步更新（by convention, not enforced）。
"""

STYLES = [
    "japanese",
    "minimal",
    "casual",
    "street",
    "formal",
    "sporty",
    "vintage",
    "preppy",
    "elegant",
]

COLORS = [
    "black",
    "white",
    "beige",
    "charcoal",
    "navy",
    "brown",
    "green",
    "red",
    "orange",
    "blue",
    "gray",
    "pink",
]

OCCASIONS = [
    "outdoor",
    "casual",
    "work",
    "date",
    "party",
    "travel",
    "formal",
    "sport",
]

FITS = [
    "relaxed",
    "slim",
    "regular",
    "oversized",
]

# 材質從純圖片判斷不可靠（棉/聚酯纖維外觀常常分不出來），
# 只保留視覺上真的看得出來的大類，其餘寧可留空也不硬猜。
MATERIALS = [
    "denim",
    "leather",
    "knit",
    "silky",
]

GARMENT_LABELS = [
    "top",
    "bottom",
    "shoes",
    "outerwear",
    "accessory",
    "dress",
]

# valentinafeve/yolos-fashionpedia 是在 Fashionpedia 資料集上訓練的偵測模型，
# 46 個類別裡有一部分是完整單品（shirt/pants/jacket...），一部分是服裝的
# 局部細節（collar/sleeve/pocket/zipper...）。我們只要「單品」這層，
# 細節類別不映射、直接忽略。
# 實測發現：這個 fashion 專用模型信心分數（0.6-0.97）遠高於通用開放詞彙
# 偵測模型 OWL-ViT（同一張圖只有 0.04-0.17），因為它是真的學過服裝分類，
# 不是硬套通用物件偵測模型。
FASHIONPEDIA_LABEL_TO_GARMENT: dict[str, str] = {
    "shirt, blouse": "top",
    "top, t-shirt, sweatshirt": "top",
    "sweater": "top",
    "cardigan": "outerwear",
    "jacket": "outerwear",
    "vest": "outerwear",
    "pants": "bottom",
    "shorts": "bottom",
    "skirt": "bottom",
    "coat": "outerwear",
    "dress": "dress",
    "jumpsuit": "dress",
    "cape": "outerwear",
    "glasses": "accessory",
    "hat": "accessory",
    "headband, head covering, hair accessory": "accessory",
    "tie": "accessory",
    "glove": "accessory",
    "watch": "accessory",
    "belt": "accessory",
    "bag, wallet": "accessory",
    "scarf": "accessory",
    "shoe": "shoes",
}
