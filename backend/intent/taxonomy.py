"""Canonical vocabulary used by the intent parser.

These values should stay aligned with the shared catalog / recommender
vocabulary defined by the project fixtures and draft2 contract.
"""


# ============================================================
# OCCASION
# ============================================================

OCCASION_ALIASES: dict[str, str] = {
    "實習面試": "interview",
    "求職面試": "interview",
    "面試": "interview",
    "interview": "interview",

    "戶外走走": "outdoor",
    "戶外活動": "outdoor",
    "戶外": "outdoor",
    "outdoor": "outdoor",

    "約會": "date",
    "date": "date",

    "上班": "office",
    "辦公室": "office",
    "office": "office",

    "上課": "school",
    "學校": "school",
    "school": "school",

    "婚禮": "wedding",
    "wedding": "wedding",

    "音樂祭": "festival",
    "festival": "festival",

    "旅行": "travel",
    "旅遊": "travel",
    "travel": "travel",

    "聚會": "party",
    "派對": "party",
    "party": "party",

    "日常": "casual",
    "平常": "casual",
    "休閒": "casual",
    "casual": "casual",
}


# ============================================================
# STYLE
# ============================================================

STYLE_ALIASES: dict[str, str] = {
    "日系": "japanese",
    "日本風": "japanese",
    "japanese": "japanese",

    "韓系": "korean",
    "韓風": "korean",
    "korean": "korean",

    "極簡": "minimal",
    "簡約": "minimal",
    "minimal": "minimal",

    "商務休閒": "business_casual",
    "business casual": "business_casual",

    "smart casual": "smart_casual",
    "輕商務": "smart_casual",

    "街頭": "streetwear",
    "streetwear": "streetwear",

    "休閒": "casual",
    "casual": "casual",

    "戶外風": "outdoor",
    "山系": "outdoor",
    "outdoor": "outdoor",

    "運動風": "sporty",
    "運動": "sporty",
    "sporty": "sporty",

    "復古": "vintage",
    "vintage": "vintage",

    "學院風": "preppy",
    "preppy": "preppy",

    "機能風": "techwear",
    "機能": "techwear",
    "techwear": "techwear",

    "老錢風": "old_money",
    "old money": "old_money",
}


# ============================================================
# COLOR
# ============================================================

COLOR_ALIASES: dict[str, str] = {
    "炭灰色": "charcoal",
    "炭灰": "charcoal",
    "charcoal": "charcoal",

    "黑色": "black",
    "black": "black",

    "白色": "white",
    "white": "white",

    "米色": "beige",
    "beige": "beige",

    "灰色": "grey",
    "gray": "grey",
    "grey": "grey",

    "深藍色": "navy",
    "深藍": "navy",
    "海軍藍": "navy",
    "navy": "navy",

    "藍色": "blue",
    "blue": "blue",

    "咖啡色": "brown",
    "棕色": "brown",
    "brown": "brown",

    "奶油色": "cream",
    "cream": "cream",

    "橄欖綠": "olive",
    "olive": "olive",

    "綠色": "green",
    "green": "green",

    "紅色": "red",
    "red": "red",

    "粉紅色": "pink",
    "粉色": "pink",
    "pink": "pink",

    "紫色": "purple",
    "purple": "purple",

    "黃色": "yellow",
    "yellow": "yellow",

    "橘色": "orange",
    "orange": "orange",
}


# ============================================================
# FIT
# ============================================================

FIT_ALIASES: dict[str, str] = {
    "oversized": "oversized",
    "大廓形": "oversized",

    "寬鬆": "relaxed",
    "relaxed": "relaxed",

    "寬版": "relaxed",

    "正常版型": "regular",
    "標準版型": "regular",
    "合身": "regular",
    "regular": "regular",

    "修身": "slim",
    "slim": "slim",

    "緊身": "fitted",
    "貼身": "fitted",
    "fitted": "fitted",
}


# ============================================================
# MATERIAL
# ============================================================

MATERIAL_ALIASES: dict[str, str] = {
    "純棉": "cotton",
    "棉質": "cotton",
    "棉": "cotton",
    "cotton": "cotton",

    "亞麻": "linen",
    "linen": "linen",

    "羊毛": "wool",
    "wool": "wool",

    "牛仔": "denim",
    "denim": "denim",

    "聚酯纖維": "polyester",
    "polyester": "polyester",

    "帆布": "canvas",
    "canvas": "canvas",
}


# ============================================================
# CATEGORY
# ============================================================

CATEGORY_ALIASES: dict[str, str] = {
    "上衣": "top",
    "top": "top",

    "下身": "bottom",
    "褲子": "bottom",
    "bottom": "bottom",

    "鞋子": "shoes",
    "鞋": "shoes",
    "shoes": "shoes",
}

STYLE_ALIASES.update({
    "minimalist": "minimal",
    "minimalistic": "minimal",
})

FIT_ALIASES.update({
    "loose": "relaxed",
    "loose fit": "relaxed",
    "loose-fitting": "relaxed",

    "tight": "fitted",
    "tight fit": "fitted",
    "tight-fitting": "fitted",
})
