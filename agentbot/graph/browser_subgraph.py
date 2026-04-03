"""Browser subgraph assembly."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from agentbot.graph.browser_nodes import (
    browser_act_safe,
    browser_decide_safe,
    browser_evaluate_safe,
    browser_finish,
    browser_observe_safe,
    browser_prepare_safe,
)
from agentbot.graph.browser_routes import (
    route_after_browser_act,
    route_after_browser_decide,
    route_after_browser_evaluate,
    route_after_browser_observe,
    route_after_browser_prepare,
)
from agentbot.graph.state import AgentGraphState


def build_browser_subgraph(llm: BaseChatModel):
    graph = StateGraph(AgentGraphState)
    graph.add_node("browser_prepare", browser_prepare_safe)
    graph.add_node("browser_observe", browser_observe_safe)
    graph.add_node("browser_decide", lambda state: browser_decide_safe(state, llm))
    graph.add_node("browser_act", browser_act_safe)
    graph.add_node("browser_evaluate", browser_evaluate_safe)
    graph.add_node("browser_finish", browser_finish)
    graph.add_edge(START, "browser_prepare")
    graph.add_conditional_edges(
        "browser_prepare",
        route_after_browser_prepare,
        {
            "browser_observe": "browser_observe",
            "browser_finish": "browser_finish",
        },
    )
    graph.add_conditional_edges(
        "browser_observe",
        route_after_browser_observe,
        {
            "browser_decide": "browser_decide",
            "browser_finish": "browser_finish",
        },
    )
    graph.add_conditional_edges(
        "browser_decide",
        route_after_browser_decide,
        {
            "browser_act": "browser_act",
            "browser_finish": "browser_finish",
        },
    )
    graph.add_conditional_edges(
        "browser_act",
        route_after_browser_act,
        {
            "browser_evaluate": "browser_evaluate",
            "browser_finish": "browser_finish",
        },
    )
    graph.add_conditional_edges(
        "browser_evaluate",
        route_after_browser_evaluate,
        {
            "browser_observe": "browser_observe",
            "browser_finish": "browser_finish",
        },
    )
    graph.add_edge("browser_finish", END)
    return graph.compile()
