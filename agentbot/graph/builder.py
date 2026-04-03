"""Build the current minimal agent loop graph."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agentbot.graph.browser_nodes import detect_browser_intent
from agentbot.graph.browser_subgraph import build_browser_subgraph
from agentbot.graph.nodes import browser_summary, chatbot, execute_tools
from agentbot.graph.routes import route_after_chatbot, route_after_intent
from agentbot.graph.state import MessagesState
from agentbot.tools.infra.error_handling import format_tool_error
from agentbot.tools.registry import get_registered_tools


def build_graph(
    llm: BaseChatModel,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
):
    """Build the minimal agent loop with model -> tools -> model."""
    tools = get_registered_tools()
    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools, handle_tool_errors=format_tool_error)
    browser_subgraph = build_browser_subgraph(llm)

    graph = StateGraph(MessagesState)
    graph.add_node("browser_intent", detect_browser_intent)
    graph.add_node("chatbot", lambda state: chatbot(state, llm_with_tools))
    graph.add_node("tools", lambda state: execute_tools(state, tool_node))
    graph.add_node("browser_subgraph", browser_subgraph)
    graph.add_node("browser_summary", lambda state: browser_summary(state, llm))
    graph.add_edge(START, "browser_intent")
    graph.add_conditional_edges(
        "browser_intent",
        route_after_intent,
        {
            "browser_subgraph": "browser_subgraph",
            "chatbot": "chatbot",
        },
    )
    graph.add_conditional_edges(
        "chatbot",
        route_after_chatbot,
        {"tools": "tools", "__end__": END},
    )
    graph.add_edge("tools", "chatbot")
    graph.add_edge("browser_subgraph", "browser_summary")
    graph.add_edge("browser_summary", END)
    return graph.compile(checkpointer=checkpointer)
