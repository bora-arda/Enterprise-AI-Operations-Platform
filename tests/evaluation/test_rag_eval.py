"""Evaluation tests for RAG metrics."""

from procurement_ai.evaluation.rag_eval import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)


class TestRAGMetrics:
    def test_faithfulness_perfect(self):
        answer = "Invoice INV-001 is overdue"
        context = "Invoice INV-001 is overdue because payment was not received"
        score = faithfulness(answer, context)
        assert score > 0.5

    def test_faithfulness_low(self):
        answer = "The sky is blue"
        context = "Invoice INV-001 is overdue"
        score = faithfulness(answer, context)
        assert score < 0.5

    def test_answer_relevancy(self):
        question = "Why is INV-001 overdue?"
        answer = "Invoice INV-001 is overdue because payment was not received"
        score = answer_relevancy(question, answer)
        assert score > 0.3

    def test_context_precision(self):
        retrieved = ["chunk-1", "chunk-2", "chunk-3"]
        relevant = ["chunk-1", "chunk-2"]
        assert abs(context_precision(retrieved, relevant) - 2 / 3) < 0.01

    def test_context_recall(self):
        retrieved = ["chunk-1"]
        relevant = ["chunk-1", "chunk-2"]
        assert context_recall(retrieved, relevant) == 0.5
