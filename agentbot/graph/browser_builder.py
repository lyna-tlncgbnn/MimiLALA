"""Build the browser subgraph used for explicit browser tasks."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from agentbot.graph.browser_nodes import (
    browser_act,
    browser_enter,
    browser_finish,
    browser_observe,
    browser_plan,
)
from agentbot.graph.browser_routes import route_after_browser_act, route_after_browser_plan
from agentbot.graph.browser_state import BrowserSubgraphState


def build_browser_graph(llm: BaseChatModel):
    """Compile the minimal browser subgraph for explicit browser tasks."""
    graph = StateGraph(BrowserSubgraphState)
    graph.add_node("browser_enter", browser_enter)
    graph.add_node("browser_observe", browser_observe)
    graph.add_node("browser_plan", lambda state: browser_plan(state, llm))
    graph.add_node("browser_act", browser_act)
    graph.add_node("browser_finish", browser_finish)
    graph.add_edge(START, "browser_enter")
    graph.add_edge("browser_enter", "browser_observe")
    graph.add_edge("browser_observe", "browser_plan")
    graph.add_conditional_edges(
        "browser_plan",
        route_after_browser_plan,
        {
            "act": "browser_act",
            "finish": "browser_finish",
        },
    )
    graph.add_conditional_edges(
        "browser_act",
        route_after_browser_act,
        {
            "observe": "browser_observe",
            "finish": "browser_finish",
        },
    )
    graph.add_edge("browser_finish", END)
    return graph.compile()
