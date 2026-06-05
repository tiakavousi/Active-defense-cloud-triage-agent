"""Anomaly injection: distinct kinds of malicious-looking behavior."""
from __future__ import annotations

import random
from datetime import datetime, timezone

from .profiles import UserProfile

EXOTIC_COUNTRIES = [
    ("RU", "185.220."),
    ("CN", "117.50."),
    ("IR", "5.160."),
    ("KP", "175.45."),
    ("NG", "197.210."),
]

SUSPICIOUS_USER_AGENTS = [
    "curl/7.88.1",
    "python-requests/2.31.0",
    "Go-http-client/1.1",
    "",
]

ANOMALY_KINDS = [
    "impossible_travel",
    "off_hours_privilege_escalation",
    "data_exfil_spike",
    "credential_stuffing",
    "unusual_user_agent",
]


def synth_anomalous_event(user: UserProfile, now: datetime, rng: random.Random) -> dict:
    kind = rng.choice(ANOMALY_KINDS)

    base = {
        "ts": now,
        "user_id": user.user_id,
        "source_ip": user.random_home_ip(),
        "geo_country": user.home_country,
        "action": rng.choice(user.actions),
        "resource": f"arn:aws:s3:::bucket-{rng.randint(1, 20)}/key-{rng.randint(1, 9999)}",
        "bytes_out": max(0, int(rng.gauss(user.bytes_mean, user.bytes_sd))),
        "status": "success",
        "user_agent": user.typical_user_agent,
        "mfa_used": True,
        "is_anomaly_truth": True,
        "anomaly_kind": kind,
    }

    if kind == "impossible_travel":
        country, prefix = rng.choice(EXOTIC_COUNTRIES)
        base["geo_country"] = country
        base["source_ip"] = f"{prefix}{rng.randint(0, 255)}.{rng.randint(1, 254)}"

    elif kind == "off_hours_privilege_escalation":
        base["ts"] = now.replace(hour=rng.choice([2, 3, 4]), minute=rng.randint(0, 59))
        base["action"] = rng.choice(["assume_role", "attach_policy", "create_user", "put_user_policy"])
        base["mfa_used"] = False

    elif kind == "data_exfil_spike":
        base["action"] = "get_object"
        base["bytes_out"] = int(rng.uniform(50, 500) * max(user.bytes_mean, 50_000))

    elif kind == "credential_stuffing":
        country, prefix = rng.choice(EXOTIC_COUNTRIES)
        base["geo_country"] = country
        base["source_ip"] = f"{prefix}{rng.randint(0, 255)}.{rng.randint(1, 254)}"
        base["action"] = "login"
        base["status"] = "failure"
        base["mfa_used"] = False

    elif kind == "unusual_user_agent":
        base["user_agent"] = rng.choice(SUSPICIOUS_USER_AGENTS)

    return base
