"""Pydantic schemas for structured data extraction and API responses."""

from __future__ import annotations

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


# --- Extraction Schemas (GPT structured output) ---

class MaterialUsed(BaseModel):
    """A single material used during a job."""
    item: str = Field(description="Name of the material")
    quantity: int = Field(ge=1, description="Number of units used")
    unit: str = Field(default="piece", description="Unit of measurement")


class JobExtraction(BaseModel):
    """Structured data extracted from a voice transcript by GPT."""
    customer_name: str | None = Field(default="Unknown", description="Customer or client name")
    job_type: str | None = Field(default="General", description="Type of work performed (e.g., plumbing, electrical)")
    materials_used: list[MaterialUsed] = Field(default_factory=list, description="Materials consumed")
    labor_hours: float | None = Field(default=0.0, ge=0, description="Hours of labor performed")
    follow_up_date: str | None = Field(default=None, description="Follow-up date (ISO format or relative like '6 months')")
    follow_up_reason: str | None = Field(default=None, description="Reason for follow-up")
    invoice_required: bool = Field(default=True, description="Whether an invoice should be generated")
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.85, description="Extraction confidence 0-1")
    raw_transcript: str = Field(default="", description="Original transcript text")


# --- Tool Execution Schemas ---

class ToolResult(BaseModel):
    """Result of a single tool execution."""
    tool_name: str
    success: bool
    message: str
    data: dict | None = None


class AgentStep(BaseModel):
    """A single step in the agent's reasoning trace."""
    step_number: int
    action: str
    reasoning: str
    tool_name: str | None = None
    result: ToolResult | None = None
class AgentTraceStep(BaseModel):
    step: str
    before: dict | None = None
    after: dict | None = None
    amount: float | None = None
    due_date: str | None = None


class ExecutionSummary(BaseModel):
    job_logged: bool = False
    inventory_updated: bool = False
    invoice_generated: bool = False
    followup_scheduled: bool = False
    revenue_added: float = 0.0
    low_stock_items: list[str] = Field(default_factory=list)
    next_followup_date: str | None = None


class AgentResult(BaseModel):
    """Full result of the agent orchestration workflow."""
    extraction: JobExtraction
    steps: list[AgentStep] = Field(default_factory=list)
    tools_executed: list[str] = Field(default_factory=list)
    success: bool = True
    summary: str = ""
    execution: ExecutionSummary = Field(default_factory=ExecutionSummary)
    agent_trace: list[AgentTraceStep] = Field(default_factory=list)


# --- API Response Schemas ---

class VoiceResponse(BaseModel):
    """Response from the voice processing endpoint."""
    transcript: str
    extraction: JobExtraction
    agent_result: AgentResult
    execution: ExecutionSummary
    agent_trace: list[AgentTraceStep] = Field(default_factory=list)

class JobResponse(BaseModel):
    """Job data for API responses."""
    id: int
    customer_name: str | None
    job_type: str | None
    materials_used: list[dict]
    labor_hours: float | None
    status: str
    confidence_score: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardSummary(BaseModel):
    """Dashboard overview data."""
    total_jobs_today: int = 0
    total_revenue_today: float = 0.0
    total_revenue_week: float = 0.0
    total_revenue_month: float = 0.0
    low_stock_items: list[dict] = Field(default_factory=list)
    upcoming_followups: list[dict] = Field(default_factory=list)
    recent_jobs: list[dict] = Field(default_factory=list)


class InventoryItem(BaseModel):
    """Inventory item for API response."""
    id: int
    item_name: str
    quantity: int
    unit: str
    unit_cost: float
    is_low_stock: bool = False

    model_config = ConfigDict(from_attributes=True)


class FollowUpResponse(BaseModel):
    """Follow-up for API response."""
    id: int
    customer_name: str
    scheduled_date: date
    reason: str
    status: str
    job_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
