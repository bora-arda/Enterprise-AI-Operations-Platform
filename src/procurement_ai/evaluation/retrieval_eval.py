"""Retrieval evaluation metrics."""

import logging

logger = logging.getLogger(__name__)


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Compute Recall@K."""
    if not relevant:
        return 0.0
    retrieved_k = set(retrieved[:k])
    relevant_set = set(relevant)
    return len(retrieved_k & relevant_set) / len(relevant_set)


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Compute Precision@K."""
    if not retrieved:
        return 0.0
    retrieved_k = set(retrieved[:k])
    relevant_set = set(relevant)
    return len(retrieved_k & relevant_set) / len(retrieved_k)


def mean_reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    """Compute Mean Reciprocal Rank."""
    for i, doc in enumerate(retrieved, 1):
        if doc in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Compute Normalized Discounted Cumulative Gain@K."""
    import math

    dcg = 0.0
    for i, doc in enumerate(retrieved[:k], 1):
        if doc in relevant:
            dcg += 1.0 / math.log2(i + 1)

    ideal_dcg = 0.0
    for i in range(min(len(relevant), k)):
        ideal_dcg += 1.0 / math.log2(i + 2)

    return dcg / ideal_dcg if ideal_dcg > 0 else 0.0


def evaluate_retrieval(
    benchmark: list[dict],
    retrieval_results: dict[str, list[str]],
) -> dict[str, float]:
    """Evaluate retrieval performance against a benchmark."""
    recalls = []
    precisions = []
    mrrs = []
    ndcgs = []

    for item in benchmark:
        query_id = item.get("metadata", {}).get("document_id")
        relevant = item.get("expected_sources", [])
        retrieved = retrieval_results.get(query_id, [])

        if relevant:
            recalls.append(recall_at_k(retrieved, relevant, 5))
            precisions.append(precision_at_k(retrieved, relevant, 5))
            mrrs.append(mean_reciprocal_rank(retrieved, relevant))
            ndcgs.append(ndcg_at_k(retrieved, relevant, 5))

    n = len(recalls)
    return {
        "recall@5": sum(recalls) / n if n > 0 else 0.0,
        "precision@5": sum(precisions) / n if n > 0 else 0.0,
        "mrr": sum(mrrs) / n if n > 0 else 0.0,
        "ndcg@5": sum(ndcgs) / n if n > 0 else 0.0,
        "total_queries": n,
    }
