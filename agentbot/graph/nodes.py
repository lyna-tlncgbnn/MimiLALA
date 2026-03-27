"""Graph nodes for Phase 2."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage

from agentbot.graph.state import MessagesState


def chatbot(state: MessagesState, llm: BaseChatModel):
    """Run the real chat model against the current message list."""
    response = llm.invoke(state["messages"])
    if not isinstance(response, AIMessage):
        raise TypeError(f"Expected AIMessage from chat model, got {type(response).__name__}")
    return {"messages": [response]}
