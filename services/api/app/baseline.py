"""Per-user baseline computation from recent log history."""
from __future__ import annotations

import json
import math
from collections import Counter
from psycopg import Connection

LOOKBACK_HOURS = 24
TOP_K_IPS = 8
TOP_K_UA = 4
MIN_SAMPLE = 20


SELECT_USERS_SQL = "SELECT DISTINCT user_id FROM logs WHERE ts > now() - interval '%s hours'"
SELECT_USER_EVENTS_SQL = """
SELECT ts, source_ip, geo_country, action, bytes_out, user_agent, status
FROM logs
WHERE user_id = %s AND ts > now() - interval '%s hours'
"""

UPSERT_BASELINE_SQL = """
INSERT INTO baselines (user_id, typical_hours, typical_countries, typical_ips,
                       typical_user_agents, action_counts,
                       mean_bytes_out, stddev_bytes_out, sample_size, updated_at)
VALUES (%(user_id)s, %(typical_hours)s, %(typical_countries)s, %(typical_ips)s,
        %(typical_user_agents)s, %(action_counts)s,
        %(mean_bytes_out)s, %(stddev_bytes_out)s, %(sample_size)s, now())
ON CONFLICT (user_id) DO UPDATE SET
    typical_hours       = EXCLUDED.typical_hours,
    typical_countries   = EXCLUDED.typical_countries,
    typical_ips         = EXCLUDED.typical_ips,
    typical_user_agents = EXCLUDED.typical_user_agents,
    action_counts       = EXCLUDED.action_counts,
    mean_bytes_out      = EXCLUDED.mean_bytes_out,
    stddev_bytes_out    = EXCLUDED.stddev_bytes_out,
    sample_size         = EXCLUDED.sample_size,
    updated_at          = now()
"""


def _mean_std(xs: list[float]) -> tuple[float, float]:
    if not xs:
        return 0.0, 0.0
    n = len(xs)
    mean = sum(xs) / n
    if n < 2:
        return mean, 0.0
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    return mean, math.sqrt(var)


def compute_baseline_for_user(conn: Connection, user_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(SELECT_USER_EVENTS_SQL, (user_id, LOOKBACK_HOURS))
        rows = cur.fetchall()
    if len(rows) < MIN_SAMPLE:
        return None

    hours = Counter()
    countries = Counter()
    ips = Counter()
    user_agents = Counter()
    actions = Counter()
    byte_samples: list[float] = []

    for ts, ip, geo, action, bytes_out, ua, status in rows:
        hours[ts.hour] += 1
        countries[geo] += 1
        ips[ip] += 1
        user_agents[ua] += 1
        actions[action] += 1
        byte_samples.append(float(bytes_out))

    mean, sd = _mean_std(byte_samples)

    typical_hours = [h for h, _ in hours.most_common() if hours[h] >= max(2, len(rows) // 48)]
    typical_countries = [c for c, _ in countries.most_common(3)]
    typical_ips = [ip for ip, _ in ips.most_common(TOP_K_IPS)]
    typical_user_agents = [ua for ua, _ in user_agents.most_common(TOP_K_UA)]

    return {
        "user_id": user_id,
        "typical_hours": typical_hours,
        "typical_countries": typical_countries,
        "typical_ips": typical_ips,
        "typical_user_agents": typical_user_agents,
        "action_counts": json.dumps(dict(actions)),
        "mean_bytes_out": mean,
        "stddev_bytes_out": sd,
        "sample_size": len(rows),
    }


def refresh_all_baselines(conn: Connection) -> int:
    with conn.cursor() as cur:
        cur.execute(SELECT_USERS_SQL, (LOOKBACK_HOURS,))
        user_ids = [r[0] for r in cur.fetchall()]

    n_written = 0
    for uid in user_ids:
        baseline = compute_baseline_for_user(conn, uid)
        if baseline is None:
            continue
        with conn.cursor() as cur:
            cur.execute(UPSERT_BASELINE_SQL, baseline)
        n_written += 1
    return n_written
