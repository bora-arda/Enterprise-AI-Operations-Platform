#!/usr/bin/env python3
"""
Build embeddings for the document corpus and store them in pgvector.

Steps:
1. Insert contract-summary documents derived from the contracts table
   (so retrieval covers more than policies/emails/notes).
2. Encode every document with a NULL embedding and update pgvector.

Uses a local sentence-transformers model by default (all-MiniLM-L6-v2, 384 dims).
"""

import argparse
import logging
import sys
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def build_contract_summaries(session, limit: int) -> int:
    """Insert contract-summary documents for retrieval."""
    from procurement_ai.database.models import Document

    if limit <= 0:
        return 0

    rows = (
        session.execute(
            text(
                """
            SELECT c.id, c.contract_number, c.title, c.description, c.value,
                   c.max_value, c.currency, c.start_date, c.end_date,
                   c.category_description, c.vendor_id, c.buyer_id
            FROM contracts c
            WHERE c.title IS NOT NULL AND c.description IS NOT NULL
            ORDER BY c.contract_number
            LIMIT :limit
            """
            ),
            {"limit": limit},
        )
        .mappings()
        .all()
    )

    inserted = 0
    for row in rows:
        document_id = f"CONTRACT-SUMMARY-{row['contract_number']}"[:100]
        exists = session.execute(
            text("SELECT 1 FROM documents WHERE document_id = :document_id"),
            {"document_id": document_id},
        ).first()
        if exists:
            continue

        content = (
            f"Contract {row['contract_number']}: {row['title']}\n"
            f"Value: {row['currency'] or 'GBP'} {float(row['value'] or 0):,.2f} "
            f"(maximum {float(row['max_value'] or 0):,.2f})\n"
            f"Period: {row['start_date']} to {row['end_date']}\n"
            f"Category: {row['category_description'] or 'N/A'}\n\n"
            f"Description: {(row['description'] or '')[:1000]}"
        )

        session.add(
            Document(
                id=uuid.uuid4(),
                document_id=document_id,
                document_type="contract_summary",
                title=f"Contract summary: {row['title']}"[:500],
                content=content,
                vendor_id=str(row["vendor_id"]) if row["vendor_id"] else None,
                contract_id=str(row["id"]),
                effective_date=row["start_date"],
                expiration_date=row["end_date"],
                source="synthetic",
                doc_metadata={
                    "contract_number": row["contract_number"],
                    "value": float(row["value"]) if row["value"] else None,
                    "currency": row["currency"],
                },
            )
        )
        inserted += 1

    session.commit()
    logger.info(f"Inserted {inserted} contract-summary documents")
    return inserted


def embed_documents(session, model_name: str, batch_size: int) -> int:
    """Compute embeddings for documents that do not have one."""
    from sentence_transformers import SentenceTransformer

    docs = (
        session.execute(
            text(
                """
            SELECT id, document_id, content
            FROM documents
            WHERE embedding IS NULL AND content IS NOT NULL
            ORDER BY created_at
            """
            )
        )
        .mappings()
        .all()
    )

    if not docs:
        logger.info("All documents already have embeddings")
        return 0

    logger.info(f"Encoding {len(docs)} documents with {model_name}")
    model = SentenceTransformer(model_name)

    updated = 0
    for start in range(0, len(docs), batch_size):
        batch = docs[start : start + batch_size]
        vectors = model.encode([row["content"] for row in batch], show_progress_bar=False)

        for row, vector in zip(batch, vectors, strict=False):
            values = "[" + ",".join(f"{float(v):.6f}" for v in vector) + "]"
            session.execute(
                text("UPDATE documents SET embedding = CAST(:emb AS vector) WHERE id = :id"),
                {"emb": values, "id": row["id"]},
            )
            updated += 1

        session.commit()
        logger.info(f"Embedded {min(start + batch_size, len(docs))}/{len(docs)}")

    return updated


def main():
    parser = argparse.ArgumentParser(description="Build document embeddings")
    parser.add_argument(
        "--database-url",
        default="postgresql+psycopg2://user:pass@localhost:5432/procurement",
    )
    parser.add_argument("--model", default="all-MiniLM-L6-v2")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument(
        "--contracts",
        type=int,
        default=200,
        help="Number of contract summary documents to add (0 to skip)",
    )
    args = parser.parse_args()

    engine = create_engine(args.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        build_contract_summaries(session, args.contracts)
        count = embed_documents(session, args.model, args.batch_size)
        logger.info(f"Done. Embedded {count} documents.")
    except Exception as e:
        session.rollback()
        logger.error(f"Embedding build failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
