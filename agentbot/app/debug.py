"""Minimal console debug helpers for the learning project."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool


@dataclass(slots=True)
class DebugPrinter:
    """Print concise debug summaries when debug mode is enabled."""

    enabled: bool = False

    def log(self, message: str) -> None:
        if self.enabled:
            print(f"[debug] {message}")

    def log_loaded_session(self, history: list[BaseMessage]) -> None:
        self.log(f"loaded session: {len(history)} messages")

    def log_registered_tools(self, tools: list[BaseTool]) -> None:
        names = ", ".join(tool.name for tool in tools) or "(none)"
        self.log(f"registered tools: {names}")

    def log_graph_started(self) -> None:
        self.log("graph execution started")

    def log_new_messages(self, messages: list[BaseMessage]) -> None:
        for message in messages:
            if isinstance(message, AIMessage):
                self.log("node=chatbot")
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        self.log(
                            "model emitted tool call: "
                            f"{tool_call.get('name')}({self._format_tool_args(tool_call.get('args'))})"
                        )
                else:
                    self.log(f"final answer: {self._summarize_content(message.content)}")
            elif isinstance(message, ToolMessage):
                self.log("node=tools")
                tool_name = message.name or "unknown_tool"
                self.log(
                    f"tool {tool_name} returned: {self._summarize_content(message.content)}"
                )

    def log_failure(self, stage: str, exc: Exception) -> None:
        self.log(f"{stage} failed: {exc}")

    @staticmethod
    def _format_tool_args(raw_args: Any) -> str:
        if isinstance(raw_args, dict):
            return ", ".join(f"{key}={value!r}" for key, value in raw_args.items())
        return repr(raw_args)

    @staticmethod
    def _summarize_content(content: Any, limit: int = 120) -> str:
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            text = " ".join(str(item) for item in content).strip()
        else:
            text = str(content).strip()

        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."
