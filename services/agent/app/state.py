"""Shared investigation state."""
from __future__ import annotations

from typing import Any, TypedDict


class InvestigationState(TypedDict, total=False):
    trigger: dict[str, Any]          # flagged log event
    user_id: str
    user_role: dict[str, Any]
    baseline: dict[str, Any] | None
    identity_findings: str
    network_findings: str
    trace: list[dict[str, Any]]
    final_report: dict[str, Any]
