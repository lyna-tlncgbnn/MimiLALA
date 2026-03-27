"""Graph nodes for the current minimal agent."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langgraph.prebuilt import ToolNode

from agentbot.graph.state import MessagesState


def chatbot(state: MessagesState, llm: BaseChatModel):
    """Run the real chat model against the current message list."""
    try:
        response = llm.invoke(state["messages"])
    except Exception as exc:
        raise RuntimeError(f"Model execution failed: {exc}") from exc
    if not isinstance(response, AIMessage):
        raise TypeError(f"Expected AIMessage from chat model, got {type(response).__name__}")
    return {"messages": [response]}


def execute_tools(state: MessagesState, tool_node: ToolNode):
    """Run the tool node with a clearer error boundary."""
    try:
        return tool_node.invoke(state)
    except Exception as exc:
        raise RuntimeError(f"Tool execution failed: {exc}") from exc
