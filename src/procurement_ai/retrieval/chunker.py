"""Document chunking strategies."""

import logging
import re
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Chunker(ABC):
    """Abstract base class for document chunkers."""

    @abstractmethod
    def chunk(self, text: str, metadata: dict | None = None) -> list[dict]:
        pass


class RecursiveChunker(Chunker):
    """Recursive character-based chunker."""

    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, metadata: dict | None = None) -> list[dict]:
        if not text:
            return []

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            # Try to break at a sentence boundary
            if end < len(text):
                last_period = chunk_text.rfind(". ")
                if last_period > self.chunk_size * 0.5:
                    end = start + last_period + 1
                    chunk_text = text[start:end]

            chunks.append(
                {
                    "content": chunk_text.strip(),
                    "metadata": metadata or {},
                    "start_char": start,
                    "end_char": end,
                }
            )

            start = end - self.chunk_overlap

        return chunks


class SectionChunker(Chunker):
    """Section-based chunker for contracts and policies."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, metadata: dict | None = None) -> list[dict]:
        if not text:
            return []

        # Split by section headers (numbered sections, ALL CAPS, etc.)
        sections = re.split(r"\n(?=\d+\.\s+[A-Z]|[A-Z][A-Z\s]{3,})", text)

        chunks = []
        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Further split long sections
            if len(section) > self.chunk_size:
                sub_chunks = RecursiveChunker(self.chunk_size, self.chunk_overlap).chunk(section, metadata)
                chunks.extend(sub_chunks)
            else:
                chunks.append(
                    {
                        "content": section,
                        "metadata": metadata or {},
                    }
                )

        return chunks


def get_chunker(document_type: str) -> Chunker:
    """Get the appropriate chunker for a document type."""
    if document_type in ("contract", "policy"):
        return SectionChunker()
    else:
        return RecursiveChunker()
