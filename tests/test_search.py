"""
Unit tests for backend/search.py and compute_relevance.
"""

import unittest
from backend.schemas import Product, SearchFilters, SearchRequest
from backend.search import compute_relevance, search_products


class TestSearchRelevance(unittest.TestCase):
    def setUp(self):
        self.products = [
            Product(
                product_id="p-001",
                name="黑色日系寬鬆襯衫",
                category="top",
                price=790,
                colors=["black"],
                styles=["japanese", "casual"],
                fit="relaxed",
                source="test",
                search_text="黑色 日系 寬鬆 襯衫",
            ),
            Product(
                product_id="p-002",
                name="炭灰工裝短褲",
                category="bottom",
                price=890,
                colors=["charcoal"],
                styles=["outdoor", "casual"],
                fit="relaxed",
                source="test",
                search_text="炭灰 工裝 短褲 戶外",
            ),
            Product(
                product_id="p-003",
                name="米色極簡針織上衣",
                category="top",
                price=1200,
                colors=["beige"],
                styles=["minimal"],
                fit="regular",
                source="test",
                search_text="米色 極簡 針織 上衣",
            ),
        ]

    def test_text_relevance(self):
        scores = compute_relevance(
            query_text="黑色 日系 襯衫",
            candidates=self.products,
            mode="text",
        )
        self.assertEqual(len(scores), 3)
        self.assertIn("p-001", scores)
        # p-001 should have the highest relevance for "黑色 日系 襯衫"
        self.assertGreater(scores["p-001"], scores["p-003"])
        for pid, score in scores.items():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_mixed_rrf_relevance(self):
        scores = compute_relevance(
            query_text="工裝 戶外",
            query_image=None,
            candidates=self.products,
            mode="mixed",
            image_weight=0.5,
        )
        self.assertEqual(len(scores), 3)
        for pid, score in scores.items():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_search_products_response(self):
        req = SearchRequest(
            session_id="test-session",
            query_text="日系",
            mode="text",
            filters=SearchFilters(categories=["top"]),
            limit=2,
        )
        catalog = [p for p in self.products if p.category == "top"]
        resp = search_products(req, catalog)

        self.assertEqual(resp.session_id, "test-session")
        self.assertEqual(resp.mode, "text")
        self.assertTrue(len(resp.products) <= 2)
        # Hits must be sorted descending by relevance score
        for i in range(len(resp.products) - 1):
            self.assertGreaterEqual(resp.products[i].score, resp.products[i + 1].score)
            self.assertIn("relevance", resp.products[i].score_breakdown)

    def test_filter_only_browse_does_not_need_an_embedding_query(self):
        req = SearchRequest(
            session_id="test-session",
            query_text="",
            mode="text",
            filters=SearchFilters(categories=["top"]),
            limit=10,
        )
        catalog = [p for p in self.products if p.category == "top"]
        resp = search_products(req, catalog)

        self.assertEqual(resp.retrieval.fusion_method, "filters_only")
        self.assertEqual([hit.product_id for hit in resp.products], ["p-001", "p-003"])
        self.assertTrue(all(hit.score == 0 for hit in resp.products))


if __name__ == "__main__":
    unittest.main()
