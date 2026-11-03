"""Convert documents.embedding to pgvector and add HNSW index.

Revision ID: 002
Revises: 001
Create Date: 2026-11-03
"""

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Column was created as double precision[] in 001; convert to pgvector.
    # Existing values are NULL, so USING NULL is safe.
    op.execute("ALTER TABLE documents ALTER COLUMN embedding TYPE vector(384) USING NULL")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_embedding_hnsw ON documents USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_documents_embedding_hnsw")
    op.execute("ALTER TABLE documents ALTER COLUMN embedding TYPE double precision[] USING NULL")
