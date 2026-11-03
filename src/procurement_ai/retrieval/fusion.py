"""Hybrid fusion strategies for combining BM25 and dense retrieval results."""

import logging

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    bm25_results: list[dict],
    dense_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """
    Reciprocal Rank Fusion (RRF) combines BM25 and dense retrieval results.

    RRF_score(d) = 1 / (k + rank_bm25(d)) + 1 / (k + rank_dense(d))
    """
    scores = {}
    doc_map = {}

    # Add BM25 scores
    for rank, result in enumerate(bm25_results, 1):
        doc_id = result["document"]["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
        doc_map[doc_id] = result["document"]

    # Add dense scores
    for rank, result in enumerate(dense_results, 1):
        doc_id = result["document"]["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
        doc_map[doc_id] = result["document"]

    # Sort by fused score
    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    fused_results = []
    for doc_id, score in sorted_docs:
        fused_results.append(
            {
                "document": doc_map[doc_id],
                "score": score,
                "rank": len(fused_results) + 1,
            }
        )

    return fused_results


def weighted_fusion(
    bm25_results: list[dict],
    dense_results: list[dict],
    bm25_weight: float = 0.5,
    dense_weight: float = 0.5,
) -> list[dict]:
    """Weighted score fusion."""
    scores = {}
    doc_map = {}

    max_bm25 = max((r["score"] for r in bm25_results), default=1.0)
    max_dense = max((r["score"] for r in dense_results), default=1.0)

    for result in bm25_results:
        doc_id = result["document"]["id"]
        normalized_score = result["score"] / max_bm25 if max_bm25 > 0 else 0
        scores[doc_id] = scores.get(doc_id, 0) + bm25_weight * normalized_score
        doc_map[doc_id] = result["document"]

    for result in dense_results:
        doc_id = result["document"]["id"]
        normalized_score = result["score"] / max_dense if max_dense > 0 else 0
        scores[doc_id] = scores.get(doc_id, 0) + dense_weight * normalized_score
        doc_map[doc_id] = result["document"]

    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    fused_results = []
    for doc_id, score in sorted_docs:
        fused_results.append(
            {
                "document": doc_map[doc_id],
                "score": score,
                "rank": len(fused_results) + 1,
            }
        )

    return fused_results
