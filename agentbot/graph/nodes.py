"""Graph nodes for Phase 1."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from agentbot.graph.state import MessagesState


def chatbot(state: MessagesState, llm: BaseChatModel):
    """Run the real chat model against the current message list."""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

