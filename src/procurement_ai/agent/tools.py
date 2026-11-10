"""Tool schemas and executor for the open-ended agent.

All tools are read-only. Actions such as payments continue to go through the
existing human-approval workflow, not through this agent.
"""

import copy
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from procurement_ai.agent.cache import get_agent_cache
from procurement_ai.database.connection import AsyncSessionLocal
from procurement_ai.database.models import (
    ApprovalRequest,
    Contract,
    Invoice,
    Payment,
    PurchaseOrder,
    Vendor,
)
from procurement_ai.database.models import Exception as ExceptionRecord
from procurement_ai.database.sql_guard import describe_schema, run_readonly_sql
from procurement_ai.observability.metrics import CACHE_EVENTS, EXCEPTIONS_OPEN
from procurement_ai.retrieval.hybrid import hybrid_search
from procurement_ai.security.access import AccessScope
from procurement_ai.semantic.metrics import (
    ALLOWED_DIMENSIONS,
    DIMENSIONS,
    METRIC_LABELS,
    MetricRequest,
    compute_metric,
)
from procurement_ai.semantic.parser import format_metric_result
from procurement_ai.tools.read_tools import (
    get_contract,
    get_invoice,
    get_purchase_order,
    get_vendor,
)

logger = logging.getLogger(__name__)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return str(value)


TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "describe_schema",
            "description": (
                "Return the public database schema (table names and columns). "
                "Use before writing SQL if you are unsure about table/column names."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": (
                "Execute ONE read-only SELECT/WITH query against the procurement "
                "PostgreSQL database. Use for arbitrary joins, comparisons, filters, "
                "and aggregations not covered by semantic metrics. The query is "
                "limited to 100 rows and a 5 second timeout. Never use data-changing "
                "statements. Prefer semantic metrics for common aggregates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "A single read-only SELECT or WITH query.",
                    }
                },
                "required": ["sql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_metric",
            "description": (
                "Run a governed semantic metric. Prefer this over SQL for total_spend, "
                "invoice_count, avg_invoice_value, overdue_rate, exception_count, "
                "exception_rate, approval_cycle_time, contracts_expiring, "
                "overdue_invoices, pending_approvals, pending_payment_requests, or "
                "pending_payments."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": sorted(METRIC_LABELS.keys())},
                    "dimension": {
                        "type": "string",
                        "enum": sorted(DIMENSIONS.keys()),
                        "description": "Optional grouping dimension, when allowed.",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Optional lookback/expiry window in days.",
                    },
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Search policies, contract summaries, emails, and operational notes "
                "using hybrid retrieval. Use for process/policy/document questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 8},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_exceptions",
            "description": (
                "List curated anomaly/exception records with invoice, purchase order, "
                "vendor, and contract context. Use for anomaly summaries and for "
                "follow-ups such as 'invoice exceeds po', 'missing approval', "
                "'already paid', 'payment mismatch', 'wrong vendor', or "
                "'duplicate invoices'. Omit exception_type to get counts by type."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "exception_type": {
                        "type": "string",
                        "description": (
                            "Optional exception type or natural alias, e.g. "
                            "invoice_exceeds_po, missing_approval, already_paid, "
                            "invoice_exceeds_contract, duplicate_invoice, "
                            "payment_mismatch, wrong_vendor, wrong_currency, "
                            "expired_contract, invalid_po."
                        ),
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_invoice",
            "description": "Retrieve a single invoice by number (e.g. INV-000001).",
            "parameters": {
                "type": "object",
                "properties": {"invoice_id": {"type": "string"}},
                "required": ["invoice_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_purchase_order",
            "description": "Retrieve a purchase order by number (e.g. PO-000001).",
            "parameters": {
                "type": "object",
                "properties": {"po_id": {"type": "string"}},
                "required": ["po_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_contract",
            "description": "Retrieve a contract by number (e.g. CF-2022-00001).",
            "parameters": {
                "type": "object",
                "properties": {"contract_id": {"type": "string"}},
                "required": ["contract_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vendor",
            "description": "Retrieve a vendor by UUID.",
            "parameters": {
                "type": "object",
                "properties": {"vendor_id": {"type": "string"}},
                "required": ["vendor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_payment",
            "description": "Retrieve a payment by reference (e.g. PAY-000001).",
            "parameters": {
                "type": "object",
                "properties": {"payment_reference": {"type": "string"}},
                "required": ["payment_reference"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_approval",
            "description": "Retrieve an approval request by number (e.g. APPR-E0467A0D).",
            "parameters": {
                "type": "object",
                "properties": {"approval_number": {"type": "string"}},
                "required": ["approval_number"],
            },
        },
    },
]


async def _invoice_department(invoice_id: str | None) -> str | None:
    if not invoice_id:
        return None
    try:
        invoice_uuid = UUID(str(invoice_id))
    except (ValueError, TypeError):
        return None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PurchaseOrder.department_id)
            .join(Invoice, Invoice.po_id == PurchaseOrder.id)
            .where(Invoice.id == invoice_uuid)
        )
        value = result.scalar_one_or_none()
        return str(value) if value else None


async def _vendor_in_department(vendor_id: str | None, scope: AccessScope) -> bool:
    if not vendor_id:
        return False
    try:
        vendor_uuid = UUID(str(vendor_id))
    except (ValueError, TypeError):
        return False
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PurchaseOrder.id)
            .where(
                PurchaseOrder.vendor_id == vendor_uuid,
                PurchaseOrder.department_id == scope.department_uuid,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None


def _scope_denied() -> dict:
    return {
        "error": "not_found",
        "detail": "Record not found or not accessible for this user's department",
    }


def _scope_allows_department(scope: AccessScope | None, department_id: str | UUID | None) -> bool:
    return scope is None or scope.allows_department(department_id)


async def _get_payment(reference: str) -> dict | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Payment).where(Payment.payment_reference == reference.upper()))
        payment = result.scalar_one_or_none()
        if not payment:
            return None
        return {
            "payment_reference": payment.payment_reference,
            "invoice_id": str(payment.invoice_id) if payment.invoice_id else None,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
            "method": payment.method,
            "status": payment.status,
        }


async def _get_approval(number: str) -> dict | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ApprovalRequest).where(ApprovalRequest.approval_number == number.upper()))
        approval = result.scalar_one_or_none()
        if not approval:
            return None
        return {
            "approval_number": approval.approval_number,
            "request_type": approval.request_type,
            "invoice_id": str(approval.invoice_id) if approval.invoice_id else None,
            "status": approval.status,
            "justification": approval.justification,
            "requested_at": approval.requested_at.isoformat() if approval.requested_at else None,
            "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
        }


EXCEPTION_ALIASES = {
    "invoice exceeds po": "invoice_exceeds_po",
    "invoice exceed po": "invoice_exceeds_po",
    "exceeds po": "invoice_exceeds_po",
    "over po": "invoice_exceeds_po",
    "invoice exceeds purchase order": "invoice_exceeds_po",
    "missing approval": "missing_approval",
    "missing approvals": "missing_approval",
    "already paid": "already_paid",
    "duplicate invoice": "duplicate_invoice",
    "duplicate invoices": "duplicate_invoice",
    "payment mismatch": "payment_mismatch",
    "wrong vendor": "wrong_vendor",
    "wrong currency": "wrong_currency",
    "expired contract": "expired_contract",
    "expired contracts": "expired_contract",
    "invalid po": "invalid_po",
}


def _normalize_exception_type(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower().replace("-", "_")
    if normalized in EXCEPTION_ALIASES:
        return EXCEPTION_ALIASES[normalized]
    if normalized.replace(" ", "_") in {
        "invoice_exceeds_po",
        "invoice_exceeds_contract",
        "missing_approval",
        "already_paid",
        "duplicate_invoice",
        "payment_mismatch",
        "wrong_vendor",
        "wrong_currency",
        "expired_contract",
        "invalid_po",
    }:
        return normalized.replace(" ", "_")
    for phrase, rule in EXCEPTION_ALIASES.items():
        if phrase in normalized:
            return rule
    return normalized


async def _list_exceptions(
    exception_type: str | None,
    severity: str | None,
    limit: int,
    scope: AccessScope | None = None,
) -> dict:
    normalized_type = _normalize_exception_type(exception_type)
    normalized_severity = severity.lower() if severity else None

    if scope is not None and scope.restricted and not scope.department_uuid:
        return {
            "exception_type": normalized_type,
            "severity": normalized_severity,
            "total": 0,
            "counts": [],
            "rows": [],
            "row_count": 0,
        }

    async with AsyncSessionLocal() as session:
        filters = []
        if normalized_type:
            filters.append(ExceptionRecord.exception_type == normalized_type)
        if normalized_severity:
            filters.append(ExceptionRecord.severity == normalized_severity)
        if scope is not None and scope.restricted:
            filters.append(PurchaseOrder.department_id == scope.department_uuid)

        count_stmt = (
            select(ExceptionRecord.exception_type, func.count())
            .group_by(ExceptionRecord.exception_type)
            .order_by(func.count().desc())
        )
        total_stmt = select(func.count()).select_from(ExceptionRecord)
        if scope is not None and scope.restricted:
            count_stmt = count_stmt.join(Invoice, Invoice.id == ExceptionRecord.invoice_id).join(
                PurchaseOrder, PurchaseOrder.id == Invoice.po_id
            )
            total_stmt = total_stmt.join(Invoice, Invoice.id == ExceptionRecord.invoice_id).join(
                PurchaseOrder, PurchaseOrder.id == Invoice.po_id
            )
        if filters:
            count_stmt = count_stmt.where(*filters)
            total_stmt = total_stmt.where(*filters)

        counts_result = await session.execute(count_stmt)
        counts = [{"exception_type": row[0], "count": row[1]} for row in counts_result.all()]
        for item in counts:
            EXCEPTIONS_OPEN.labels(type=item["exception_type"]).set(float(str(item["count"] or 0)))
        total = int(await session.scalar(total_stmt) or 0)

        row_stmt = (
            select(
                ExceptionRecord.exception_type,
                ExceptionRecord.severity,
                ExceptionRecord.description,
                ExceptionRecord.status,
                Invoice.invoice_number,
                Invoice.amount,
                Invoice.currency,
                PurchaseOrder.po_number,
                PurchaseOrder.total_amount,
                Vendor.name,
                Contract.contract_number,
                Contract.title,
                Contract.max_value,
            )
            .join(Invoice, Invoice.id == ExceptionRecord.invoice_id)
            .outerjoin(PurchaseOrder, PurchaseOrder.id == Invoice.po_id)
            .outerjoin(Vendor, Vendor.id == Invoice.vendor_id)
            .outerjoin(Contract, Contract.id == PurchaseOrder.contract_id)
            .order_by(Invoice.amount.desc())
            .limit(limit)
        )
        if filters:
            row_stmt = row_stmt.where(*filters)
        rows_result = await session.execute(row_stmt)

        rows = []
        for row in rows_result.all():
            (
                rule,
                level,
                description,
                status,
                invoice_number,
                amount,
                currency,
                po_number,
                po_amount,
                vendor_name,
                contract_number,
                contract_title,
                contract_max,
            ) = row
            invoice_amount = float(amount) if amount is not None else None
            po_value = float(po_amount) if po_amount is not None else None
            contract_value = float(contract_max) if contract_max is not None else None
            over_by = None
            if invoice_amount is not None:
                if rule == "invoice_exceeds_po" and po_value is not None:
                    over_by = round(invoice_amount - po_value, 2)
                elif rule == "invoice_exceeds_contract" and contract_value is not None:
                    over_by = round(invoice_amount - contract_value, 2)
            rows.append(
                {
                    "exception_type": rule,
                    "severity": level,
                    "description": description,
                    "status": status,
                    "invoice_number": invoice_number,
                    "amount": invoice_amount,
                    "currency": currency,
                    "po_number": po_number,
                    "po_amount": po_value,
                    "vendor": vendor_name,
                    "contract_number": contract_number,
                    "contract_title": contract_title,
                    "contract_max": contract_value,
                    "over_by": over_by,
                }
            )

        return {
            "exception_type": normalized_type,
            "severity": normalized_severity,
            "total": total,
            "counts": counts,
            "rows": rows,
            "row_count": len(rows),
        }


async def execute_tool(
    name: str,
    args: dict,
    user_id: str | None = None,
    scope: AccessScope | None = None,
) -> dict:
    """Execute a read-only agent tool and return JSON-serializable data."""
    try:
        if name == "describe_schema":
            cache = get_agent_cache()
            cache_key = "schema:public"
            cached = cache.get(cache_key)
            if cached is not None:
                CACHE_EVENTS.labels(cache="schema", result="hit").inc()
                return copy.deepcopy(cached)
            CACHE_EVENTS.labels(cache="schema", result="miss").inc()
            result = await describe_schema()
            cache.set(cache_key, result)
            return result

        if name == "query_database":
            if scope is not None and scope.restricted:
                return {
                    "error": "access_denied",
                    "detail": (
                        "Arbitrary SQL is available only to global read roles. "
                        "Use scoped metrics, exceptions, or entity tools."
                    ),
                }
            sql = str(args.get("sql", ""))
            return await run_readonly_sql(sql, user_id=user_id)

        if name == "run_metric":
            metric = str(args.get("metric", "")).lower()
            if metric not in METRIC_LABELS:
                return {"error": "invalid_metric", "detail": f"Unknown metric: {metric}"}

            dimension = args.get("dimension")
            if dimension and dimension not in ALLOWED_DIMENSIONS.get(metric, set()):
                dimension = None
            try:
                days = int(args["days"]) if args.get("days") is not None else None
            except (TypeError, ValueError):
                days = None

            department_id = scope.department_id if scope is not None and scope.restricted else None
            request = MetricRequest(
                metric=metric,
                dimension=dimension,
                days=days,
                limit=20,
                department_id=department_id,
            )
            cache_key = f"metric:{department_id or 'global'}:{metric}:{dimension}:{days}:{request.limit}"
            cache = get_agent_cache()
            cached = cache.get(cache_key)
            if cached is not None:
                CACHE_EVENTS.labels(cache="metric", result="hit").inc()
                return copy.deepcopy(cached)
            CACHE_EVENTS.labels(cache="metric", result="miss").inc()
            async with AsyncSessionLocal() as session:
                metric_result = await compute_metric(session, request)
            response = {
                "metric": metric_result.metric,
                "label": metric_result.label,
                "dimension": metric_result.dimension,
                "rows": _json_safe(metric_result.rows),
                "row_count": len(metric_result.rows),
                "formatted": format_metric_result(metric_result),
            }
            cache.set(cache_key, response)
            return response

        if name == "search_documents":
            query = str(args.get("query", "")).strip()
            if not query:
                return {"error": "invalid_query", "detail": "Query is required"}
            top_k = min(max(int(args.get("top_k", 5)), 1), 8)
            department_key = scope.department_id if scope is not None and scope.restricted else "global"
            cache_key = f"documents:{department_key}:{top_k}:{query[:200]}"
            cache = get_agent_cache()
            cached = cache.get(cache_key)
            if cached is not None:
                CACHE_EVENTS.labels(cache="documents", result="hit").inc()
                return copy.deepcopy(cached)
            CACHE_EVENTS.labels(cache="documents", result="miss").inc()
            async with AsyncSessionLocal() as session:
                results = await hybrid_search(session, query, top_k=top_k)
            results = [
                r
                for r in results
                if scope is None
                or not scope.restricted
                or not r.get("department")
                or str(r.get("department")) == str(scope.department_id)
            ]
            response = {
                "query": query,
                "results": [
                    {
                        "source": r["source"],
                        "title": r.get("title", ""),
                        "content": (r.get("content") or "")[:1200],
                        "score": r.get("score", 0),
                        "department": r.get("department"),
                    }
                    for r in results
                ],
            }
            cache.set(cache_key, response)
            return response

        if name == "list_exceptions":
            try:
                limit = min(max(int(args.get("limit", 50)), 1), 100)
            except (TypeError, ValueError):
                limit = 50
            return await _list_exceptions(
                str(args.get("exception_type") or "") or None,
                str(args.get("severity") or "") or None,
                limit,
                scope=scope,
            )

        if name == "get_invoice":
            async with AsyncSessionLocal() as session:
                entity_result = await get_invoice(session, str(args.get("invoice_id", "")))
            if entity_result and scope is not None and scope.restricted:
                department = await _invoice_department(entity_result.get("invoice_id"))
                if not scope.allows_department(department):
                    return _scope_denied()
            return entity_result or {"error": "not_found", "detail": "Invoice not found"}

        if name == "get_purchase_order":
            async with AsyncSessionLocal() as session:
                entity_result = await get_purchase_order(session, str(args.get("po_id", "")))
            if (
                entity_result
                and scope is not None
                and scope.restricted
                and not scope.allows_department(entity_result.get("department_id"))
            ):
                return _scope_denied()
            return entity_result or {
                "error": "not_found",
                "detail": "Purchase order not found",
            }

        if name == "get_contract":
            if scope is not None and scope.restricted:
                return _scope_denied()
            async with AsyncSessionLocal() as session:
                entity_result = await get_contract(session, str(args.get("contract_id", "")))
            return entity_result or {
                "error": "not_found",
                "detail": "Contract not found",
            }

        if name == "get_vendor":
            async with AsyncSessionLocal() as session:
                entity_result = await get_vendor(session, str(args.get("vendor_id", "")))
            if (
                entity_result
                and scope is not None
                and scope.restricted
                and not await _vendor_in_department(entity_result.get("vendor_id"), scope)
            ):
                return _scope_denied()
            return entity_result or {"error": "not_found", "detail": "Vendor not found"}

        if name == "get_payment":
            entity_result = await _get_payment(str(args.get("payment_reference", "")))
            if entity_result and scope is not None and scope.restricted:
                department = await _invoice_department(entity_result.get("invoice_id"))
                if not scope.allows_department(department):
                    return _scope_denied()
            return entity_result or {"error": "not_found", "detail": "Payment not found"}

        if name == "get_approval":
            entity_result = await _get_approval(str(args.get("approval_number", "")))
            if entity_result and scope is not None and scope.restricted:
                department = await _invoice_department(entity_result.get("invoice_id"))
                if not scope.allows_department(department):
                    return _scope_denied()
            return entity_result or {
                "error": "not_found",
                "detail": "Approval not found",
            }

        return {"error": "unknown_tool", "detail": f"Unknown tool: {name}"}
    except Exception as e:
        logger.warning("Agent tool %s failed: %s", name, e, exc_info=True)
        return {"error": "tool_failed", "detail": str(e)[:300]}


def citations_for_tool(name: str, args: dict, result: dict) -> list[dict]:
    """Build evidence citations from a tool call result."""
    if name == "query_database":
        sql = str(args.get("sql", ""))
        rows = result.get("row_count", 0)
        return [
            {
                "source": "sql",
                "snippet": f"{rows} row(s): {sql[:240]}",
            }
        ]

    if name == "describe_schema":
        tables = len((result.get("tables") or {}).keys())
        return [{"source": "schema", "snippet": f"{tables} tables inspected"}]

    if name == "run_metric":
        return [
            {
                "source": f"metric:{result.get('metric', args.get('metric', ''))}",
                "snippet": result.get("label", "semantic metric"),
            }
        ]

    if name == "search_documents":
        return [
            {
                "source": item.get("source", "document"),
                "snippet": (f"{item.get('title', '')}: " if item.get("title") else "")
                + (item.get("content") or "")[:240],
            }
            for item in (result.get("results") or [])[:3]
        ]

    if name == "list_exceptions":
        labels = ", ".join(f"{item['exception_type']}={item['count']}" for item in (result.get("counts") or [])[:5])
        return [
            {
                "source": f"exceptions:{result.get('exception_type') or 'all'}",
                "snippet": f"{result.get('total', 0)} record(s); {labels}",
            }
        ]

    if name == "get_invoice":
        return [
            {
                "source": f"invoice:{result.get('invoice_number', args.get('invoice_id', ''))}",
                "snippet": f"Amount {result.get('amount')} {result.get('currency')}",
            }
        ]

    if name == "get_purchase_order":
        return [
            {
                "source": f"purchase_order:{result.get('po_number', args.get('po_id', ''))}",
                "snippet": f"Total {result.get('total_amount')} {result.get('currency')}",
            }
        ]

    if name == "get_contract":
        return [
            {
                "source": f"contract:{result.get('contract_number', args.get('contract_id', ''))}",
                "snippet": str(result.get("title", ""))[:200],
            }
        ]

    if name == "get_vendor":
        return [
            {
                "source": f"vendor:{result.get('vendor_id', args.get('vendor_id', ''))}",
                "snippet": str(result.get("name", ""))[:200],
            }
        ]

    if name == "get_payment":
        return [
            {
                "source": f"payment:{result.get('payment_reference', args.get('payment_reference', ''))}",
                "snippet": f"Amount {result.get('amount')} {result.get('currency')}",
            }
        ]

    if name == "get_approval":
        return [
            {
                "source": f"approval:{result.get('approval_number', args.get('approval_number', ''))}",
                "snippet": f"Status {result.get('status')}",
            }
        ]

    return []
