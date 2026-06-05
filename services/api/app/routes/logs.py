"""Log read endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from uuid import UUID

from ..db import pool
from ..schemas import LogOut

router = APIRouter(prefix="/logs", tags=["logs"])


LOG_COLS = """id, ts, user_id, source_ip, geo_country, action, resource,
              bytes_out, status, user_agent, mfa_used, is_anomaly_truth,
              anomaly_kind, anomaly_score, score_reasons, flagged, investigated"""


def _row_to_log(row) -> dict:
    keys = ["id", "ts", "user_id", "source_ip", "geo_country", "action", "resource",
            "bytes_out", "status", "user_agent", "mfa_used", "is_anomaly_truth",
            "anomaly_kind", "anomaly_score", "score_reasons", "flagged", "investigated"]
    return dict(zip(keys, row))


@router.get("/recent", response_model=list[LogOut])
def recent_logs(limit: int = Query(100, le=1000)) -> list[dict]:
    sql = f"SELECT {LOG_COLS} FROM logs ORDER BY ts DESC LIMIT %s"
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (limit,))
        return [_row_to_log(r) for r in cur.fetchall()]


@router.get("/flagged", response_model=list[LogOut])
def flagged_logs(investigated: bool | None = None, limit: int = Query(50, le=500)) -> list[dict]:
    base = f"SELECT {LOG_COLS} FROM logs WHERE flagged = TRUE"
    params: list = []
    if investigated is not None:
        base += " AND investigated = %s"
        params.append(investigated)
    base += " ORDER BY ts DESC LIMIT %s"
    params.append(limit)
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(base, params)
        return [_row_to_log(r) for r in cur.fetchall()]


@router.get("/{log_id}", response_model=LogOut)
def get_log(log_id: UUID) -> dict:
    sql = f"SELECT {LOG_COLS} FROM logs WHERE id = %s"
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (str(log_id),))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "log not found")
    return _row_to_log(row)


@router.post("/{log_id}/mark-investigated")
def mark_investigated(log_id: UUID) -> dict:
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("UPDATE logs SET investigated = TRUE WHERE id = %s", (str(log_id),))
    return {"ok": True}
