"""Browser subgraph assembly."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from agentbot.graph.browser_nodes import browser_act, browser_decide, browser_evaluate, browser_finish, browser_observe, browser_prepare
from agentbot.graph.browser_routes import route_after_browser_decide, route_after_browser_evaluate
from agentbot.graph.state import AgentGraphState


def build_browser_subgraph(llm: BaseChatModel):
    graph = StateGraph(AgentGraphState)
    graph.add_node("browser_prepare", browser_prepare)
    graph.add_node("browser_observe", browser_observe)
    graph.add_node("browser_decide", lambda state: browser_decide(state, llm))
    graph.add_node("browser_act", browser_act)
    graph.add_node("browser_evaluate", browser_evaluate)
    graph.add_node("browser_finish", browser_finish)
    graph.add_edge(START, "browser_prepare")
    graph.add_edge("browser_prepare", "browser_observe")
    graph.add_edge("browser_observe", "browser_decide")
    graph.add_conditional_edges(
        "browser_decide",
        route_after_browser_decide,
        {
            "browser_act": "browser_act",
            "browser_finish": "browser_finish",
        },
    )
    graph.add_edge("browser_act", "browser_evaluate")
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
