"""Dense vector search using pgvector."""

import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def dense_search(
    session: AsyncSession,
    query_embedding: list[float],
    top_k: int = 20,
    filters: dict | None = None,
) -> list[dict]:
    """
    Execute dense vector search using pgvector.

    Args:
        session: Database session
        query_embedding: Query embedding vector
        top_k: Number of results to return
        filters: Optional metadata filters

    Returns:
        List of search results with scores
    """
    # Build WHERE clause from filters
    where_clauses = []
    params = {"query_embedding": str(query_embedding), "top_k": top_k}

    if filters:
        for key, value in filters.items():
            where_clauses.append(f"metadata->>'{key}' = :filter_{key}")
            params[f"filter_{key}"] = str(value)

    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

    sql = f"""
        SELECT
            document_id,
            document_type,
            title,
            content,
            metadata,
            1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity
        FROM documents
        WHERE {where_clause}
        ORDER BY embedding <=> CAST(:query_embedding AS vector)
        LIMIT :top_k
    """

    result = await session.execute(text(sql), params)
    rows = result.mappings().all()

    results = []
    for row in rows:
        results.append(
            {
                "document": {
                    "id": row["document_id"],
                    "document_type": row["document_type"],
                    "title": row["title"],
                    "content": row["content"],
                    "metadata": row["metadata"],
                },
                "score": float(row["similarity"]),
                "rank": len(results) + 1,
            }
        )

    return results


async def insert_document_embedding(
    session: AsyncSession,
    document_id: str,
    document_type: str,
    title: str,
    content: str,
    embedding: list[float],
    metadata: dict | None = None,
) -> None:
    """Insert a document with its embedding into the database."""
    sql = """
        INSERT INTO documents (document_id, document_type, title, content, embedding, metadata)
        VALUES (:document_id, :document_type, :title, :content,
                CAST(:embedding AS vector), CAST(:metadata AS jsonb))
        ON CONFLICT (document_id) DO UPDATE SET
            content = EXCLUDED.content,
            embedding = EXCLUDED.embedding,
            metadata = EXCLUDED.metadata
    """

    await session.execute(
        text(sql),
        {
            "document_id": document_id,
            "document_type": document_type,
            "title": title,
            "content": content,
            "embedding": str(embedding),
            "metadata": json.dumps(metadata) if metadata else None,
        },
    )
