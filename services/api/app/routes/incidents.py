"""Incident endpoints — agent reports here, UI reads from here."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from psycopg.types.json import Json

from ..db import pool
from ..schemas import IncidentCreate, IncidentOut

router = APIRouter(prefix="/incidents", tags=["incidents"])


INCIDENT_COLS = """id, triggering_log_id, user_id, severity, confidence,
                   summary, recommended_action, reasoning_trace,
                   status, created_at, completed_at"""


def _row_to_incident(row) -> dict:
    keys = ["id", "triggering_log_id", "user_id", "severity", "confidence",
            "summary", "recommended_action", "reasoning_trace",
            "status", "created_at", "completed_at"]
    return dict(zip(keys, row))


@router.get("", response_model=list[IncidentOut])
def list_incidents(limit: int = Query(100, le=500),
                   severity: str | None = None) -> list[dict]:
    sql = f"SELECT {INCIDENT_COLS} FROM incidents"
    params: list = []
    if severity:
        sql += " WHERE severity = %s"
        params.append(severity)
    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return [_row_to_incident(r) for r in cur.fetchall()]


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: UUID) -> dict:
    sql = f"SELECT {INCIDENT_COLS} FROM incidents WHERE id = %s"
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (str(incident_id),))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "incident not found")
    return _row_to_incident(row)


@router.post("", response_model=IncidentOut, status_code=201)
def create_incident(payload: IncidentCreate) -> dict:
    sql = f"""
    INSERT INTO incidents (triggering_log_id, user_id, severity, confidence,
                           summary, recommended_action, reasoning_trace,
                           status, completed_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
    RETURNING {INCIDENT_COLS}
    """
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (
            str(payload.triggering_log_id), payload.user_id, payload.severity,
            payload.confidence, payload.summary, payload.recommended_action,
            Json(payload.reasoning_trace), payload.status,
        ))
        row = cur.fetchone()
        cur.execute("UPDATE logs SET investigated = TRUE WHERE id = %s",
                    (str(payload.triggering_log_id),))
    return _row_to_incident(row)
