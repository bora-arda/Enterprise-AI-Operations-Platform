"""Retrieval workflow node.

Uses hybrid retrieval (BM25 + dense pgvector + reciprocal rank fusion) with an
optional cross-encoder. Falls back to keyword scoring if the embedding model or
vector search is unavailable.
"""

import logging
import re

from sqlalchemy import select

from procurement_ai.database.connection import AsyncSessionLocal
from procurement_ai.database.models import Document
from procurement_ai.retrieval.hybrid import hybrid_search

logger = logging.getLogger(__name__)

STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "of",
    "for",
    "to",
    "in",
    "on",
    "at",
    "by",
    "with",
    "and",
    "or",
    "what",
    "which",
    "who",
    "how",
    "why",
    "does",
    "do",
    "did",
    "can",
    "could",
    "should",
    "would",
    "please",
    "me",
    "show",
    "tell",
    "about",
    "our",
    "we",
    "i",
    "it",
    "this",
    "that",
    "new",
    "need",
    "want",
    "like",
    "there",
    "have",
    "has",
    "get",
}


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9][a-z0-9-]{2,}", text.lower())
    return [w for w in words if w not in STOPWORDS]


def _stem(word: str) -> str:
    return word[:6] if len(word) > 7 else word


def _score_document(content: str, keywords: list[str]) -> int:
    content_lower = content.lower()
    return sum(content_lower.count(_stem(kw)) for kw in keywords)


def _best_excerpt(content: str, keywords: list[str], max_chars: int = 1200) -> str:
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if not paragraphs:
        return content[:max_chars]
    relevant = max(paragraphs, key=lambda p: _score_document(p, keywords))
    return relevant[:max_chars]


async def _keyword_fallback(question: str, top_n: int = 3) -> list[dict]:
    """Keyword-scored fallback when hybrid retrieval is unavailable."""
    keywords = _keywords(question)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Document).limit(500))
        documents = list(result.scalars().all())

    scored = []
    for doc in documents:
        score = _score_document(doc.content or "", keywords)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, doc in scored[:top_n]:
        results.append(
            {
                "source": f"{doc.document_type}:{doc.document_id}",
                "content": doc.content or "",
                "title": doc.title or doc.document_id,
                "score": float(score),
                "document_type": doc.document_type or "document",
                "metadata": doc.doc_metadata or {},
            }
        )
    return results


async def retrieval_workflow_node(state: dict) -> dict:
    """Search documents and answer from retrieved evidence."""
    question = state.get("user_input", "")
    keywords = _keywords(question)

    if not keywords:
        state["response"] = "Could you rephrase your question with more specific terms?"
        return state

    # Structured entity lookup first (invoice, PO, contract, vendor, payment,
    # approval). Transactional data is queried live, never embedded.
    try:
        from procurement_ai.graph.nodes.entity_lookup import lookup_entity

        entity = await lookup_entity(state, question)
    except Exception as e:
        logger.warning(f"Entity lookup failed, continuing to documents: {e}")
        entity = None

    if entity is not None:
        state["response"] = entity.response
        state["citations"] = entity.citations
        state["evidence"] = entity.evidence
        state["confidence"] = 0.9 if entity.citations else 0.5
        state["workflow"] = "retrieval"
        if entity.invoice_number:
            state["last_invoice_number"] = entity.invoice_number
        return state

    results: list[dict] = []
    try:
        async with AsyncSessionLocal() as session:
            results = await hybrid_search(session, question, top_k=3)
    except Exception as e:
        logger.warning(f"Hybrid retrieval failed, falling back to keywords: {e}")

    if not results:
        try:
            results = await _keyword_fallback(question, top_n=3)
        except Exception as e:
            logger.error(f"Keyword retrieval failed: {e}", exc_info=True)
            state["response"] = "I encountered an error while searching documents."
            state["errors"] = state.get("errors", []) + [str(e)]
            return state

    if not results:
        state["response"] = (
            "I couldn't find relevant documents for that question. "
            "Try asking about procurement policies, approval rules, or payment terms."
        )
        state["confidence"] = 0.3
        state["workflow"] = "retrieval"
        return state

    best = results[0]
    excerpt = _best_excerpt(best["content"], keywords)

    sources = ", ".join(r["source"] for r in results[:3])
    response = f"Based on {best['title']}:\n\n{excerpt}\n\nSources: {sources}"

    state["response"] = response
    state["citations"] = [
        {
            "source": r["source"],
            "snippet": (r["content"] or "")[:300].replace("\n", " ").strip(),
        }
        for r in results[:3]
    ]
    state["evidence"] = [
        {
            "source": r["source"],
            "content": r["content"],
            "metadata": r.get("metadata", {}),
        }
        for r in results[:3]
    ]
    state["confidence"] = 0.8
    state["workflow"] = "retrieval"
    return state
