"""Agent worker: polls API for pending flagged events, runs LangGraph, posts incidents."""
from __future__ import annotations

import logging
import os
import time

import httpx

from .graph import build_graph

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("agent")

API_HOST = os.environ["API_HOST"]
POLL_SECONDS = int(os.environ.get("AGENT_POLL_SECONDS", 5))


def fetch_pending(client: httpx.Client) -> list[dict]:
    r = client.get("/logs/flagged", params={"investigated": False, "limit": 5})
    r.raise_for_status()
    return r.json()


def post_incident(client: httpx.Client, payload: dict) -> dict:
    r = client.post("/incidents", json=payload)
    r.raise_for_status()
    return r.json()


def investigate_one(graph, trigger: dict) -> dict:
    state = {
        "trigger": trigger,
        "user_id": trigger["user_id"],
        "trace": [],
    }
    log.info("investigating log_id=%s user=%s score=%s",
             trigger["id"], trigger["user_id"], trigger.get("anomaly_score"))
    result = graph.invoke(state)
    report = result.get("final_report", {})
    return {
        "triggering_log_id": trigger["id"],
        "user_id": trigger["user_id"],
        "severity": report.get("severity", "medium"),
        "confidence": report.get("confidence", 0.4),
        "summary": report.get("summary", ""),
        "recommended_action": report.get("recommended_action", ""),
        "reasoning_trace": result.get("trace", []),
        "status": "closed",
    }


def main() -> None:
    log.info("agent starting — poll_interval=%ss api=%s", POLL_SECONDS, API_HOST)
    graph = build_graph()

    with httpx.Client(base_url=API_HOST, timeout=120.0) as client:
        while True:
            try:
                pending = fetch_pending(client)
            except Exception:
                log.exception("failed to poll API")
                time.sleep(POLL_SECONDS)
                continue

            if not pending:
                time.sleep(POLL_SECONDS)
                continue

            for trigger in pending:
                try:
                    payload = investigate_one(graph, trigger)
                    incident = post_incident(client, payload)
                    log.info("posted incident=%s severity=%s confidence=%.2f",
                             incident["id"], incident["severity"], incident["confidence"])
                except Exception:
                    log.exception("investigation failed for log_id=%s", trigger.get("id"))
                    try:
                        client.post(f"/logs/{trigger['id']}/mark-investigated")
                    except Exception:
                        log.exception("failed to mark log investigated after error")


if __name__ == "__main__":
    main()
