"""BM25 index for full-text search."""

import logging
import pickle
from pathlib import Path

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class BM25Index:
    """BM25 index for document retrieval."""

    def __init__(self):
        self.index: BM25Okapi | None = None
        self.documents: list[dict] = []
        self.tokenized_docs: list[list[str]] = []

    def build(self, documents: list[dict]) -> None:
        """Build the BM25 index from documents."""
        self.documents = documents
        self.tokenized_docs = [self._tokenize(doc["content"]) for doc in documents]
        self.index = BM25Okapi(self.tokenized_docs)
        logger.info(f"Built BM25 index with {len(documents)} documents")

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        """Search the index and return top-k results."""
        if not self.index:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.index.get_scores(tokenized_query)

        # Get top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append(
                    {
                        "document": self.documents[idx],
                        "score": float(scores[idx]),
                        "rank": len(results) + 1,
                    }
                )

        return results

    def save(self, path: Path) -> None:
        """Save the index to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"documents": self.documents, "tokenized_docs": self.tokenized_docs}, f)
        logger.info(f"Saved BM25 index to {path}")

    def load(self, path: Path) -> None:
        """Load the index from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.documents = data["documents"]
        self.tokenized_docs = data["tokenized_docs"]
        self.index = BM25Okapi(self.tokenized_docs)
        logger.info(f"Loaded BM25 index from {path} ({len(self.documents)} documents)")

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple tokenization for BM25."""
        return text.lower().split()
