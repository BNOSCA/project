"""Build the app-ready catalog from official brand snapshots only."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OFFICIAL = ROOT / "data" / "catalog" / "official_brands" / "products.json"
OUTPUT = ROOT / "data" / "catalog" / "combined"


def main() -> None:
    products = json.loads(OFFICIAL.read_text(encoding="utf-8"))
    for product in products:
        name = product["name"]
        if any(word in name for word in ("吊飾", "腰帶", "領巾", "圍巾", "襪", "太陽眼鏡")):
            product["category"] = "accessory"
        elif "連帽上衣" in name:
            product["category"] = "top"
        # The scraped listing category has a few obvious mismatches. Keep
        # jackets out of trouser results and tops out of jacket results before
        # category-constrained image retrieval.
        elif "外套" in name and product["category"] in {"top", "bottom"}:
            product["category"] = "outerwear"
        elif product["category"] == "bottom" and (
            "背心" in name or ("襯衫" in name and "連身裙" not in name)
        ):
            product["category"] = "top"
    ids = [record["product_id"] for record in products]
    if len(ids) != len(set(ids)):
        raise ValueError("official product IDs must be unique")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "products.json").write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name in ("posts.json", "creators.json"):
        (OUTPUT / name).write_text("[]\n", encoding="utf-8")

    summary = {
        "total_products": len(products),
        "sources": dict(sorted(Counter(record["source_name"] for record in products).items())),
        "categories": dict(sorted(Counter(record["category"] for record in products).items())),
        "priced_products": sum(record.get("price") is not None for record in products),
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
