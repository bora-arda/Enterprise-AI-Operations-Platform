"""Approval request/response schemas."""

from pydantic import BaseModel, Field


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject)$", description="Decision: approve or reject")
    comment: str | None = Field(None, max_length=500, description="Optional comment")


class ApprovalResponse(BaseModel):
    id: str
    approval_number: str
    request_type: str
    invoice_id: str | None = None
    invoice_number: str | None = None
    amount: float | None = None
    currency: str | None = None
    vendor_name: str | None = None
    requested_by_name: str | None = None
    department_name: str | None = None
    department_code: str | None = None
    due_date: str | None = None
    risk_level: str | None = None
    status: str
    requested_at: str | None = None
    decided_at: str | None = None
    justification: str | None = None


class ApprovalListResponse(BaseModel):
    approvals: list[ApprovalResponse]
    total: int
