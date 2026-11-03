"""Evaluation tests for retrieval metrics."""

from procurement_ai.evaluation.retrieval_eval import (
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


class TestRetrievalMetrics:
    def test_recall_at_k(self):
        retrieved = ["doc-1", "doc-2", "doc-3"]
        relevant = ["doc-1", "doc-2"]
        assert recall_at_k(retrieved, relevant, 3) == 1.0

    def test_recall_at_k_partial(self):
        retrieved = ["doc-1", "doc-3"]
        relevant = ["doc-1", "doc-2"]
        assert recall_at_k(retrieved, relevant, 2) == 0.5

    def test_precision_at_k(self):
        retrieved = ["doc-1", "doc-2", "doc-3"]
        relevant = ["doc-1", "doc-2"]
        assert abs(precision_at_k(retrieved, relevant, 3) - 2 / 3) < 0.01

    def test_mrr_first_rank(self):
        retrieved = ["doc-1", "doc-2"]
        relevant = ["doc-1"]
        assert mean_reciprocal_rank(retrieved, relevant) == 1.0

    def test_mrr_second_rank(self):
        retrieved = ["doc-3", "doc-1"]
        relevant = ["doc-1"]
        assert mean_reciprocal_rank(retrieved, relevant) == 0.5

    def test_ndcg_perfect(self):
        retrieved = ["doc-1", "doc-2"]
        relevant = ["doc-1", "doc-2"]
        assert ndcg_at_k(retrieved, relevant, 2) == 1.0
