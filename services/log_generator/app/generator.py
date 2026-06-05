"""Streaming generator for normal events."""
from __future__ import annotations

import random
from datetime import datetime

from .profiles import UserProfile


def synth_normal_event(user: UserProfile, now: datetime, rng: random.Random) -> dict:
    hour = now.hour
    in_hours = user.work_hours_start <= hour < user.work_hours_end
    if not in_hours and rng.random() > 0.05:
        now = now.replace(hour=rng.randint(user.work_hours_start, user.work_hours_end - 1))

    action = rng.choices(user.actions, weights=_action_weights(user.actions), k=1)[0]
    bytes_out = max(0, int(rng.gauss(user.bytes_mean, user.bytes_sd)))
    if action in ("login", "assume_role"):
        bytes_out = rng.randint(100, 2_000)

    status = "success" if rng.random() > 0.02 else "failure"

    return {
        "ts": now,
        "user_id": user.user_id,
        "source_ip": user.random_home_ip(),
        "geo_country": user.home_country,
        "action": action,
        "resource": f"arn:aws:s3:::bucket-{rng.randint(1, 20)}/key-{rng.randint(1, 9999)}" if action != "login" else None,
        "bytes_out": bytes_out,
        "status": status,
        "user_agent": user.typical_user_agent,
        "mfa_used": True,
        "is_anomaly_truth": False,
        "anomaly_kind": None,
    }


def _action_weights(actions: list[str]) -> list[float]:
    weights = []
    for a in actions:
        if a == "login":
            weights.append(1.0)
        elif a in ("get_object", "list_buckets", "describe_instances"):
            weights.append(4.0)
        elif a in ("assume_role", "create_user", "attach_policy"):
            weights.append(0.3)
        else:
            weights.append(2.0)
    return weights
