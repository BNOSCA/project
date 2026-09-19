"""Build the app-ready catalog from the checked-in Kaggle and official snapshots."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KAGGLE = ROOT / "data" / "catalog" / "kaggle_500" / "products.json"
OFFICIAL = ROOT / "data" / "catalog" / "official_brands" / "products.json"
EDITORIAL_POSTS = ROOT / "data" / "fixtures" / "posts.json"
EDITORIAL_CREATORS = ROOT / "data" / "fixtures" / "creators.json"
OUTPUT = ROOT / "data" / "catalog" / "combined"

CATEGORY_MAP = {
    "Topwear": "top",
    "Bottomwear": "bottom",
    "Shoes": "shoes",
    "Accessories": "accessory",
    "Innerwear": "innerwear",
    "Dress": "dress",
    "Apparel Set": "set",
}
GENDER_MAP = {"Men": "men", "Women": "women", "Boys": "kids", "Girls": "kids", "Unisex": "unisex"}


def load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_kaggle(record: dict) -> dict:
    """Retain only Product contract fields and make absent commerce data explicit."""
    gender = GENDER_MAP.get(str(record.get("gender", "")).title())
    color = record.get("color")
    category = CATEGORY_MAP.get(record.get("source_sub_category"), record.get("category", "other"))
    styles = [value for value in (record.get("usage"), record.get("article_type")) if value]
    search_text = " ".join(str(value) for value in (
        record.get("name"), category, record.get("source_master_category"),
        record.get("source_sub_category"), record.get("article_type"), color,
        record.get("season"), record.get("usage"), gender,
    ) if value)
    return {
        "product_id": record["product_id"],
        "name": record["name"],
        "category": category,
        "price": None,
        "currency": "TWD",
        "colors": [color] if color else [],
        "styles": styles,
        "fit": None,
        "materials": [],
        "sizes": [],
        "image_url": record.get("image_url"),
        "image_urls": [record["image_url"]] if record.get("image_url") else [],
        "product_url": None,
        "source": record["source"],
        "source_name": "Kaggle Fashion Product Images Dataset",
        "brand": None,
        "brand_product_code": record.get("source_product_id"),
        "gender": gender,
        "category_path": [value for value in (record.get("source_master_category"), record.get("source_sub_category"), record.get("article_type")) if value],
        "attributes": {
            "image_file": record["image_file"],
            "image_source_url": record.get("image_source_url", ""),
            "season": record.get("season", ""),
            "year": record.get("year", 0),
            "dataset_usage": record.get("usage", ""),
        },
        "source_checked_at": record.get("source_checked_at"),
        "availability": "demo_only",
        "search_text": search_text,
    }


def match_similar_product(post: dict, products: list[dict]) -> dict:
    """Link a clearly labelled similar item; never claim the creator wore it."""
    caption = post.get("caption", "").lower()
    if any(word in caption for word in ("鞋", "sneaker", "boots")):
        category = "shoes"
    elif any(word in caption for word in ("褲", "裙", "pants", "skirt")) and not any(
        word in caption for word in ("上衣", "襯衫", "背心", "外套", "shirt", "jacket")
    ):
        category = "bottom"
    else:
        category = "top"

    colors = set(post.get("colors", []))
    styles = set(post.get("styles", []))
    candidates = [p for p in products if p["category"] == category and p.get("price") is not None]
    if not candidates:
        raise ValueError(f"no priced {category} products for {post['post_id']}")

    def score(product: dict) -> tuple[int, int, str]:
        product_colors = set(product.get("colors", []))
        if "white" in colors:
            product_colors = product_colors | ({"white"} if "off_white" in product_colors else set())
        overlap = 3 * len(colors & product_colors) + len(styles & set(product.get("styles", [])))
        return (-overlap, product["price"], product["product_id"])

    chosen = min(candidates, key=score)
    return {"product_id": chosen["product_id"], "label": category, "bbox": None, "match_type": "similar"}


def main() -> None:
    kaggle = [normalize_kaggle(record) for record in load(KAGGLE)]
    official = load(OFFICIAL)
    for record in official:
        if record["category"] == "shoes" and "吊飾" in record["name"]:
            record["category"] = "accessory"
    products = kaggle + official
    ids = [record["product_id"] for record in products]
    if len(ids) != len(set(ids)):
        raise ValueError("combined product IDs must be unique")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "products.json").write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    posts = load(EDITORIAL_POSTS)
    creators = load(EDITORIAL_CREATORS)
    creator_ids = {creator["creator_id"] for creator in creators}
    for post in posts:
        if post["creator_id"] not in creator_ids:
            raise ValueError(f"unknown creator in {post['post_id']}")
        if not post.get("tagged_products"):
            tag = match_similar_product(post, official)
            post["tagged_products"] = [tag]
            post["item_tags"] = list(dict.fromkeys(post.get("item_tags", []) + [tag["label"]]))
    product_ids = set(ids)
    if any(tag["product_id"] not in product_ids for post in posts for tag in post["tagged_products"]):
        raise ValueError("editorial post tag refers to an unknown catalog product")
    (OUTPUT / "posts.json").write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "creators.json").write_text(json.dumps(creators, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    image_link = OUTPUT / "images"
    target = Path("..") / "kaggle_500" / "images"
    if image_link.exists() or image_link.is_symlink():
        if not image_link.is_symlink() or image_link.readlink() != target:
            raise ValueError(f"unexpected existing image path: {image_link}")
    else:
        image_link.symlink_to(target, target_is_directory=True)

    summary = {
        "total_products": len(products),
        "sources": {"kaggle": len(kaggle), "official_brands": len(official)},
        "categories": dict(sorted(Counter(record["category"] for record in products).items())),
        "priced_products": sum(record.get("price") is not None for record in products),
        "local_kaggle_images": len(kaggle),
        "posts": len(posts),
        "creators": len(creators),
        "posts_with_similar_product": sum(bool(post["tagged_products"]) for post in posts),
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
