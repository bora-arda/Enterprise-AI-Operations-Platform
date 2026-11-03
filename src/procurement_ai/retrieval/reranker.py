"""Cross-encoder reranking for retrieval results."""

import logging

from sentence_transformers import CrossEncoder

from procurement_ai.config.settings import get_settings

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder reranker."""

    def __init__(self):
        settings = get_settings()
        self.model_name = settings.reranking_model
        self._model: CrossEncoder | None = None

    def _get_model(self) -> CrossEncoder:
        if self._model is None:
            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, query: str, documents: list[dict], top_n: int = 5) -> list[dict]:
        """Rerank documents by relevance to the query."""
        if not documents:
            return []

        model = self._get_model()

        # Create pairs for cross-encoder
        pairs = [(query, doc["content"]) for doc in documents]

        # Score
        scores = model.predict(pairs)

        # Sort by score
        scored_docs = list(zip(documents, scores, strict=False))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc, score in scored_docs[:top_n]:
            results.append(
                {
                    "document": doc,
                    "score": float(score),
                    "rank": len(results) + 1,
                }
            )

        return results
