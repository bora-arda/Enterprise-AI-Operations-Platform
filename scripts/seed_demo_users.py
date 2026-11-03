#!/usr/bin/env python3
"""Seed deterministic demo users for local authentication."""

import argparse
import logging
import os
import sys
import uuid

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from procurement_ai.auth.security import hash_password
from procurement_ai.database.models import Department, User

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEMO_USERS = [
    ("specialist@example.com", "Alice Specialist", "specialist"),
    ("manager@example.com", "Maya Manager", "manager"),
    ("finance@example.com", "Frank Finance", "finance"),
    ("director@example.com", "Diana Director", "director"),
    ("admin@example.com", "Adam Admin", "admin"),
]


def main():
    parser = argparse.ArgumentParser(description="Seed demo auth users")
    parser.add_argument(
        "--database-url",
        default="postgresql+psycopg2://user:pass@localhost:5432/procurement",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("DEMO_PASSWORD", "demo123"),
        help="Password for all demo users",
    )
    args = parser.parse_args()

    engine = create_engine(args.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        department = session.execute(
            select(Department).where(Department.name.ilike("%procurement%")).limit(1)
        ).scalar_one_or_none()
        if department is None:
            department = session.execute(select(Department).limit(1)).scalar_one_or_none()

        password_hash = hash_password(args.password)

        for email, name, role in DEMO_USERS:
            existing = session.execute(
                select(User).where(text("lower(users.email) = :email")),
                {"email": email.lower()},
            ).scalar_one_or_none()

            if existing:
                existing.name = name
                existing.role = role
                existing.password_hash = password_hash
                if department:
                    existing.department_id = department.id
                logger.info(f"Updated {email} ({role})")
            else:
                session.add(
                    User(
                        id=uuid.uuid4(),
                        name=name,
                        email=email,
                        password_hash=password_hash,
                        role=role,
                        department_id=department.id if department else None,
                    )
                )
                logger.info(f"Created {email} ({role})")

        session.commit()

        print(f"\nDemo credentials (password: {args.password}):")
        for email, name, role in DEMO_USERS:
            print(f"  {email:26} {role:12} {name}")

    except Exception as e:
        session.rollback()
        logger.error(f"Seeding failed: {e}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
