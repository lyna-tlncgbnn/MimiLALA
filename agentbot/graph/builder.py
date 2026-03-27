"""Build the minimal Phase 1 graph."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from agentbot.graph.nodes import chatbot
from agentbot.graph.state import MessagesState


def build_graph(llm: BaseChatModel):
    """Build the minimal START -> chatbot -> END graph."""
    graph = StateGraph(MessagesState)
    graph.add_node("chatbot", lambda state: chatbot(state, llm))
    graph.add_edge(START, "chatbot")
    graph.add_edge("chatbot", END)
    return graph.compile()

