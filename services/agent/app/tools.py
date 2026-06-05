"""LangChain tools that wrap the FastAPI tool endpoints."""
from __future__ import annotations

import os
import httpx
from langchain_core.tools import tool

API_HOST = os.environ["API_HOST"]
_client = httpx.Client(base_url=API_HOST, timeout=20.0)


@tool
def get_user_history(user_id: str, hours: int = 24) -> list[dict]:
    """Return recent log events for a user over the last N hours (max 168).
    Use to compare the suspect event against the user's own recent behavior."""
    r = _client.get("/tools/user_history", params={"user_id": user_id, "hours": hours, "limit": 50})
    r.raise_for_status()
    return r.json()


@tool
def get_user_baseline(user_id: str) -> dict:
    """Return the learned baseline for a user: typical hours, countries, IPs,
    user-agents, mean/stddev bytes-out, action histogram. Use to define 'normal'."""
    r = _client.get(f"/tools/user_baseline/{user_id}")
    r.raise_for_status()
    return r.json()


@tool
def get_user_role(user_id: str) -> dict:
    """Return the user's role, home country, and working hours."""
    r = _client.get(f"/tools/user_role/{user_id}")
    r.raise_for_status()
    return r.json()


@tool
def get_peer_activity(role: str, hours: int = 24) -> dict:
    """Return aggregated activity stats for peers in the same role. Use to check
    whether the suspect behavior is normal for that role overall."""
    r = _client.get("/tools/peer_activity", params={"role": role, "hours": hours})
    r.raise_for_status()
    return r.json()


@tool
def get_ip_reputation(ip: str) -> dict:
    """Look up IP threat-intel: is_known_bad, threat_categories, ASN, country."""
    r = _client.get("/tools/ip_reputation", params={"ip": ip})
    r.raise_for_status()
    return r.json()


IDENTITY_TOOLS = [get_user_history, get_user_baseline, get_user_role, get_peer_activity]
NETWORK_TOOLS = [get_ip_reputation, get_user_history, get_user_baseline]
