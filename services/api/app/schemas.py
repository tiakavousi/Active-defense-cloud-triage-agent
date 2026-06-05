"""Pydantic models for request/response."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


class LogOut(BaseModel):
    id: UUID
    ts: datetime
    user_id: str
    source_ip: str
    geo_country: str
    action: str
    resource: str | None = None
    bytes_out: int
    status: str
    user_agent: str
    mfa_used: bool
    is_anomaly_truth: bool
    anomaly_kind: str | None = None
    anomaly_score: float | None = None
    score_reasons: dict[str, Any] | None = None
    flagged: bool
    investigated: bool


class BaselineOut(BaseModel):
    user_id: str
    typical_hours: list[int]
    typical_countries: list[str]
    typical_ips: list[str]
    typical_user_agents: list[str]
    action_counts: dict[str, int]
    mean_bytes_out: float
    stddev_bytes_out: float
    sample_size: int
    updated_at: datetime


class PeerActivity(BaseModel):
    role: str
    user_count: int
    common_actions: dict[str, int]
    common_countries: list[str]
    mean_bytes_out: float


class IpReputation(BaseModel):
    ip: str
    is_known_bad: bool
    threat_categories: list[str] = Field(default_factory=list)
    asn: str | None = None
    country: str | None = None
    notes: str


class IncidentCreate(BaseModel):
    triggering_log_id: UUID
    user_id: str
    severity: str
    confidence: float
    summary: str
    recommended_action: str
    reasoning_trace: list[dict[str, Any]]
    status: str = "closed"


class IncidentOut(BaseModel):
    id: UUID
    triggering_log_id: UUID
    user_id: str
    severity: str
    confidence: float
    summary: str | None
    recommended_action: str | None
    reasoning_trace: list[dict[str, Any]]
    status: str
    created_at: datetime
    completed_at: datetime | None
