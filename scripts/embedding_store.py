"""
EmbeddingStore: Teammate-friendly helper for loading and querying FashionCLIP embeddings.

Usage Example:
--------------
from scripts.embedding_store import EmbeddingStore

# 1. Load the store
store = EmbeddingStore.load("data/embeddings")

# 2. Get a single product's image or text embedding
vec = store.get_image_vector("p-top-001")

# 3. Fast cosine similarity search among pre-filtered candidate IDs
results = store.search(
    query_vector=vec,
    modality="image",
    top_k=5,
    candidate_ids=["p-top-001", "p-top-002", "p-bottom-001"] # optional deterministic filter
)
for product_id, similarity in results:
    print(f"{product_id}: {similarity:.4f}")
"""

import json
from pathlib import Path
from typing import Optional
import numpy as np


class EmbeddingStore:
    def __init__(
        self,
        id_to_index: dict[str, int],
        index_to_id: list[str],
        image_embeddings: Optional[np.ndarray] = None,
        text_embeddings: Optional[np.ndarray] = None,
        metadata: Optional[dict] = None,
    ):
        self.id_to_index = id_to_index
        self.index_to_id = index_to_id
        self.image_embeddings = image_embeddings
        self.text_embeddings = text_embeddings
        self.metadata = metadata or {}

    @classmethod
    def load(cls, embedding_dir: str | Path) -> "EmbeddingStore":
        """Load embeddings and mapping from directory."""
        path = Path(embedding_dir)
        mapping_file = path / "id_mapping.json"
        if not mapping_file.is_file():
            raise FileNotFoundError(f"Mapping file not found at: {mapping_file}")

        with open(mapping_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        id_to_index = meta.get("id_to_index", {})
        index_to_id = meta.get("index_to_id", [])

        img_path = path / "image_embeddings.npy"
        image_embeddings = np.load(img_path) if img_path.is_file() else None

        txt_path = path / "text_embeddings.npy"
        text_embeddings = np.load(txt_path) if txt_path.is_file() else None

        return cls(
            id_to_index=id_to_index,
            index_to_id=index_to_id,
            image_embeddings=image_embeddings,
            text_embeddings=text_embeddings,
            metadata=meta,
        )

    def contains(self, item_id: str) -> bool:
        return item_id in self.id_to_index

    def get_image_vector(self, item_id: str) -> Optional[np.ndarray]:
        """Get L2-normalized image embedding for a specific ID."""
        if self.image_embeddings is None or item_id not in self.id_to_index:
            return None
        idx = self.id_to_index[item_id]
        return self.image_embeddings[idx]

    def get_text_vector(self, item_id: str) -> Optional[np.ndarray]:
        """Get L2-normalized text embedding for a specific ID."""
        if self.text_embeddings is None or item_id not in self.id_to_index:
            return None
        idx = self.id_to_index[item_id]
        return self.text_embeddings[idx]

    def search(
        self,
        query_vector: np.ndarray,
        modality: str = "image",
        top_k: int = 10,
        candidate_ids: Optional[list[str]] = None,
    ) -> list[tuple[str, float]]:
        """
        Fast Cosine Similarity search using matrix dot product.
        
        Args:
            query_vector: 1D numpy array of shape (dimension,)
            modality: "image" or "text"
            top_k: Number of top results to return
            candidate_ids: Optional subset of IDs (e.g. after price/category filtering)
            
        Returns:
            List of (item_id, similarity_score) sorted descending by score.
        """
        matrix = self.image_embeddings if modality == "image" else self.text_embeddings
        if matrix is None:
            raise ValueError(f"No embeddings loaded for modality: {modality}")

        # Ensure query is 1D and normalized
        q = np.squeeze(np.array(query_vector, dtype=np.float32))
        q_norm = np.linalg.norm(q)
        if q_norm > 1e-6:
            q = q / q_norm

        if candidate_ids is not None:
            # Filter to specific candidates
            valid_indices = [self.id_to_index[cid] for cid in candidate_ids if cid in self.id_to_index]
            if not valid_indices:
                return []
            sub_matrix = matrix[valid_indices]
            sub_ids = [self.index_to_id[idx] for idx in valid_indices]
            sims = np.dot(sub_matrix, q)
            top_indices = np.argsort(-sims)[:top_k]
            return [(sub_ids[i], float(sims[i])) for i in top_indices]
        else:
            sims = np.dot(matrix, q)
            top_indices = np.argsort(-sims)[:top_k]
            return [(self.index_to_id[i], float(sims[i])) for i in top_indices]

