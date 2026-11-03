#!/usr/bin/env python3
"""
Load synthetic documents into the documents table for retrieval.

Loads lightweight document types (policies, emails, operational notes) so
retrieval works without embedding hundreds of thousands of contract chunks.
"""

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Document types to load by default (skip huge contract/invoice/PO corpora)
DEFAULT_TYPES = {"policy", "email", "operational_note"}


def parse_date(value):
    if not value:
        return None
    try:
        from datetime import date

        return date.fromisoformat(str(value).split("T")[0])
    except (ValueError, IndexError):
        return None


def main():
    parser = argparse.ArgumentParser(description="Load documents into PostgreSQL")
    parser.add_argument(
        "--database-url",
        default="postgresql+psycopg2://user:pass@localhost:5432/procurement",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/documents/documents.json"),
    )
    parser.add_argument(
        "--types",
        default="policy,email,operational_note",
        help="Comma-separated document types to load",
    )
    parser.add_argument("--limit-per-type", type=int, default=None)
    args = parser.parse_args()

    if not args.input.exists():
        logger.error(f"Documents file not found: {args.input}")
        sys.exit(1)

    with open(args.input) as f:
        documents = json.load(f)

    allowed_types = {t.strip() for t in args.types.split(",")}
    filtered = [d for d in documents if d.get("document_type") in allowed_types]

    if args.limit_per_type:
        by_type: dict[str, list[dict]] = {}
        for doc in filtered:
            by_type.setdefault(doc["document_type"], []).append(doc)
        filtered = []
        for doc_type, docs in by_type.items():
            filtered.extend(docs[: args.limit_per_type])

    logger.info(f"Loading {len(filtered)} documents (types: {sorted(allowed_types)})")

    from procurement_ai.database.models import Document

    engine = create_engine(args.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        loaded = 0
        for doc in filtered:
            row = Document(
                id=uuid.uuid4(),
                document_id=str(doc.get("id", uuid.uuid4().hex))[:100],
                document_type=doc.get("document_type"),
                title=(doc.get("title") or "")[:500] or None,
                content=doc.get("content"),
                vendor_id=None,
                contract_id=None,
                invoice_id=None,
                po_id=None,
                department=doc.get("department"),
                effective_date=parse_date(doc.get("effective_date")),
                expiration_date=parse_date(doc.get("expiration_date")),
                source=doc.get("source", "synthetic"),
                doc_metadata=doc.get("metadata"),
            )
            session.add(row)
            loaded += 1

        session.commit()
        logger.info(f"Loaded {loaded} documents into the documents table")

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to load documents: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
