"""Identity analyst: ReAct-style sub-agent focused on identity signals."""
from __future__ import annotations

import json
import logging
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from ..state import InvestigationState
from ..prompts import IDENTITY_SYSTEM
from ..tools import IDENTITY_TOOLS
from ..llm import get_llm

log = logging.getLogger("identity")
MAX_STEPS = int(os.environ.get("AGENT_MAX_TOOL_CALLS", 8))


def _build_agent():
    return create_react_agent(get_llm(), tools=IDENTITY_TOOLS)


def identity_analyst(state: InvestigationState) -> InvestigationState:
    agent = _build_agent()
    trigger = state["trigger"]
    role = state.get("user_role", {}).get("role", "unknown")

    user_msg = (
        f"Investigate this flagged event from the identity angle.\n\n"
        f"Triggering event:\n{json.dumps(trigger, default=str, indent=2)}\n\n"
        f"User role: {role}\n"
        f"Use your tools to gather evidence, then write your one-paragraph finding."
    )

    result = agent.invoke(
        {"messages": [SystemMessage(content=IDENTITY_SYSTEM), HumanMessage(content=user_msg)]},
        config={"recursion_limit": MAX_STEPS * 3},
    )
    final = result["messages"][-1].content if result["messages"] else ""
    tool_calls = [m for m in result["messages"] if getattr(m, "tool_calls", None)]

    trace_entry = {
        "step": "identity_analyst",
        "tool_invocations": [
            {"name": tc["name"], "args": tc["args"]}
            for m in tool_calls for tc in m.tool_calls
        ],
        "finding": final,
    }
    trace = state.get("trace", []) + [trace_entry]
    return {**state, "identity_findings": final, "trace": trace}
