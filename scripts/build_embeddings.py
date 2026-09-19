"""
FashionCLIP Embedding Generation Pipeline
Author: Hackathon Role C / F (Data & Multimodal Embeddings)

Converts JSON items (products or posts) into L2-normalized image and text embeddings.
Exports .npy matrices and an id_mapping.json for downstream search and recommendation.
"""

import argparse
import hashlib
import json
import os
import sys
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image

try:
    import requests
except ImportError:
    requests = None

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable


class ImageLoader:
    """Handles local loading and remote downloading of images with disk caching."""

    def __init__(self, cache_dir: Path, image_dir: Optional[Path] = None, timeout: int = 10):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.image_dir = image_dir
        self.timeout = timeout

    def get_image(self, source: str) -> Optional[Image.Image]:
        """Load image from local path or URL."""
        if not source:
            return None

        # 1. Local path or image_dir check
        candidates = [Path(source)]
        if self.image_dir:
            candidates.append(self.image_dir / source)
            candidates.append(self.image_dir / Path(source).name)

        for p in candidates:
            if p.is_file():
                try:
                    img = Image.open(p)
                    return img.convert("RGB")
                except Exception as e:
                    print(f"[Warning] Failed to open local image {p}: {e}", file=sys.stderr)
                    return None

        # 2. Remote URL check
        if source.startswith("http://") or source.startswith("https://"):
            if requests is None:
                print("[Error] 'requests' library required for URL downloading.", file=sys.stderr)
                return None

            url_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
            cache_file = self.cache_dir / f"{url_hash}.jpg"

            # Check cache
            if cache_file.is_file():
                try:
                    img = Image.open(cache_file)
                    return img.convert("RGB")
                except Exception:
                    pass  # Corrupted cache, re-fetch

            # Download
            try:
                resp = requests.get(source, timeout=self.timeout)
                if resp.status_code == 200:
                    img = Image.open(BytesIO(resp.content)).convert("RGB")
                    img.save(cache_file, format="JPEG", quality=95)
                    return img
                else:
                    print(f"[Warning] HTTP {resp.status_code} fetching {source}", file=sys.stderr)
                    return None
            except Exception as e:
                print(f"[Warning] Failed to download {source}: {e}", file=sys.stderr)
                return None

        print(f"[Warning] Image source not found: {source}", file=sys.stderr)
        return None


