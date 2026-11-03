"""Unit tests for retrieval components."""

from procurement_ai.retrieval.chunker import RecursiveChunker, SectionChunker
from procurement_ai.retrieval.context import format_context, select_context
from procurement_ai.retrieval.fusion import reciprocal_rank_fusion


class TestChunker:
    def test_recursive_chunker(self):
        chunker = RecursiveChunker(chunk_size=100, chunk_overlap=20)
        text = "This is a test document. " * 20
        chunks = chunker.chunk(text)
        assert len(chunks) > 0
        assert all("content" in c for c in chunks)

    def test_section_chunker(self):
        chunker = SectionChunker()
        text = "1. Section One\nContent here.\n2. Section Two\nMore content."
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2


class TestFusion:
    def test_reciprocal_rank_fusion(self):
        bm25_results = [
            {"document": {"id": "doc-1"}, "score": 10.0},
            {"document": {"id": "doc-2"}, "score": 8.0},
        ]
        dense_results = [
            {"document": {"id": "doc-2"}, "score": 0.9},
            {"document": {"id": "doc-3"}, "score": 0.8},
        ]
        fused = reciprocal_rank_fusion(bm25_results, dense_results)
        assert len(fused) == 3
        assert fused[0]["document"]["id"] == "doc-2"


class TestContext:
    def test_select_context(self):
        results = [
            {
                "document": {"id": f"doc-{i}", "content": f"Content {i}" * 100},
                "score": 1.0 - i * 0.1,
            }
            for i in range(5)
        ]
        context = select_context(results, max_tokens=1000, max_chunks=3)
        assert len(context) <= 3

    def test_format_context(self):
        context = [{"source": "doc-1", "content": "Test content"}]
        formatted = format_context(context)
        assert "doc-1" in formatted
        assert "Test content" in formatted
