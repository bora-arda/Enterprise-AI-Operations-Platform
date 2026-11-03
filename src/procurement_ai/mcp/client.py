"""MCP client for connecting to the mock ERP server."""

import logging
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for the mock ERP MCP server."""

    def __init__(self, server_url: str | None = None):
        self.server_url = server_url or "http://localhost:8001"
        self.session: ClientSession | None = None

    async def connect(self):
        """Connect to the MCP server."""
        # For stdio-based MCP server
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "python", "-m", "src.procurement_ai.mcp.server"],
        )
        self._stdio_context = stdio_client(server_params)
        self._read_stream, self._write_stream = await self._stdio_context.__aenter__()
        self.session = ClientSession(self._read_stream, self._write_stream)
        await self.session.__aenter__()
        await self.session.initialize()
        logger.info("Connected to MCP server")

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None
        if hasattr(self, "_stdio_context"):
            await self._stdio_context.__aexit__(None, None, None)
        logger.info("Disconnected from MCP server")

    async def create_payment_request(
        self, payment_reference: str, invoice_id: str, amount: float, currency: str
    ) -> Any:
        """Create a payment request."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        result = await self.session.call_tool(
            "create_payment_request",
            {
                "payment_reference": payment_reference,
                "invoice_id": invoice_id,
                "amount": amount,
                "currency": currency,
            },
        )
        return result

    async def get_payment_status(self, payment_reference: str) -> Any:
        """Get payment status."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        result = await self.session.call_tool(
            "get_payment_status",
            {
                "payment_reference": payment_reference,
            },
        )
        return result

    async def create_exception(self, exception_type: str, entity_id: str, description: str) -> Any:
        """Create an exception."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        result = await self.session.call_tool(
            "create_exception",
            {
                "exception_type": exception_type,
                "entity_id": entity_id,
                "description": description,
            },
        )
        return result

    async def update_workflow_status(self, workflow_id: str, status: str, comment: str | None = None) -> Any:
        """Update workflow status."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        result = await self.session.call_tool(
            "update_workflow_status",
            {
                "workflow_id": workflow_id,
                "status": status,
                "comment": comment,
            },
        )
        return result