class FashionCLIPWrapper:
    """
    Unified interface for FashionCLIP.
    Tries official 'fashion-clip' package first, then HuggingFace Transformers,
    and falls back to deterministic mock vectors if --mock is enabled.
    """

    def __init__(self, device: str = "auto", mock: bool = False):
        self.mock = mock
        self.dimension = 512
        self.device = device
        self.model = None
        self.processor = None
        self.backend = None

        if self.mock:
            print("[Info] Running in MOCK mode (generating deterministic normalized embeddings).")
            self.backend = "mock"
            return

        self._init_model()

    def _init_model(self):
        # Determine PyTorch device
        if self.device == "auto":
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.device = "cpu"
        print(f"[Info] Target device: {self.device}")

        # Attempt 1: Official fashion-clip package
        try:
            from fashion_clip.fashion_clip import FashionCLIP
            print("[Info] Loading official FashionCLIP model...")
            self.model = FashionCLIP("fashion-clip")
            self.backend = "fashion_clip"
            print("[OK] Loaded official FashionCLIP successfully.")
            return
        except ImportError:
            pass

        # Attempt 2: Hugging Face Transformers with patrickjohncyh/fashion-clip or clip-ViT-B/32
        try:
            from transformers import AutoProcessor, AutoModel
            import torch

            model_name = "patrickjohncyh/fashion-clip"
            print(f"[Info] Trying HuggingFace model: {model_name}...")
            self.processor = AutoProcessor.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name).to(self.device)
            self.model.eval()
            self.backend = "transformers"
            print(f"[OK] Loaded HuggingFace {model_name} successfully.")
            return
        except Exception as e:
            print(f"[Warning] Could not load HuggingFace FashionCLIP ({e}).", file=sys.stderr)

        # If nothing works and not explicitly mock, warn and switch to mock
        print("[Warning] Neither 'fashion-clip' nor transformers model could be loaded.", file=sys.stderr)
        print("[Warning] Falling back to mock embeddings for testing.", file=sys.stderr)
        self.backend = "mock"

    def encode_images(self, images: list[Image.Image], batch_size: int = 32) -> np.ndarray:
        if self.backend == "mock":
            # Deterministic mock vectors based on image dimensions & average RGB
            vecs = []
            for img in images:
                stat = np.array(img.resize((16, 16)).convert("RGB"), dtype=np.float32)
                # Seed pseudo-random with image stats
                np.random.seed(int(stat.mean() * 1000) % (2**31 - 1))
                v = np.random.randn(self.dimension).astype(np.float32)
                vecs.append(v)
            return np.vstack(vecs)

        if self.backend == "fashion_clip":
            # fashion-clip accepts image objects or paths
            embeddings = self.model.encode_images(images, batch_size=batch_size)
            return np.array(embeddings, dtype=np.float32)

        if self.backend == "transformers":
            import torch
            all_embeddings = []
            for i in range(0, len(images), batch_size):
                batch_imgs = images[i : i + batch_size]
                inputs = self.processor(images=batch_imgs, return_tensors="pt").to(self.device)
                with torch.no_grad():
                    image_features = self.model.get_image_features(**inputs)
                    if hasattr(image_features, "pooler_output") and image_features.pooler_output is not None:
                        image_features = image_features.pooler_output
                    elif hasattr(image_features, "last_hidden_state"):
                        image_features = image_features.last_hidden_state[:, 0, :]
                    elif not isinstance(image_features, torch.Tensor) and hasattr(image_features, "__getitem__"):
                        image_features = image_features[0]
                    image_features = image_features.cpu().numpy().astype(np.float32)
                all_embeddings.append(image_features)
            return np.vstack(all_embeddings)

        raise RuntimeError(f"Unknown backend: {self.backend}")

    def encode_texts(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        if self.backend == "mock":
            vecs = []
            for text in texts:
                h = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)
                np.random.seed(h)
                v = np.random.randn(self.dimension).astype(np.float32)
                vecs.append(v)
            return np.vstack(vecs)

        if self.backend == "fashion_clip":
            embeddings = self.model.encode_text(texts, batch_size=batch_size)
            return np.array(embeddings, dtype=np.float32)

        if self.backend == "transformers":
            import torch
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]
                inputs = self.processor(
                    text=batch_texts, return_tensors="pt", padding=True, truncation=True
                ).to(self.device)
                with torch.no_grad():
                    text_features = self.model.get_text_features(**inputs)
                    if hasattr(text_features, "pooler_output") and text_features.pooler_output is not None:
                        text_features = text_features.pooler_output
                    elif hasattr(text_features, "last_hidden_state"):
                        text_features = text_features.last_hidden_state[:, 0, :]
                    elif not isinstance(text_features, torch.Tensor) and hasattr(text_features, "__getitem__"):
                        text_features = text_features[0]
                    text_features = text_features.cpu().numpy().astype(np.float32)
                all_embeddings.append(text_features)
            return np.vstack(all_embeddings)

        raise RuntimeError(f"Unknown backend: {self.backend}")


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    """L2 normalize vectors along last axis."""
    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    return matrix / np.maximum(norms, 1e-10)


def extract_search_text(item: dict[str, Any], text_field: str) -> str:
    """Extract search text or build informative text representation from item fields."""
    if text_field in item and item[text_field]:
        return str(item[text_field])

    # Fallback to combining common clothing attributes
    parts = []
    for key in ["name", "category", "caption"]:
        if key in item and item[key]:
            parts.append(str(item[key]))

    for list_key in ["colors", "styles", "materials", "occasion"]:
        if list_key in item and isinstance(item[list_key], list):
            parts.extend([str(x) for x in item[list_key]])

    if "fit" in item and item["fit"]:
        parts.append(f"版型:{item['fit']}")

    return "；".join(parts) if parts else "clothing item"


