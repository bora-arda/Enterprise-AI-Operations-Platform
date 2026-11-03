"""Tool-layer guardrails for authorization and safety."""

import logging

logger = logging.getLogger(__name__)

# Role-based tool access
TOOL_PERMISSIONS = {
    "get_invoice": ["specialist", "manager", "director", "admin"],
    "get_purchase_order": ["specialist", "manager", "director", "admin"],
    "get_contract": ["specialist", "manager", "director", "admin"],
    "get_vendor": ["specialist", "manager", "director", "admin"],
    "get_payment_status": ["specialist", "manager", "director", "admin"],
    "search_documents": ["specialist", "manager", "director", "admin"],
    "query_procurement_db": ["manager", "director", "admin"],
    "run_business_analysis": ["manager", "director", "admin"],
    "detect_anomalies": ["specialist", "manager", "director", "admin"],
    "check_policy": ["specialist", "manager", "director", "admin"],
    "get_approval_status": ["specialist", "manager", "director", "admin"],
    "create_approval_request": ["specialist", "manager", "director", "admin"],
    "execute_controlled_action": ["manager", "director", "admin"],
}


class ToolGuard:
    """Tool authorization and safety checks."""

    @staticmethod
    def check_authorization(tool_name: str, user_role: str) -> tuple[bool, str | None]:
        """Check if a user role is authorized to use a tool."""
        allowed_roles = TOOL_PERMISSIONS.get(tool_name, [])
        if user_role not in allowed_roles:
            return False, f"Role '{user_role}' is not authorized to use '{tool_name}'"
        return True, None

    @staticmethod
    def check_idempotency(tool_name: str, tool_args: dict, existing_calls: list[dict]) -> dict:
        """Check for duplicate tool calls (idempotency)."""
        for call in existing_calls:
            if call.get("tool_name") == tool_name and call.get("tool_args") == tool_args:
                return {
                    "duplicate": True,
                    "original_result": call.get("result"),
                }
        return {"duplicate": False}

    @staticmethod
    def validate_tool_args(tool_name: str, args: dict) -> tuple[bool, str | None]:
        """Validate tool arguments."""
        if not args:
            return False, "Tool arguments cannot be empty"

        # Check for SQL injection patterns in any string values
        sql_patterns = [r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b.*\b(FROM|TABLE|DATABASE)\b)"]
        for key, value in args.items():
            if isinstance(value, str):
                for pattern in sql_patterns:
                    import re

                    if re.search(pattern, value, re.IGNORECASE):
                        return False, f"Potential SQL injection in argument '{key}'"

        return True, None
