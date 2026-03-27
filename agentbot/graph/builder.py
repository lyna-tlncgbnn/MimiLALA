"""Build the current minimal agent loop graph."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agentbot.graph.nodes import chatbot
from agentbot.graph.routes import route_after_chatbot
from agentbot.graph.state import MessagesState
from agentbot.tools.registry import get_registered_tools


def build_graph(llm: BaseChatModel):
    """Build the minimal agent loop with model -> tools -> model."""
    tools = get_registered_tools()
    llm_with_tools = llm.bind_tools(tools)

    graph = StateGraph(MessagesState)
    graph.add_node("chatbot", lambda state: chatbot(state, llm_with_tools))
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "chatbot")
    graph.add_conditional_edges(
        "chatbot",
        route_after_chatbot,
        {"tools": "tools", "__end__": END},
    )
    graph.add_edge("tools", "chatbot")
    return graph.compile()
