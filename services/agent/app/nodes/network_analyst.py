"""Network analyst: ReAct-style sub-agent focused on network signals."""
from __future__ import annotations

import json
import logging
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from ..state import InvestigationState
from ..prompts import NETWORK_SYSTEM
from ..tools import NETWORK_TOOLS
from ..llm import get_llm

log = logging.getLogger("network")
MAX_STEPS = int(os.environ.get("AGENT_MAX_TOOL_CALLS", 8))


def _build_agent():
    return create_react_agent(get_llm(), tools=NETWORK_TOOLS)


def network_analyst(state: InvestigationState) -> InvestigationState:
    agent = _build_agent()
    trigger = state["trigger"]

    user_msg = (
        f"Investigate this flagged event from the network angle.\n\n"
        f"Triggering event:\n{json.dumps(trigger, default=str, indent=2)}\n\n"
        f"Use your tools (IP reputation, history, baseline) to gather evidence, "
        f"then write your one-paragraph finding."
    )

    result = agent.invoke(
        {"messages": [SystemMessage(content=NETWORK_SYSTEM), HumanMessage(content=user_msg)]},
        config={"recursion_limit": MAX_STEPS * 3},
    )
    final = result["messages"][-1].content if result["messages"] else ""
    tool_calls = [m for m in result["messages"] if getattr(m, "tool_calls", None)]

    trace_entry = {
        "step": "network_analyst",
        "tool_invocations": [
            {"name": tc["name"], "args": tc["args"]}
            for m in tool_calls for tc in m.tool_calls
        ],
        "finding": final,
    }
    trace = state.get("trace", []) + [trace_entry]
    return {**state, "network_findings": final, "trace": trace}
