"""
Data Validation and Preprocessing Tool
Author: Hackathon Role C / F (Data & Embeddings)

Validates and cleans incoming products.json and posts.json against backend/schemas.py.
Handles Kaggle, official brands, and raw scraped catalogs cleanly.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pydantic import ValidationError

# Import schemas from backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.schemas import Product, Post, Creator


def clean_product_item(item: dict[str, Any], generate_search_text: bool = True) -> tuple[dict[str, Any], list[str]]:
    """Clean and sanitize raw product dict to conform strictly to backend.schemas.Product."""
    fixes = []
    cleaned = dict(item)

    # 1. Map singular 'color' to 'colors' list if needed
    if "color" in item and not cleaned.get("colors"):
        c_val = str(item["color"]).strip().lower()
        if c_val:
            cleaned["colors"] = [c_val]
            fixes.append(f"Mapped color '{c_val}' -> colors: {cleaned['colors']}")

    # 2. Fix price (handle null, string, float)
    raw_price = cleaned.get("price")
    if raw_price is None:
        cat = str(cleaned.get("category", "top")).lower()
        default_price = 790 if cat == "top" else (890 if cat == "bottom" else (990 if cat == "shoes" else 850))
        cleaned["price"] = default_price
        fixes.append(f"Set default price {default_price} for {cat}")
    elif isinstance(raw_price, str):
        digits = re.findall(r"\d+", raw_price)
        cleaned["price"] = int("".join(digits)) if digits else 790
        fixes.append(f"Converted price '{raw_price}' -> {cleaned['price']}")
    elif isinstance(raw_price, float):
        cleaned["price"] = int(round(raw_price))
        fixes.append(f"Converted float price {raw_price} -> {cleaned['price']}")

    # 3. Fix currency
    if cleaned.get("currency") != "TWD":
        cleaned["currency"] = "TWD"
        fixes.append("Set currency to 'TWD'")

    # 4. Fix availability enum: "unknown", "demo_only", "available", "unavailable"
    allowed_avail = {"unknown", "demo_only", "available", "unavailable"}
    current_avail = cleaned.get("availability")
    if current_avail not in allowed_avail:
        if current_avail in {"in_stock", "instock", "true", "True", True}:
            cleaned["availability"] = "available"
        elif current_avail in {"out_of_stock", "false", "False", False}:
            cleaned["availability"] = "unavailable"
        elif current_avail in {"demo_only", "demo"}:
            cleaned["availability"] = "demo_only"
        else:
            cleaned["availability"] = "demo_only"
        fixes.append(f"Normalized availability '{current_avail}' -> '{cleaned['availability']}'")

    # 5. Fix image_url: must be valid HttpUrl or None
    raw_img = cleaned.get("image_url")
    if raw_img is not None:
        raw_img_str = str(raw_img).strip()
        if not raw_img_str or not (raw_img_str.startswith("http://") or raw_img_str.startswith("https://")):
            cleaned["image_url"] = None
            fixes.append(f"Set non-HttpUrl image_url '{raw_img_str}' to null")

    # 6. Fix product_url: must be valid HttpUrl or None
    raw_prod_url = cleaned.get("product_url")
    if raw_prod_url is not None:
        raw_prod_str = str(raw_prod_url).strip()
        if not raw_prod_str or not (raw_prod_str.startswith("http://") or raw_prod_str.startswith("https://")):
            cleaned["product_url"] = None
            fixes.append(f"Set non-HttpUrl product_url '{raw_prod_str}' to null")

    # 7. Ensure list fields are lists of strings
    for list_field in ["colors", "styles", "materials", "sizes"]:
        val = cleaned.get(list_field)
        if val is None:
            cleaned[list_field] = []
        elif isinstance(val, str):
            cleaned[list_field] = [s.strip() for s in re.split(r"[,/、\s]+", val) if s.strip()]
            fixes.append(f"Split string in {list_field} -> {cleaned[list_field]}")

    # 8. Build search_text if missing or empty
    if generate_search_text and not cleaned.get("search_text"):
        parts = []
        for k in ["name", "category", "article_type", "color", "usage", "season"]:
            val = item.get(k)
            if val and isinstance(val, str):
                parts.append(val)
        parts.extend(cleaned.get("colors", []))
        parts.extend(cleaned.get("styles", []))
        if cleaned.get("fit"):
            parts.append(cleaned["fit"])
        cleaned["search_text"] = " ".join(parts)
        fixes.append(f"Generated search_text: '{cleaned['search_text']}'")

    # 9. Ensure default source
    if not cleaned.get("source"):
        cleaned["source"] = "dataset_import"
        fixes.append("Set default source='dataset_import'")

    # 10. Strip extra forbidden fields
    allowed_fields = set(Product.model_fields.keys())
    extra_keys = set(cleaned.keys()) - allowed_fields
    if extra_keys:
        for k in extra_keys:
            del cleaned[k]
        fixes.append(f"Removed {len(extra_keys)} forbidden extra fields")

    return cleaned, fixes


def validate_products(data: list[dict], auto_fix: bool = False) -> tuple[list[dict], bool]:
    all_clean = True
    output_items = []
    id_set = set()

    print(f"\n--- Checking {len(data)} Product items against backend.schemas.Product ---")

    for idx, item in enumerate(data):
        pid = item.get("product_id", f"index_{idx}")

        # Check unique ID
        if pid in id_set:
            print(f"  [ERROR] Duplicate product_id: {pid} at index {idx}")
            all_clean = False
        id_set.add(pid)

        item_to_test = item
        if auto_fix:
            item_to_test, fixes = clean_product_item(item)

        try:
            Product.model_validate(item_to_test)
            output_items.append(item_to_test)
        except ValidationError as e:
            all_clean = False
            print(f"  [INVALID] {pid}:")
            for err in e.errors():
                loc = ".".join(str(l) for l in err["loc"])
                print(f"    -> Field '{loc}': {err['msg']} (input={err.get('input')})")

    return output_items, all_clean


def validate_posts(data: list[dict], products_json: Path | None = None) -> bool:
    all_clean = True
    known_product_ids = set()
    if products_json and products_json.is_file():
        with open(products_json, "r", encoding="utf-8") as f:
            pdata = json.load(f)
            known_product_ids = {p["product_id"] for p in pdata}

    print(f"\n--- Checking {len(data)} Post items against backend.schemas.Post ---")
    post_ids = set()

    for idx, item in enumerate(data):
        pid = item.get("post_id", f"index_{idx}")
        if pid in post_ids:
            print(f"  [ERROR] Duplicate post_id: {pid} at index {idx}")
            all_clean = False
        post_ids.add(pid)

        try:
            post = Post.model_validate(item)
            if known_product_ids:
                for tag in post.tagged_products:
                    if tag.product_id not in known_product_ids:
                        print(f"  [WARNING] Post {pid} tagged unknown product: '{tag.product_id}'")
        except ValidationError as e:
            all_clean = False
            print(f"  [INVALID] Post {pid}:")
            for err in e.errors():
                loc = ".".join(str(l) for l in err["loc"])
                print(f"    -> Field '{loc}': {err['msg']}")

    return all_clean


def main():
    parser = argparse.ArgumentParser(description="Validate and clean incoming JSON data for hackathon backend.")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to input JSON (products or posts)")
    parser.add_argument("--type", "-t", choices=["product", "post"], default="product", help="Data type")
    parser.add_argument("--auto-fix", action="store_true", help="Auto-fix schema violations (strip extra fields, normalize types)")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Save cleaned JSON to this path")
    parser.add_argument("--catalog", type=Path, default=None, help="Optional products.json to cross-check tagged_products in posts")
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"[Error] File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print(f"[Error] JSON root must be an array of objects, got {type(data)}", file=sys.stderr)
        sys.exit(1)

    if args.type == "product":
        cleaned_data, is_valid = validate_products(data, auto_fix=args.auto_fix)
        if args.output and (args.auto_fix or is_valid):
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
            print(f"\n[OK] Saved cleaned product data ({len(cleaned_data)} items) to: {args.output}")

    elif args.type == "post":
        is_valid = validate_posts(data, products_json=args.catalog)

    if is_valid:
        print("\n[SUCCESS] All items strictly satisfy backend/schemas.py requirements!")
    else:
        print("\n[FAILED] Schema violations found. Run with --auto-fix --output <path> to auto-clean.")
        sys.exit(1)


if __name__ == "__main__":
    main()
