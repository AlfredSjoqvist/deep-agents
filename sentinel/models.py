"""Shared Pydantic models for the Sentinel breach response pipeline."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class IncidentType(str, Enum):
    """Classification of incident types detected in breach data."""

    CREDENTIAL_STUFFING = "credential_stuffing"
    PHISHING = "phishing"
    RANSOMWARE = "ransomware"
    INSIDER_THREAT = "insider_threat"
    EXPOSED_API = "exposed_api"
    SQL_INJECTION = "sql_injection"
    MALWARE = "malware"
    MITM = "man_in_the_middle"
    PHYSICAL_THEFT = "physical_theft"
    UNKNOWN = "unknown"


class SeverityLevel(str, Enum):
    """Severity classification for incidents."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PipelineEvent(BaseModel):
    """A single event emitted during pipeline execution."""

    type: str  # setup, ingest, matching, research, lockdown, notify, complete, error
    message: str
    timestamp: float
    data: dict = {}
    phase: str = ""  # which phase: ingest, research, respond


class IncidentReport(BaseModel):
    """Structured incident report produced by the research phase."""

    breach_source: str = ""
    incident_type: IncidentType = IncidentType.UNKNOWN
    attack_vector: str = ""
    cve_id: str = ""
    affected_software: str = ""
    affected_version: str = ""
    severity: SeverityLevel = SeverityLevel.HIGH
    recommended_patches: list[str] = []
    data_classes_exposed: list[str] = []  # PII, credentials, financial, etc.
    estimated_records: int = 0
    summary: str = ""


class SentinelResult(BaseModel):
    """Complete result of a Sentinel pipeline run."""

    run_id: str = ""
    status: str = "pending"
    start_time: float = 0.0
    end_time: float = 0.0
    duration_seconds: float = 0.0

    # Phase 1
    total_breach_records: int = 0
    total_matches: int = 0
    critical_count: int = 0
    warning_count: int = 0

    # Phase 2
    incident_report: dict = {}
    incident_type: str = "unknown"

    # Phase 3
    accounts_locked: int = 0
    sessions_revoked: int = 0
    calls_initiated: int = 0
    lock_failures: int = 0
    call_failures: int = 0
