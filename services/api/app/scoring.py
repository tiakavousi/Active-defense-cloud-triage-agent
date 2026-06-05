"""Statistical anomaly scoring against per-user baselines."""
from __future__ import annotations

import json
import math
import os
from psycopg import Connection
from psycopg.types.json import Json

THRESHOLD = float(os.environ.get("ANOMALY_FLAG_THRESHOLD", 0.75))

SELECT_UNSCORED_SQL = """
SELECT l.id, l.ts, l.user_id, l.source_ip, l.geo_country, l.action,
       l.bytes_out, l.user_agent, l.status, l.mfa_used,
       b.typical_hours, b.typical_countries, b.typical_ips,
       b.typical_user_agents, b.mean_bytes_out, b.stddev_bytes_out,
       b.sample_size
FROM logs l
LEFT JOIN baselines b ON b.user_id = l.user_id
WHERE l.anomaly_score IS NULL
ORDER BY l.ts ASC
LIMIT %s
"""

UPDATE_SCORE_SQL = """
UPDATE logs
SET anomaly_score = %s, score_reasons = %s, flagged = %s
WHERE id = %s
"""


def _z_score(x: float, mean: float, sd: float) -> float:
    if sd <= 1.0:
        return 0.0
    return abs(x - mean) / sd


def score_event(event: dict, baseline: dict | None) -> tuple[float, dict]:
    """Return (score in [0,1], reasons dict). No baseline → low score."""
    if baseline is None or baseline.get("sample_size", 0) < 20:
        return 0.0, {"note": "no baseline yet"}

    reasons: dict = {}
    contributions: list[float] = []

    if event["geo_country"] not in baseline["typical_countries"]:
        contributions.append(0.9)
        reasons["unfamiliar_country"] = event["geo_country"]

    if event["source_ip"] not in baseline["typical_ips"]:
        contributions.append(0.4)
        reasons["unfamiliar_ip"] = event["source_ip"]

    if event["user_agent"] not in baseline["typical_user_agents"]:
        contributions.append(0.55)
        reasons["unfamiliar_user_agent"] = event["user_agent"]

    if baseline["typical_hours"] and event["ts"].hour not in baseline["typical_hours"]:
        contributions.append(0.5)
        reasons["off_hours"] = event["ts"].hour

    z = _z_score(float(event["bytes_out"]), baseline["mean_bytes_out"], baseline["stddev_bytes_out"])
    if z > 3.0:
        contributions.append(min(0.95, 0.3 + 0.1 * z))
        reasons["bytes_out_zscore"] = round(z, 2)

    if event["action"] in ("assume_role", "attach_policy", "create_user", "put_user_policy") and not event["mfa_used"]:
        contributions.append(0.85)
        reasons["privilege_action_without_mfa"] = event["action"]

    if event["action"] == "login" and event["status"] == "failure":
        contributions.append(0.3)
        reasons["failed_login"] = True

    if not contributions:
        return 0.0, reasons

    score = 1.0 - math.prod(1.0 - c for c in contributions)
    return round(score, 3), reasons


def score_pending(conn: Connection, batch_size: int = 200) -> int:
    with conn.cursor() as cur:
        cur.execute(SELECT_UNSCORED_SQL, (batch_size,))
        rows = cur.fetchall()

    n = 0
    for row in rows:
        (log_id, ts, user_id, source_ip, geo, action,
         bytes_out, ua, status, mfa,
         typical_hours, typical_countries, typical_ips,
         typical_uas, mean_bytes, sd_bytes, sample_size) = row

        event = {
            "ts": ts, "user_id": user_id, "source_ip": source_ip,
            "geo_country": geo, "action": action, "bytes_out": bytes_out,
            "user_agent": ua, "status": status, "mfa_used": mfa,
        }
        baseline = None
        if sample_size:
            baseline = {
                "typical_hours": typical_hours or [],
                "typical_countries": typical_countries or [],
                "typical_ips": typical_ips or [],
                "typical_user_agents": typical_uas or [],
                "mean_bytes_out": mean_bytes or 0.0,
                "stddev_bytes_out": sd_bytes or 0.0,
                "sample_size": sample_size or 0,
            }

        score, reasons = score_event(event, baseline)
        flagged = score >= THRESHOLD

        with conn.cursor() as cur:
            cur.execute(UPDATE_SCORE_SQL, (score, Json(reasons), flagged, log_id))
        n += 1

    return n
