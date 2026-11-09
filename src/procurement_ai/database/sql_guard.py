"""Read-only SQL execution with conservative validation.

This is the safety boundary for the open-ended agent. It is intentionally
conservative: SELECT/WITH only, single statement, denied keywords/functions,
denied sensitive tables/columns, row caps, statement timeout, and a read-only
transaction. Production deployments should also use a dedicated SELECT-only
database role.
"""

import logging
import re
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text

from procurement_ai.config.settings import get_settings
from procurement_ai.database.connection import AsyncSessionLocal

logger = logging.getLogger(__name__)

DENIED_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "merge",
    "upsert",
    "drop",
    "alter",
    "create",
    "truncate",
    "grant",
    "revoke",
    "copy",
    "call",
    "do",
    "set",
    "reset",
    "vacuum",
    "analyze",
    "explain",
    "comment",
    "lock",
    "reindex",
    "refresh",
    "cluster",
    "discard",
    "listen",
    "notify",
    "unlisten",
    "prepare",
    "execute",
    "deallocate",
    "declare",
    "fetch",
    "move",
    "close",
    "begin",
    "commit",
    "rollback",
    "savepoint",
    "release",
    "start",
    "abort",
    "into",
}

DENIED_FUNCTIONS = {
    "pg_sleep",
    "pg_read_file",
    "pg_read_binary_file",
    "pg_ls_dir",
    "lo_import",
    "lo_export",
    "dblink",
    "set_config",
    "pg_terminate_backend",
    "pg_cancel_backend",
    "pg_reload_conf",
    "pg_rotate_logfile",
    "pg_create_restore_point",
    "pg_switch_wal",
}

DENIED_TABLES = {
    "planner_decisions",
    "checkpoints",
    "checkpoint_blobs",
    "checkpoint_writes",
    "checkpoint_migrations",
    "pg_shadow",
    "pg_authid",
    "pg_user",
    "pg_roles",
    "pg_settings",
    "pg_stat_activity",
    "pg_stat_ssl",
}

DENIED_COLUMNS = {
    "password_hash",
    "embedding",
    "bank_details",
}


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql


def _mask_string_literals(sql: str) -> str:
    return re.sub(r"'(?:''|[^'])*'", "''", sql)


def _normalize_sql(sql: str) -> str:
    """Remove comments/fences and tolerate common model formatting artifacts."""
    cleaned = _strip_comments(sql).strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # The model occasionally emits an unmatched wrapping quote.
    if len(cleaned) >= 2 and cleaned[0] in ('"', "'") and cleaned[-1] == cleaned[0]:
        cleaned = cleaned[1:-1].strip()
    if cleaned.endswith('"') and cleaned.count('"') % 2 == 1:
        cleaned = cleaned[:-1].rstrip()
    if cleaned.endswith("'") and cleaned.count("'") % 2 == 1:
        cleaned = cleaned[:-1].rstrip()

    return cleaned


def validate_sql(sql: str) -> tuple[bool, str | None]:
    """Return (valid, reason). Reasons are safe to show to the model."""
    if not sql or not sql.strip():
        return False, "SQL is empty"

    cleaned = _normalize_sql(sql)
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    if ";" in cleaned:
        return False, "Only a single SQL statement is allowed"

    masked = _mask_string_literals(cleaned).lower()

    if not re.match(r"^(select|with)\b", masked):
        return False, "Only SELECT/WITH queries are allowed"

    for keyword in DENIED_KEYWORDS:
        if re.search(rf"\b{keyword}\b", masked):
            return False, f"Keyword '{keyword}' is not allowed"

    if re.search(r"\bfor\s+(update|share)\b", masked):
        return False, "Row-locking queries are not allowed"

    for function in DENIED_FUNCTIONS:
        if re.search(rf"\b{function}\s*\(", masked):
            return False, f"Function '{function}' is not allowed"

    for table in DENIED_TABLES:
        if re.search(rf"\b{table}\b", masked):
            return False, f"Table '{table}' is not accessible"

    for column in DENIED_COLUMNS:
        if re.search(rf"\b{column}\b", masked):
            return False, f"Column '{column}' is not accessible"

    return True, None


def _serialize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return "<binary>"
    return str(value)


async def run_readonly_sql(
    sql: str,
    *,
    user_id: str | None = None,
) -> dict:
    """Validate and execute a read-only SQL query with row/time limits."""
    settings = get_settings()
    valid, reason = validate_sql(sql)
    if not valid:
        logger.warning("Rejected SQL from user %s: %s", user_id, reason)
        return {"error": "query_rejected", "detail": reason, "sql": sql[:1000]}

    max_rows = max(1, settings.sql_max_rows)
    timeout_ms = max(100, settings.sql_query_timeout_ms)
    cleaned = _normalize_sql(sql).rstrip(";").strip()

    # Wrap to enforce a hard row cap without rewriting the user's ORDER BY/LIMIT.
    wrapped = f"SELECT * FROM (\n{cleaned}\n) AS agent_query LIMIT :max_rows"
    start = time.perf_counter()

    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("SET TRANSACTION READ ONLY"))
            await session.execute(
                text("SELECT set_config('statement_timeout', :timeout, true)"),
                {"timeout": str(timeout_ms)},
            )

            result = await session.execute(text(wrapped), {"max_rows": max_rows + 1})
            keys = [str(key) for key in result.keys()]  # noqa: SIM118
            raw_rows = result.fetchall()
            truncated = len(raw_rows) > max_rows

            # Defense in depth: never expose denied columns, even via SELECT *.
            safe_keys = [key for key in keys if key.lower() not in DENIED_COLUMNS]
            rows = []
            for row in raw_rows[:max_rows]:
                mapping = dict(zip(keys, row, strict=False))
                rows.append(
                    {key: _serialize(value) for key, value in mapping.items() if key.lower() not in DENIED_COLUMNS}
                )

            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                "Read-only SQL executed",
                extra={
                    "user_id": user_id,
                    "duration_ms": duration_ms,
                    "row_count": len(rows),
                    "truncated": truncated,
                },
            )
            return {
                "columns": safe_keys,
                "rows": rows,
                "row_count": len(rows),
                "truncated": truncated,
                "sql": cleaned,
                "duration_ms": duration_ms,
            }
        except Exception as e:
            await session.rollback()
            logger.warning("Read-only SQL failed for user %s: %s", user_id, e)
            return {
                "error": "query_failed",
                "detail": str(e)[:300],
                "sql": cleaned[:1000],
            }


async def describe_schema() -> dict:
    """Return a compact schema summary, excluding sensitive tables/columns."""
    query = """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("SET TRANSACTION READ ONLY"))
            result = await session.execute(text(query))
            tables: dict[str, list[dict]] = {}
            for table_name, column_name, data_type in result.fetchall():
                if table_name in DENIED_TABLES:
                    continue
                if column_name.lower() in DENIED_COLUMNS:
                    continue
                tables.setdefault(table_name, []).append({"column": column_name, "type": data_type})
            return {"tables": tables}
        except Exception as e:
            logger.warning("Schema introspection failed: %s", e)
            return {"error": "schema_unavailable", "detail": str(e)[:200]}
