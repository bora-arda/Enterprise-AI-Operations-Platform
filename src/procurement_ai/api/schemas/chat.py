"""Chat request/response schemas."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User's natural language question")
    user_id: str | None = Field(
        None,
        description="Deprecated: the authenticated user is used instead",
    )
    session_id: str | None = Field(None, description="Optional session identifier for conversation context")


class Citation(BaseModel):
    source: str = Field(..., description="Evidence source identifier")
    snippet: str = Field(..., description="Relevant text snippet")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent's natural language response")
    citations: list[Citation] = Field(default_factory=list, description="Evidence citations")
    confidence: float | None = Field(None, ge=0.0, le=1.0, description="Confidence score")
    workflow: str | None = Field(None, description="Workflow that handled the request")
    trace_id: str | None = Field(None, description="Observability trace identifier")
    decision_id: str | None = Field(None, description="Planner decision audit record identifier")
