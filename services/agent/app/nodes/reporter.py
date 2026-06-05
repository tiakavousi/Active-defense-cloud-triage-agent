"""Reporter: synthesizes analyst findings into a final structured incident report."""
from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from ..state import InvestigationState
from ..prompts import REPORTER_SYSTEM
from ..llm import get_llm

log = logging.getLogger("reporter")


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        text = match.group(0)
    try:
        return json.loads(text)
    except Exception:
        log.warning("reporter returned non-JSON, falling back: %s", text[:200])
        return {
            "severity": "medium",
            "confidence": 0.4,
            "summary": "Reporter failed to produce valid JSON; raw output: " + text[:240],
            "recommended_action": "Manual review required.",
        }


def reporter(state: InvestigationState) -> InvestigationState:
    llm = get_llm()
    trigger = state["trigger"]
    user_msg = (
        f"Triggering event summary:\n{json.dumps(trigger, default=str, indent=2)}\n\n"
        f"Identity analyst finding:\n{state.get('identity_findings', '(none)')}\n\n"
        f"Network analyst finding:\n{state.get('network_findings', '(none)')}\n\n"
        f"Produce the final JSON report."
    )
    msgs = [SystemMessage(content=REPORTER_SYSTEM), HumanMessage(content=user_msg)]
    resp = llm.invoke(msgs)
    report = _extract_json(resp.content if hasattr(resp, "content") else str(resp))

    report.setdefault("severity", "medium")
    report.setdefault("confidence", 0.4)
    report.setdefault("summary", "")
    report.setdefault("recommended_action", "")
    try:
        report["confidence"] = max(0.0, min(1.0, float(report["confidence"])))
    except (TypeError, ValueError):
        report["confidence"] = 0.4

    trace = state.get("trace", []) + [{"step": "reporter", "report": report}]
    return {**state, "final_report": report, "trace": trace}
