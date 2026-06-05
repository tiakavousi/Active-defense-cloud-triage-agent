"""Streaming log generator: seeds users, emits a continuous mix of normal + anomalous events."""
from __future__ import annotations

import os
import random
import time
from datetime import datetime, timezone

import psycopg

from .anomalies import synth_anomalous_event
from .generator import synth_normal_event
from .profiles import UserProfile, build_user_population


DSN = (
    f"host={os.environ['POSTGRES_HOST']} port={os.environ['POSTGRES_PORT']} "
    f"user={os.environ['POSTGRES_USER']} password={os.environ['POSTGRES_PASSWORD']} "
    f"dbname={os.environ['POSTGRES_DB']}"
)

EVENTS_PER_SECOND = float(os.environ.get("GEN_EVENTS_PER_SECOND", 8))
NUM_USERS = int(os.environ.get("GEN_NUM_USERS", 25))
ANOMALY_RATE = float(os.environ.get("GEN_ANOMALY_RATE", 0.04))
WARMUP_SECONDS = int(os.environ.get("GEN_WARMUP_SECONDS", 60))


INSERT_USER_SQL = """
INSERT INTO simulated_users (user_id, role, home_country, home_ip_prefix,
                             work_hours_start, work_hours_end, typical_user_agent)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (user_id) DO NOTHING
"""

INSERT_LOG_SQL = """
INSERT INTO logs (ts, user_id, source_ip, geo_country, action, resource,
                  bytes_out, status, user_agent, mfa_used,
                  is_anomaly_truth, anomaly_kind)
VALUES (%(ts)s, %(user_id)s, %(source_ip)s, %(geo_country)s, %(action)s, %(resource)s,
        %(bytes_out)s, %(status)s, %(user_agent)s, %(mfa_used)s,
        %(is_anomaly_truth)s, %(anomaly_kind)s)
"""


def seed_users(conn: psycopg.Connection, users: list[UserProfile]) -> None:
    with conn.cursor() as cur:
        for u in users:
            cur.execute(
                INSERT_USER_SQL,
                (u.user_id, u.role, u.home_country, u.home_ip_prefix,
                 u.work_hours_start, u.work_hours_end, u.typical_user_agent),
            )
    conn.commit()


def main() -> None:
    rng = random.Random()
    users = build_user_population(NUM_USERS)

    print(f"[log_generator] connecting to {DSN.split('password=')[0]}...", flush=True)
    with psycopg.connect(DSN, autocommit=False) as conn:
        seed_users(conn, users)
        print(f"[log_generator] seeded {len(users)} users", flush=True)

        interval = 1.0 / EVENTS_PER_SECOND
        warmup_until = time.monotonic() + WARMUP_SECONDS
        emitted = 0
        anomalies = 0

        while True:
            user = rng.choice(users)
            now = datetime.now(timezone.utc)

            in_warmup = time.monotonic() < warmup_until
            effective_rate = 0.0 if in_warmup else ANOMALY_RATE

            if rng.random() < effective_rate:
                event = synth_anomalous_event(user, now, rng)
                anomalies += 1
            else:
                event = synth_normal_event(user, now, rng)

            with conn.cursor() as cur:
                cur.execute(INSERT_LOG_SQL, event)
            conn.commit()

            emitted += 1
            if emitted % 100 == 0:
                print(f"[log_generator] emitted={emitted} anomalies={anomalies} warmup={in_warmup}", flush=True)

            time.sleep(interval)


if __name__ == "__main__":
    main()
