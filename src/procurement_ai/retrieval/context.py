"""Context selection and formatting for LLM consumption."""

import logging

logger = logging.getLogger(__name__)


def select_context(
    results: list[dict],
    max_tokens: int = 4000,
    max_chunks: int = 10,
    diversity_threshold: float = 0.85,
) -> list[dict]:
    """
    Select and format context for LLM consumption.

    Args:
        results: Reranked search results
        max_tokens: Maximum total tokens
        max_chunks: Maximum number of chunks
        diversity_threshold: Minimum diversity between chunks

    Returns:
        Selected context chunks
    """
    selected = []
    total_tokens = 0

    for result in results:
        if len(selected) >= max_chunks:
            break

        content = result.get("document", {}).get("content", "")
        # Rough token estimate: ~4 chars per token
        token_estimate = len(content) // 4

        if total_tokens + token_estimate > max_tokens:
            break

        # Simple diversity check (skip if too similar to already selected)
        if selected and _similarity(content, selected[-1].get("content", "")) > diversity_threshold:
            continue

        selected.append(
            {
                "source": result.get("document", {}).get("id", "unknown"),
                "content": content,
                "score": result.get("score", 0),
            }
        )
        total_tokens += token_estimate

    return selected


def format_context(context: list[dict]) -> str:
    """Format context chunks for LLM prompt."""
    formatted = []
    for i, chunk in enumerate(context, 1):
        formatted.append(f"[Source {i}: {chunk['source']}]\n{chunk['content']}")
    return "\n\n---\n\n".join(formatted)


def _similarity(text1: str, text2: str) -> float:
    """Simple word overlap similarity."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0.0
    return len(words1 & words2) / len(words1 | words2)
