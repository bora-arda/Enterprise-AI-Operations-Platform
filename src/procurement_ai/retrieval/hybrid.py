"""Hybrid retrieval: BM25 + dense vectors + reciprocal rank fusion.

The dense leg uses pgvector cosine similarity over the documents table.
If embeddings are unavailable (or the model cannot load), the pipeline
degrades gracefully to BM25-only results.
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from procurement_ai.config.settings import get_settings
from procurement_ai.database.models import Document
from procurement_ai.models.embeddings import get_embeddings
from procurement_ai.retrieval.bm25 import BM25Index
from procurement_ai.retrieval.dense import dense_search
from procurement_ai.retrieval.fusion import reciprocal_rank_fusion

logger = logging.getLogger(__name__)


def _to_doc(doc: Document) -> dict:
    return {
        "id": doc.document_id,
        "content": doc.content or "",
        "title": doc.title or doc.document_id,
        "document_type": doc.document_type or "document",
        "metadata": doc.doc_metadata or {},
    }


async def hybrid_search(
    session: AsyncSession,
    query: str,
    top_k: int = 5,
    candidate_k: int = 20,
) -> list[dict]:
    """Run hybrid BM25 + dense retrieval and fuse the rankings."""
    settings = get_settings()

    result = await session.execute(select(Document).where(Document.content.isnot(None)))
    documents = list(result.scalars().all())
    if not documents:
        return []

    docs = [_to_doc(d) for d in documents]

    # BM25 leg
    bm25 = BM25Index()
    bm25.build(docs)
    bm25_results = bm25.search(query, top_k=candidate_k)

    # Dense leg (best-effort)
    dense_results: list[dict] = []
    try:
        embeddings = get_embeddings()
        query_vector = await asyncio.to_thread(embeddings.embed_query, query)
        dense_results = await dense_search(session, query_vector, top_k=candidate_k)
    except Exception as e:
        logger.warning(f"Dense retrieval unavailable, using BM25 only: {e}")

    fused = reciprocal_rank_fusion(bm25_results, dense_results, k=60)
    if not fused:
        return []

    # Optional cross-encoder reranking
    if settings.reranking_enabled:
        try:
            from procurement_ai.retrieval.reranker import Reranker

            candidates = [r["document"] for r in fused[:candidate_k]]
            reranker = Reranker()
            reranked = await asyncio.to_thread(reranker.rerank, query, candidates, top_k)
            fused = reranked
        except Exception as e:
            logger.warning(f"Reranking unavailable, using fused order: {e}")

    results = []
    for item in fused[:top_k]:
        doc = item["document"]
        results.append(
            {
                "source": f"{doc.get('document_type', 'document')}:{doc.get('id')}",
                "content": doc.get("content", ""),
                "title": doc.get("title", doc.get("id", "")),
                "score": float(item.get("score", 0.0)),
                "document_type": doc.get("document_type", "document"),
                "metadata": doc.get("metadata", {}),
            }
        )
    return results
