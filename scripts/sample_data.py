"""
Generate sample data (products.json and posts.json) strictly conforming to backend/schemas.py.
Also generates local placeholder images so FashionCLIP pipeline can be tested completely offline.
"""

import json
import os
from pathlib import Path
from PIL import Image, ImageDraw


def generate_placeholder_image(filepath: Path, text: str, bg_color: tuple[int, int, int]):
    """Create a clean placeholder image with product category and color info."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (300, 400), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Draw simple frame & text
    draw.rectangle([(10, 10), (290, 390)], outline=(255, 255, 255), width=3)
    draw.text((30, 180), text, fill=(255, 255, 255))
    
    img.save(filepath, format="JPEG", quality=90)


def create_sample_dataset(data_dir: Path):
    data_dir.mkdir(parents=True, exist_ok=True)
    images_dir = data_dir / "sample_images"
    images_dir.mkdir(parents=True, exist_ok=True)

    products = [
        # Tops
        {
            "product_id": "p-top-001",
            "name": "寬鬆牛津襯衫",
            "category": "top",
            "price": 990,
            "currency": "TWD",
            "colors": ["black"],
            "styles": ["japanese", "minimal"],
            "fit": "relaxed",
            "materials": ["cotton"],
            "sizes": ["S", "M", "L"],
            "image_url": "https://example.com/images/p-top-001.jpg",
            "product_url": "https://example.com/products/p-top-001",
            "source": "demo_catalog",
            "source_checked_at": "2026-09-18",
            "availability": "available",
            "search_text": "寬鬆牛津襯衫；黑色；日系；極簡；休閒；棉；非貼身",
            "_bg_color": (35, 35, 35)
        },
        {
            "product_id": "p-top-002",
            "name": "日系落肩重磅短T",
            "category": "top",
            "price": 790,
            "currency": "TWD",
            "colors": ["charcoal"],
            "styles": ["japanese", "casual"],
            "fit": "oversized",
            "materials": ["heavy_cotton"],
            "sizes": ["M", "L", "XL"],
            "image_url": "https://example.com/images/p-top-002.jpg",
            "product_url": "https://example.com/products/p-top-002",
            "source": "demo_catalog",
            "source_checked_at": "2026-09-18",
            "availability": "available",
            "search_text": "日系落肩重磅短T；炭灰；日系；休閒；戶外；寬鬆",
            "_bg_color": (60, 60, 65)
        },
        {
            "product_id": "p-top-003",
            "name": "休閒棉質亞麻開襟衫",
            "category": "top",
            "price": 1290,
            "currency": "TWD",
            "colors": ["beige"],
            "styles": ["minimal", "casual"],
            "fit": "regular",
            "materials": ["linen", "cotton"],
            "sizes": ["S", "M"],
            "image_url": "https://example.com/images/p-top-003.jpg",
            "product_url": "https://example.com/products/p-top-003",
            "source": "demo_catalog",
            "source_checked_at": "2026-09-18",
            "availability": "available",
            "search_text": "休閒棉質亞麻開襟衫；米色；極簡；亞麻；輕薄；戶外",
            "_bg_color": (210, 195, 170)
        },
        # Bottoms
        {
            "product_id": "p-bottom-001",
            "name": "日系錐形打褶長褲",
            "category": "bottom",
            "price": 1190,
            "currency": "TWD",
            "colors": ["black"],
            "styles": ["japanese", "minimal"],
            "fit": "relaxed",
            "materials": ["polyester", "rayon"],
            "sizes": ["M", "L"],
            "image_url": "https://example.com/images/p-bottom-001.jpg",
            "product_url": "https://example.com/products/p-bottom-001",
            "source": "demo_catalog",
            "source_checked_at": "2026-09-18",
            "availability": "available",
            "search_text": "日系錐形打褶長褲；黑色；日系；寬鬆；休閒；打褶",
            "_bg_color": (25, 25, 30)
        },
        {
            "product_id": "p-bottom-002",
            "name": "戶外機能工裝短褲",
            "category": "bottom",
            "price": 990,
            "currency": "TWD",
            "colors": ["olive"],
            "styles": ["outdoor", "casual"],
            "fit": "relaxed",
            "materials": ["nylon"],
            "sizes": ["S", "M", "L"],
            "image_url": "https://example.com/images/p-bottom-002.jpg",
            "product_url": "https://example.com/products/p-bottom-002",
            "source": "demo_catalog",
            "source_checked_at": "2026-09-18",
            "availability": "available",
            "search_text": "戶外機能工裝短褲；軍綠橄欖；戶外；日系機能；防潑水",
            "_bg_color": (70, 85, 60)
        },
        {
            "product_id": "p-bottom-003",
            "name": "修身卡其休閒褲",
            "category": "bottom",
            "price": 890,
            "currency": "TWD",
            "colors": ["beige"],
            "styles": ["smart_casual"],
            "fit": "slim",
            "materials": ["cotton"],
            "sizes": ["M", "L"],
            "image_url": "https://example.com/images/p-bottom-003.jpg",
            "product_url": "https://example.com/products/p-bottom-003",
            "source": "demo_catalog",
            "source_checked_at": "2026-09-18",
            "availability": "available",
            "search_text": "修身卡其休閒褲；米色卡其；合身貼身；棉質",
            "_bg_color": (205, 185, 150)
        },
        # Shoes
        {
            "product_id": "p-shoes-001",
            "name": "簡約帆布休閒鞋",
            "category": "shoes",
            "price": 820,
            "currency": "TWD",
            "colors": ["black"],
            "styles": ["japanese", "casual"],
            "fit": "regular",
            "materials": ["canvas", "rubber"],
            "sizes": ["26", "27", "28"],
            "image_url": "https://example.com/images/p-shoes-001.jpg",
            "product_url": "https://example.com/products/p-shoes-001",
            "source": "demo_catalog",
            "source_checked_at": "2026-09-18",
            "availability": "available",
            "search_text": "簡約帆布休閒鞋；黑色；日系簡約；休閒低筒；百搭",
            "_bg_color": (40, 40, 45)
        },
        {
            "product_id": "p-shoes-002",
            "name": "戶外越野健行涼鞋",
            "category": "shoes",
            "price": 1080,
            "currency": "TWD",
            "colors": ["charcoal"],
            "styles": ["outdoor", "japanese"],
            "fit": "regular",
            "materials": ["synthetic", "rubber"],
            "sizes": ["26", "27"],
            "image_url": "https://example.com/images/p-shoes-002.jpg",
            "product_url": "https://example.com/products/p-shoes-002",
            "source": "demo_catalog",
            "source_checked_at": "2026-09-18",
            "availability": "available",
            "search_text": "戶外越野健行涼鞋；炭灰黑；日系戶外；山系；透氣",
            "_bg_color": (55, 55, 58)
        },
    ]

    # Generate images locally
    for p in products:
        bg = p.pop("_bg_color")
        img_path = images_dir / f"{p['product_id']}.jpg"
        generate_placeholder_image(img_path, f"{p['product_id']}\n{p['name']}", bg)

    products_file = data_dir / "products.json"
    with open(products_file, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"[OK] Generated {len(products)} products at: {products_file}")

    # Generate posts.json for exploration feed
    posts = [
        {
            "post_id": "post-001",
            "creator_id": "creator-001",
            "image_url": "https://example.com/posts/post-001.jpg",
            "caption": "週末戶外日系寬鬆穿搭，炭灰混搭黑長褲",
            "styles": ["japanese", "outdoor", "relaxed"],
            "colors": ["black", "charcoal"],
            "occasion": ["casual", "outdoor"],
            "tagged_products": [
                {
                    "product_id": "p-top-001",
                    "label": "寬鬆牛津襯衫",
                    "bbox": [0.20, 0.12, 0.72, 0.55],
                    "match_type": "similar"
                },
                {
                    "product_id": "p-bottom-001",
                    "label": "錐形打褶長褲",
                    "bbox": [0.25, 0.52, 0.75, 0.90],
                    "match_type": "similar"
                }
            ],
            "source": "licensed_demo_content",
            "source_checked_at": "2026-09-18",
            "is_demo": True,
            "created_at": "2026-09-18T10:00:00Z"
        },
        {
            "post_id": "post-002",
            "creator_id": "creator-002",
            "image_url": "https://example.com/posts/post-002.jpg",
            "caption": "極簡米白棉麻穿搭，陽光下的自然色調",
            "styles": ["minimal", "casual"],
            "colors": ["beige"],
            "occasion": ["casual"],
            "tagged_products": [
                {
                    "product_id": "p-top-003",
                    "label": "棉質亞麻開襟衫",
                    "bbox": [0.20, 0.15, 0.70, 0.60],
                    "match_type": "similar"
                }
            ],
            "source": "licensed_demo_content",
            "source_checked_at": "2026-09-18",
            "is_demo": True,
            "created_at": "2026-09-18T11:00:00Z"
        }
    ]

    posts_file = data_dir / "posts.json"
    with open(posts_file, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print(f"[OK] Generated {len(posts)} posts at: {posts_file}")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    create_sample_dataset(base_dir / "data")
