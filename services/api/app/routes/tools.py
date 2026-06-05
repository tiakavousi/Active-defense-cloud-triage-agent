"""Agent-facing tool endpoints. The LangGraph agent calls these during investigations."""
from __future__ import annotations

import hashlib
from collections import Counter
from fastapi import APIRouter, HTTPException, Query

from ..db import pool
from ..schemas import PeerActivity, IpReputation, BaselineOut

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/user_history")
def user_history(user_id: str, hours: int = Query(24, le=168), limit: int = Query(50, le=500)) -> list[dict]:
    sql = """
    SELECT id, ts, source_ip, geo_country, action, resource, bytes_out, status,
           user_agent, mfa_used, anomaly_score
    FROM logs
    WHERE user_id = %s AND ts > now() - (%s || ' hours')::interval
    ORDER BY ts DESC LIMIT %s
    """
    keys = ["id", "ts", "source_ip", "geo_country", "action", "resource",
            "bytes_out", "status", "user_agent", "mfa_used", "anomaly_score"]
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (user_id, str(hours), limit))
        return [dict(zip(keys, r)) for r in cur.fetchall()]


@router.get("/peer_activity", response_model=PeerActivity)
def peer_activity(role: str, hours: int = Query(24, le=168)) -> dict:
    sql = """
    SELECT l.action, l.geo_country, l.bytes_out, l.user_id
    FROM logs l
    JOIN simulated_users u ON u.user_id = l.user_id
    WHERE u.role = %s AND l.ts > now() - (%s || ' hours')::interval
    """
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (role, str(hours)))
        rows = cur.fetchall()
    if not rows:
        raise HTTPException(404, f"no peer activity for role={role}")

    actions = Counter(r[0] for r in rows)
    countries = Counter(r[1] for r in rows)
    users = set(r[3] for r in rows)
    byte_vals = [r[2] for r in rows]
    return {
        "role": role,
        "user_count": len(users),
        "common_actions": dict(actions.most_common(8)),
        "common_countries": [c for c, _ in countries.most_common(5)],
        "mean_bytes_out": sum(byte_vals) / len(byte_vals),
    }


@router.get("/ip_reputation", response_model=IpReputation)
def ip_reputation(ip: str) -> dict:
    """Mocked threat intel: deterministic per-IP for reproducibility."""
    h = hashlib.sha256(ip.encode()).digest()
    is_bad = h[0] < 40 or ip.startswith(("185.220.", "117.50.", "5.160.", "175.45.", "197.210."))
    categories: list[str] = []
    if ip.startswith("185.220."):
        categories.append("tor_exit_node")
    if ip.startswith(("117.50.", "5.160.")):
        categories.append("known_botnet_c2")
    if ip.startswith(("175.45.", "197.210.")):
        categories.append("malware_distribution")
    if is_bad and not categories:
        categories.append("anomalous_reputation")

    asn_seed = int.from_bytes(h[1:3], "big")
    return {
        "ip": ip,
        "is_known_bad": is_bad,
        "threat_categories": categories,
        "asn": f"AS{10_000 + asn_seed % 40_000}",
        "country": _country_from_ip(ip),
        "notes": "mocked threat intel — deterministic per IP" + (" (FLAGGED)" if is_bad else ""),
    }


def _country_from_ip(ip: str) -> str:
    prefix_map = {
        "10.0.": "US", "10.1.": "US", "10.2.": "DE", "10.3.": "GB", "10.4.": "IN", "10.5.": "BR",
        "185.220.": "RU", "117.50.": "CN", "5.160.": "IR", "175.45.": "KP", "197.210.": "NG",
    }
    for prefix, country in prefix_map.items():
        if ip.startswith(prefix):
            return country
    return "??"


@router.get("/user_baseline/{user_id}", response_model=BaselineOut)
def user_baseline(user_id: str) -> dict:
    from .baselines import get_baseline
    return get_baseline(user_id)


@router.get("/user_role/{user_id}")
def user_role(user_id: str) -> dict:
    sql = "SELECT role, home_country, work_hours_start, work_hours_end FROM simulated_users WHERE user_id = %s"
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "user not found")
    return {
        "user_id": user_id,
        "role": row[0],
        "home_country": row[1],
        "work_hours_start": row[2],
        "work_hours_end": row[3],
    }
