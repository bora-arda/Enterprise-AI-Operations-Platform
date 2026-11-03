"""FastMCP HTTP server for the mock ERP service.

Exposes the shared mock ERP operations over the MCP streamable HTTP transport
for containerized deployments. The stdio server remains available for local
MCP clients.
"""

import logging

from fastmcp import FastMCP

from procurement_ai.mcp import service

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "mock-erp-server",
    instructions="Mock ERP/payment operations for the procurement platform.",
)


@mcp.tool
def create_payment_request(
    payment_reference: str,
    invoice_id: str,
    amount: float,
    currency: str = "GBP",
) -> dict:
    """Submit a payment request to the mock ERP."""
    return service.create_payment_request(
        payment_reference=payment_reference,
        invoice_id=invoice_id,
        amount=amount,
        currency=currency,
    )


@mcp.tool
def get_payment_status(payment_reference: str) -> dict:
    """Check the status of a mock ERP payment."""
    record = service.get_payment_status(payment_reference)
    return record or {"status": "not_found", "payment_reference": payment_reference}


@mcp.tool
def create_exception(exception_type: str, entity_id: str, description: str = "") -> dict:
    """Create an exception record in the mock ERP."""
    return service.create_exception(exception_type, entity_id, description)


@mcp.tool
def update_workflow_status(workflow_id: str, status: str, comment: str | None = None) -> dict:
    """Update workflow state in the mock ERP."""
    return service.update_workflow_status(workflow_id, status, comment)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mcp.run(transport="http", host="0.0.0.0", port=8001)
