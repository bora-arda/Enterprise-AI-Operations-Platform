"""MCP server for mock ERP/payment service.

Exposes the shared mock ERP service (``mcp/service.py``) over the Model
Context Protocol. The same service backs the internal approval executor.
"""

import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server

from procurement_ai.mcp import service

logger = logging.getLogger(__name__)


def create_server() -> Server:
    """Create the MCP server."""
    server = Server("mock-erp-server")

    @server.list_tools()
    async def list_tools() -> list[dict]:
        return [
            {
                "name": "create_payment_request",
                "description": "Submit a payment request to the mock ERP",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "payment_reference": {"type": "string"},
                        "invoice_id": {"type": "string"},
                        "amount": {"type": "number"},
                        "currency": {"type": "string"},
                    },
                    "required": ["payment_reference", "invoice_id", "amount"],
                },
            },
            {
                "name": "get_payment_status",
                "description": "Check payment status in the mock ERP",
                "inputSchema": {
                    "type": "object",
                    "properties": {"payment_reference": {"type": "string"}},
                    "required": ["payment_reference"],
                },
            },
            {
                "name": "create_exception",
                "description": "Create an exception record in the mock ERP",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "exception_type": {"type": "string"},
                        "entity_id": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["exception_type", "entity_id"],
                },
            },
            {
                "name": "update_workflow_status",
                "description": "Update workflow state in the mock ERP",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string"},
                        "status": {"type": "string"},
                        "comment": {"type": "string"},
                    },
                    "required": ["workflow_id", "status"],
                },
            },
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[dict]:
        logger.info(f"MCP tool called: {name}")

        if name == "create_payment_request":
            payment = service.create_payment_request(
                payment_reference=arguments["payment_reference"],
                invoice_id=arguments["invoice_id"],
                amount=float(arguments["amount"]),
                currency=arguments.get("currency", "GBP"),
            )
            return [{"type": "text", "text": str(payment)}]

        if name == "get_payment_status":
            payment_status = service.get_payment_status(arguments["payment_reference"])
            return [
                {
                    "type": "text",
                    "text": str(payment_status) if payment_status else "Payment not found",
                }
            ]

        if name == "create_exception":
            exception_record = service.create_exception(
                exception_type=arguments["exception_type"],
                entity_id=arguments["entity_id"],
                description=arguments.get("description", ""),
            )
            return [{"type": "text", "text": str(exception_record)}]

        if name == "update_workflow_status":
            workflow = service.update_workflow_status(
                workflow_id=arguments["workflow_id"],
                status=arguments["status"],
                comment=arguments.get("comment"),
            )
            return [{"type": "text", "text": str(workflow)}]

        return [{"type": "text", "text": f"Unknown tool: {name}"}]

    return server


async def run_server():
    """Run the MCP server over stdio."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_server())
