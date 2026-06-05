"""LangGraph wiring: context_loader -> identity & network (sequential) -> reporter."""
from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from .state import InvestigationState
from .nodes.context_loader import context_loader
from .nodes.identity_analyst import identity_analyst
from .nodes.network_analyst import network_analyst
from .nodes.reporter import reporter


def build_graph():
    g = StateGraph(InvestigationState)
    g.add_node("context_loader", context_loader)
    g.add_node("identity_analyst", identity_analyst)
    g.add_node("network_analyst", network_analyst)
    g.add_node("reporter", reporter)

    g.add_edge(START, "context_loader")
    g.add_edge("context_loader", "identity_analyst")
    g.add_edge("identity_analyst", "network_analyst")
    g.add_edge("network_analyst", "reporter")
    g.add_edge("reporter", END)

    return g.compile()
