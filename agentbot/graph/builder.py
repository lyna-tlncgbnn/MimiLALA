"""Build the supervisor-first main graph."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agentbot.graph.nodes import (
    call_browser_subgraph,
    execute_tools,
    respond,
    supervisor,
    tool_chatbot,
)
from agentbot.graph.routes import route_after_supervisor, route_after_tool_chatbot
from agentbot.graph.state import AgentGraphState
from agentbot.tools.error_handling import format_tool_error
from agentbot.tools.registry import get_registered_tools


def build_graph(llm: BaseChatModel, *, llm_config: dict | None = None):
    """Build the supervisor-first graph."""
    tools = get_registered_tools()
    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools, handle_tool_errors=format_tool_error)

    graph = StateGraph(AgentGraphState)
    graph.add_node("supervisor", lambda state: supervisor(state, llm))
    graph.add_node("respond", respond)
    graph.add_node("tool_chatbot", lambda state: tool_chatbot(state, llm_with_tools))
    graph.add_node("tools", lambda state: execute_tools(state, tool_node))
    graph.add_node(
        "browser",
        lambda state: call_browser_subgraph(
            state,
            llm,
            llm_config=llm_config,
        ),
    )
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {"respond": "respond", "tool_chatbot": "tool_chatbot", "browser": "browser"},
    )
    graph.add_conditional_edges(
        "tool_chatbot",
        route_after_tool_chatbot,
        {"tools": "tools", "__end__": END},
    )
    graph.add_edge("tools", "supervisor")
    graph.add_edge("browser", "supervisor")
    graph.add_edge("respond", END)
    return graph.compile()