def run_pipeline(
    input_file: Path,
    output_dir: Path,
    id_field: str = "product_id",
    image_field: str = "image_url",
    text_field: str = "search_text",
    image_dir: Optional[Path] = None,
    batch_size: int = 32,
    device: str = "auto",
    modality: str = "all",
    cache_dir: Optional[Path] = None,
    mock: bool = False,
):
    if not input_file.is_file():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")

    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = cache_dir or (output_dir / ".cache_images")

    # 1. Load JSON data
    print(f"[1/4] Reading data from {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list of items, got {type(data)}")

    print(f"      Total items: {len(data)}")

    # 2. Init Loader & Model
    image_loader = ImageLoader(cache_dir=cache_dir, image_dir=image_dir)
    model = FashionCLIPWrapper(device=device, mock=mock)

    valid_ids: list[str] = []
    loaded_images: list[Image.Image] = []
    texts_to_encode: list[str] = []
    failed_items: list[dict[str, str]] = []

    # Placeholder image for missing or failed images
    placeholder_img = Image.new("RGB", (224, 224), color=(200, 200, 200))

    # 3. Process items
    print(f"[2/4] Preprocessing images and text fields...")
    for idx, item in enumerate(tqdm(data, desc="Loading data")):
        item_id = str(item.get(id_field, f"item_{idx}"))
        img_src = item.get(image_field, "")
        text_content = extract_search_text(item, text_field)

        img = image_loader.get_image(img_src)
        if img is None:
            failed_items.append({"id": item_id, "field": image_field, "source": str(img_src)})
            img = placeholder_img  # Use placeholder so index alignment is preserved

        valid_ids.append(item_id)
        loaded_images.append(img)
        texts_to_encode.append(text_content)

    num_items = len(valid_ids)
    image_embeddings = None
    text_embeddings = None

    # 4. Generate Embeddings
    print(f"[3/4] Generating FashionCLIP embeddings (Modality: {modality})...")

    if modality in ("all", "image"):
        print(f"      Encoding {num_items} images (batch_size={batch_size})...")
        raw_img_emb = model.encode_images(loaded_images, batch_size=batch_size)
        image_embeddings = l2_normalize(raw_img_emb)
        print(f"      [OK] Image embeddings shape: {image_embeddings.shape}")

    if modality in ("all", "text"):
        print(f"      Encoding {num_items} text queries (batch_size={batch_size})...")
        raw_txt_emb = model.encode_texts(texts_to_encode, batch_size=batch_size)
        text_embeddings = l2_normalize(raw_txt_emb)
        print(f"      [OK] Text embeddings shape: {text_embeddings.shape}")

    # 5. Export artifacts
    print(f"[4/4] Saving artifacts to {output_dir}...")

    if image_embeddings is not None:
        img_npy_path = output_dir / "image_embeddings.npy"
        np.save(img_npy_path, image_embeddings)
        print(f"      Saved: {img_npy_path}")

    if text_embeddings is not None:
        txt_npy_path = output_dir / "text_embeddings.npy"
        np.save(txt_npy_path, text_embeddings)
        print(f"      Saved: {txt_npy_path}")

    # Mapping metadata
    id_mapping = {
        "count": num_items,
        "dimension": model.dimension,
        "backend": model.backend,
        "normalized": True,
        "id_field": id_field,
        "index_to_id": valid_ids,
        "id_to_index": {item_id: idx for idx, item_id in enumerate(valid_ids)},
        "failed_items": failed_items,
    }

    mapping_file = output_dir / "id_mapping.json"
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(id_mapping, f, ensure_ascii=False, indent=2)
    print(f"      Saved: {mapping_file}")

    # Enhanced items catalog with embedding IDs
    enhanced_items = []
    for item, item_id in zip(data, valid_ids):
        item_copy = dict(item)
        item_copy["image_embedding_id"] = f"emb_img_{item_id}"
        item_copy["text_embedding_id"] = f"emb_txt_{item_id}"
        enhanced_items.append(item_copy)

    with_emb_file = output_dir / "products_with_embeddings.json"
    with open(with_emb_file, "w", encoding="utf-8") as f:
        json.dump(enhanced_items, f, ensure_ascii=False, indent=2)
    print(f"      Saved: {with_emb_file}")

    print("\n=======================================================")
    print(f"[SUCCESS] Embeddings successfully generated for {num_items} items.")
    print(f"  - Output directory: {output_dir}")
    print(f"  - Image vector file: {'image_embeddings.npy' if image_embeddings is not None else 'None'}")
    print(f"  - Text vector file: {'text_embeddings.npy' if text_embeddings is not None else 'None'}")
    print(f"  - ID Mapping: id_mapping.json")
    if failed_items:
        print(f"  - Warning: {len(failed_items)} items had missing/corrupted images (used placeholder).")
    print("=======================================================\n")


def parse_args():
    parser = argparse.ArgumentParser(description="Convert JSON items to FashionCLIP embeddings.")
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path("data/products.json"),
        help="Path to input JSON file (default: data/products.json)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("data/embeddings"),
        help="Directory to save .npy embeddings and mapping (default: data/embeddings)",
    )
    parser.add_argument(
        "--id-field",
        type=str,
        default="product_id",
        help="JSON field for item ID (default: product_id; use post_id for posts)",
    )
    parser.add_argument(
        "--image-field",
        type=str,
        default="image_url",
        help="JSON field for image URL/path (default: image_url)",
    )
    parser.add_argument(
        "--text-field",
        type=str,
        default="search_text",
        help="JSON field for text embedding (default: search_text)",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=32,
        help="Batch size for embedding generation (default: 32)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="Device to run model on (default: auto)",
    )
    parser.add_argument(
        "--modality",
        type=str,
        default="all",
        choices=["all", "image", "text"],
        help="Modalities to encode (default: all)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Directory for caching downloaded images",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode (fast dummy normalized vectors for testing)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(
        input_file=args.input,
        output_dir=args.output_dir,
        id_field=args.id_field,
        image_field=args.image_field,
        text_field=args.text_field,
        batch_size=args.batch_size,
        device=args.device,
        modality=args.modality,
        cache_dir=args.cache_dir,
        mock=args.mock,
    )

