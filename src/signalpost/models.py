"""Pydantic v2 data models for claims, evidence, profiles, and result envelopes."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict

AvailabilityState = Literal[
    "available",
    "not_available",
    "blocked",
    "not_applicable",
    "ambiguous",
    "failed",
]


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    source_url: str
    source_class: str
    retrieved_at: str
    content_sha256: str
    claim_span: str | None = None
    effective_at: str | None = None
    reporting_period: str | None = None
    status: str = "available"
    note: str | None = None


class ClaimItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    field: str
    value: Any = None
    availability: AvailabilityState = "available"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_ids: list[str] = Field(default_factory=list)


class ChangeItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_id: str
    organisation_number: str
    field: str
    change_type: str
    old_value: Any = None
    new_value: Any = None
    effective_at: str | None = None
    detected_at: str
    old_evidence_id: str | None = None
    new_evidence_id: str | None = None
    old_content_sha256: str | None = None
    new_content_sha256: str | None = None
    source_url: str | None = None


class OperationsMetrics(BaseModel):
    model_config = ConfigDict(extra="ignore")

    requests: int = 0
    runtime_ms: int = 0
    third_party_cost_usd: float = 0.0
    bytes_downloaded: int = 0
    cache_hits: int = 0


class RunInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    run_id: str
    started_at: str
    completed_at: str
    terminal_status: str = "completed"


class TerminalEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")

    organisation_number: str
    run: RunInfo
    claims: list[ClaimItem] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    changes: list[ChangeItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    operations: OperationsMetrics = Field(default_factory=OperationsMetrics)


class CompanyProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    organisation_number: str
    name: str
    legal_form: str | None = None
    employees: int | None = None
    bankrupt: bool = False
    liquidating: bool = False
    municipality: str | None = None
    industry_code: str | None = None
    industry_label: str | None = None
    website: str | None = None
    latest_submitted_accounts: str | None = None
    summary: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    claims: list[ClaimItem] = Field(default_factory=list)
    changes: list[ChangeItem] = Field(default_factory=list)
