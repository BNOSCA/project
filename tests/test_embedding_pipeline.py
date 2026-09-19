"""
Unit tests for FashionCLIP embedding pipeline and EmbeddingStore.
Pure unittest implementation without third-party test runners.
"""

import json
import tempfile
import unittest
from pathlib import Path
import numpy as np

from scripts.sample_data import create_sample_dataset
from scripts.build_embeddings import run_pipeline
from scripts.embedding_store import EmbeddingStore


class TestEmbeddingPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.data_dir = self.base_path / "data"
        create_sample_dataset(self.data_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pipeline_and_store(self):
        data_file = self.data_dir / "products.json"
        output_dir = self.base_path / "embeddings"

        # 1. Run pipeline in mock mode
        run_pipeline(
            input_file=data_file,
            output_dir=output_dir,
            id_field="product_id",
            image_field="image_url",
            text_field="search_text",
            image_dir=self.data_dir / "sample_images",
            batch_size=4,
            modality="all",
            mock=True,
        )

        # 2. Verify generated files exist
        self.assertTrue((output_dir / "image_embeddings.npy").is_file())
        self.assertTrue((output_dir / "text_embeddings.npy").is_file())
        self.assertTrue((output_dir / "id_mapping.json").is_file())
        self.assertTrue((output_dir / "products_with_embeddings.json").is_file())

        # 3. Verify numpy shapes and L2 normalization
        img_vecs = np.load(output_dir / "image_embeddings.npy")
        txt_vecs = np.load(output_dir / "text_embeddings.npy")

        with open(data_file, "r", encoding="utf-8") as f:
            items = json.load(f)
        num_items = len(items)

        self.assertEqual(img_vecs.shape, (num_items, 512))
        self.assertEqual(txt_vecs.shape, (num_items, 512))

        # Check L2 normalization: norm should be approximately 1.0
        img_norms = np.linalg.norm(img_vecs, axis=-1)
        txt_norms = np.linalg.norm(txt_vecs, axis=-1)
        np.testing.assert_allclose(img_norms, 1.0, atol=1e-4)
        np.testing.assert_allclose(txt_norms, 1.0, atol=1e-4)

        # 4. Verify EmbeddingStore loading and search
        store = EmbeddingStore.load(output_dir)
        self.assertTrue(store.contains("p-top-001"))
        self.assertFalse(store.contains("non-existent-id"))

        v1 = store.get_image_vector("p-top-001")
        self.assertIsNotNone(v1)
        self.assertEqual(v1.shape, (512,))

        # Search against own vector should return itself as top 1 with similarity ~1.0
        results = store.search(v1, modality="image", top_k=3)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0][0], "p-top-001")
        self.assertAlmostEqual(results[0][1], 1.0, places=4)

        # Search with candidate filtering
        filtered_results = store.search(
            v1, modality="image", top_k=5, candidate_ids=["p-top-002", "p-bottom-001"]
        )
        self.assertEqual(len(filtered_results), 2)
        returned_ids = [r[0] for r in filtered_results]
        self.assertNotIn("p-top-001", returned_ids)
        self.assertIn("p-top-002", returned_ids)


if __name__ == "__main__":
    unittest.main()
