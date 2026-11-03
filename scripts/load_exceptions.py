#!/usr/bin/env python3
"""
Load anomaly ground truth into the exceptions table.
"""

import argparse
import json
import logging
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Load anomaly ground truth as exceptions")
    parser.add_argument(
        "--database-url",
        default="postgresql+psycopg2://user:pass@localhost:5432/procurement",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/evaluation/anomaly_ground_truth.json"),
    )
    args = parser.parse_args()

    if not args.input.exists():
        logger.error(f"Ground truth file not found: {args.input}")
        sys.exit(1)

    with open(args.input) as f:
        ground_truth = json.load(f)

    logger.info(f"Loading {len(ground_truth)} exceptions")

    from procurement_ai.database.models import Exception as ExceptionModel

    engine = create_engine(args.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        loaded = 0
        skipped = 0
        for item in ground_truth:
            invoice_id = item.get("invoice_id") or item.get("original_invoice_id")
            if not invoice_id and item.get("entity_type") == "invoice":
                invoice_id = item.get("entity_id")

            if not invoice_id:
                skipped += 1
                continue

            try:
                invoice_uuid = uuid.UUID(str(invoice_id))
            except (ValueError, AttributeError):
                skipped += 1
                continue

            row = ExceptionModel(
                id=uuid.uuid4(),
                invoice_id=invoice_uuid,
                exception_type=item.get("anomaly_type", "unknown"),
                severity=item.get("severity", "medium"),
                description=item.get("description", ""),
                status="open",
                detected_at=datetime.now(UTC),
            )
            session.add(row)
            loaded += 1

        session.commit()
        logger.info(f"Loaded {loaded} exceptions (skipped {skipped})")

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to load exceptions: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
