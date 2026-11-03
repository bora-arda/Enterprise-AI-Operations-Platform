"""RAG evaluation metrics."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def faithfulness(answer: str, context: str) -> float:
    """
    Evaluate whether the answer is grounded in the context.
    Returns a score between 0 and 1.
    """
    # Placeholder: In production, use an NLI model or LLM judge
    # For now, use simple word overlap as a proxy
    answer_words = set(answer.lower().split())
    context_words = set(context.lower().split())

    if not answer_words:
        return 0.0

    overlap = len(answer_words & context_words) / len(answer_words)
    return overlap


def answer_relevancy(question: str, answer: str) -> float:
    """
    Evaluate whether the answer addresses the question.
    Returns a score between 0 and 1.
    """
    # Placeholder: In production, use an embedding-based relevance score
    question_words = set(question.lower().split())
    answer_words = set(answer.lower().split())

    if not question_words:
        return 0.0

    overlap = len(question_words & answer_words) / len(question_words)
    return overlap


def context_precision(retrieved_context: list[str], relevant_context: list[str]) -> float:
    """Compute context precision."""
    if not retrieved_context:
        return 0.0
    retrieved_set = set(retrieved_context)
    relevant_set = set(relevant_context)
    return len(retrieved_set & relevant_set) / len(retrieved_set)


def context_recall(retrieved_context: list[str], relevant_context: list[str]) -> float:
    """Compute context recall."""
    if not relevant_context:
        return 0.0
    retrieved_set = set(retrieved_context)
    relevant_set = set(relevant_context)
    return len(retrieved_set & relevant_set) / len(relevant_set)


def evaluate_rag(
    benchmark: list[dict],
    results: dict[str, dict[str, Any]],
) -> dict[str, float]:
    """Evaluate RAG performance against a benchmark."""
    faithfulness_scores = []
    relevancy_scores = []

    for item in benchmark:
        query_id = item.get("metadata", {}).get("document_id")
        question = item.get("query", "")
        result = results.get(query_id, {})
        answer = result.get("answer", "")
        context = " ".join(result.get("context", []))

        if answer:
            faithfulness_scores.append(faithfulness(answer, context))
            relevancy_scores.append(answer_relevancy(question, answer))

    n = len(faithfulness_scores)
    return {
        "faithfulness": sum(faithfulness_scores) / n if n > 0 else 0.0,
        "answer_relevancy": sum(relevancy_scores) / n if n > 0 else 0.0,
        "total_queries": n,
    }
