"""Pulls user role + baseline into shared state before analysts run."""
from __future__ import annotations

import logging
import httpx
import os

from ..state import InvestigationState

API_HOST = os.environ["API_HOST"]
log = logging.getLogger("ctx")


def context_loader(state: InvestigationState) -> InvestigationState:
    user_id = state["user_id"]
    with httpx.Client(base_url=API_HOST, timeout=10.0) as c:
        role_resp = c.get(f"/tools/user_role/{user_id}")
        role = role_resp.json() if role_resp.status_code == 200 else {}
        bl_resp = c.get(f"/tools/user_baseline/{user_id}")
        baseline = bl_resp.json() if bl_resp.status_code == 200 else None

    trace = state.get("trace", []) + [{
        "step": "context_loader",
        "user_role": role.get("role"),
        "baseline_present": baseline is not None,
    }]
    return {**state, "user_role": role, "baseline": baseline, "trace": trace}
