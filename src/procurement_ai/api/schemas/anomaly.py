"""Anomaly request/response schemas."""

from pydantic import BaseModel


class AnomalyResponse(BaseModel):
    id: str
    invoice_id: str | None = None
    exception_type: str
    severity: str
    description: str
    status: str
    detected_at: str


class AnomalyListResponse(BaseModel):
    anomalies: list[AnomalyResponse]
    total: int
