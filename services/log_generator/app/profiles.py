"""Per-user behavioral profiles for the synthetic cloud environment."""
from __future__ import annotations

import random
from dataclasses import dataclass

ROLES = {
    "engineer":    {"actions": ["login", "list_buckets", "get_object", "put_object", "describe_instances", "ssh_session"], "bytes_mean": 80_000, "bytes_sd": 25_000},
    "data_analyst": {"actions": ["login", "list_buckets", "get_object", "run_query", "export_dashboard"],                "bytes_mean": 250_000, "bytes_sd": 90_000},
    "admin":       {"actions": ["login", "assume_role", "create_user", "attach_policy", "describe_instances"],          "bytes_mean": 30_000, "bytes_sd": 15_000},
    "finance":     {"actions": ["login", "get_object", "list_buckets", "run_report"],                                   "bytes_mean": 60_000, "bytes_sd": 20_000},
    "support":     {"actions": ["login", "describe_instances", "get_object", "list_tickets"],                           "bytes_mean": 40_000, "bytes_sd": 12_000},
}

COUNTRIES = [
    ("US", "10.0."),
    ("US", "10.1."),
    ("DE", "10.2."),
    ("GB", "10.3."),
    ("IN", "10.4."),
    ("BR", "10.5."),
]

USER_AGENTS = [
    "aws-cli/2.15.0 Python/3.11.0 Linux/5.15",
    "Boto3/1.34.0 Python/3.11.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
    "terraform/1.7.0",
]


@dataclass
class UserProfile:
    user_id: str
    role: str
    home_country: str
    home_ip_prefix: str
    work_hours_start: int
    work_hours_end: int
    typical_user_agent: str
    actions: list[str]
    bytes_mean: int
    bytes_sd: int

    def random_home_ip(self) -> str:
        return f"{self.home_ip_prefix}{random.randint(0, 255)}.{random.randint(1, 254)}"


def build_user_population(n: int, seed: int = 42) -> list[UserProfile]:
    rng = random.Random(seed)
    roles = list(ROLES.keys())
    profiles: list[UserProfile] = []
    for i in range(n):
        role = rng.choice(roles)
        country, prefix = rng.choice(COUNTRIES)
        wh_start = rng.choice([7, 8, 9])
        wh_end = wh_start + rng.choice([8, 9, 10])
        profiles.append(
            UserProfile(
                user_id=f"u_{i:03d}_{role}",
                role=role,
                home_country=country,
                home_ip_prefix=prefix,
                work_hours_start=wh_start,
                work_hours_end=wh_end,
                typical_user_agent=rng.choice(USER_AGENTS),
                actions=ROLES[role]["actions"],
                bytes_mean=ROLES[role]["bytes_mean"],
                bytes_sd=ROLES[role]["bytes_sd"],
            )
        )
    return profiles
