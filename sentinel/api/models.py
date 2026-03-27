"""Pydantic models for the Sentinel API request/response contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Request Models ───────────────────────────────────────────────────────────


class TriggerRequest(BaseModel):
    """Body for POST /api/trigger."""
    breach_source: str = Field(default="DarkForum X", description="Name of the breach source")
    use_sample: bool = Field(default=True, description="Use built-in sample breach CSV")
    scenario_id: str | None = None  # "credential_stuffing", "phishing_campaign", or None for default


class CallRequest(BaseModel):
    """Body for POST /api/call — trigger a Bland AI test call."""
    phone_number: str = Field(..., description="E.164 phone number to call")
    user_name: str = Field(default="Test User", description="Name of the person being called")
    breach_details: str = Field(
        default="a credential stuffing attack",
        description="Human-readable breach description for the call script",
    )


# ── Response Models ──────────────────────────────────────────────────────────


class TriggerResponse(BaseModel):
    """Response from POST /api/trigger."""
    run_id: str
    status: str = "started"


class HealthResponse(BaseModel):
    """Response from GET /api/health."""
    status: str = "ok"
    service: str = "sentinel-api"


class IntegrationStatus(BaseModel):
    """Status of a single integration."""
    name: str
    status: str = Field(description="One of: active, partial, inactive")
    role: str = Field(description="Short description of what this integration does")
    detail: str = Field(default="", description="Optional detail about the check result")


class IntegrationsResponse(BaseModel):
    """Response from GET /api/integrations."""
    integrations: list[IntegrationStatus]


class SSEEvent(BaseModel):
    """Shape of each Server-Sent Event payload."""
    type: str
    message: str
    data: dict = Field(default_factory=dict)
    timestamp: float


class RunStatusResponse(BaseModel):
    """Response from GET /api/status/{run_id} — mirrors SentinelResult."""
    status: str = "pending"
    start_time: float = 0.0
    end_time: float = 0.0
    duration_seconds: float = 0.0

    total_breach_records: int = 0
    total_matches: int = 0
    critical_count: int = 0
    warning_count: int = 0

    incident_report: dict = Field(default_factory=dict)

    accounts_locked: int = 0
    sessions_revoked: int = 0
    calls_initiated: int = 0
    lock_failures: int = 0
    call_failures: int = 0

    events: list[dict] = Field(default_factory=list)


class CallResponse(BaseModel):
    """Response from POST /api/call."""
    status: str
    call_id: str = ""
    detail: str = ""
