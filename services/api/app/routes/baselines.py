"""Baseline read endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..db import pool
from ..schemas import BaselineOut

router = APIRouter(prefix="/baselines", tags=["baselines"])


BASELINE_COLS = """user_id, typical_hours, typical_countries, typical_ips,
                   typical_user_agents, action_counts, mean_bytes_out,
                   stddev_bytes_out, sample_size, updated_at"""


def _row_to_baseline(row) -> dict:
    return {
        "user_id": row[0],
        "typical_hours": row[1] or [],
        "typical_countries": row[2] or [],
        "typical_ips": row[3] or [],
        "typical_user_agents": row[4] or [],
        "action_counts": row[5] or {},
        "mean_bytes_out": row[6] or 0.0,
        "stddev_bytes_out": row[7] or 0.0,
        "sample_size": row[8] or 0,
        "updated_at": row[9],
    }


@router.get("", response_model=list[BaselineOut])
def list_baselines() -> list[dict]:
    sql = f"SELECT {BASELINE_COLS} FROM baselines ORDER BY user_id"
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return [_row_to_baseline(r) for r in cur.fetchall()]


@router.get("/{user_id}", response_model=BaselineOut)
def get_baseline(user_id: str) -> dict:
    sql = f"SELECT {BASELINE_COLS} FROM baselines WHERE user_id = %s"
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "no baseline (insufficient data)")
    return _row_to_baseline(row)
