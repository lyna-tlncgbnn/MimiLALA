"""Console rendering for execution events."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DebugPrinter:
    """Print concise execution summaries when console debug is enabled."""

    enabled: bool = False

    def log(self, message: str) -> None:
        if self.enabled:
            rendered = f"[debug] {message}"
            encoding = sys.stdout.encoding or "utf-8"
            safe_rendered = rendered.encode(encoding, errors="replace").decode(
                encoding, errors="replace"
            )
            print(safe_rendered)

    def log_event(self, event: dict[str, Any]) -> None:
        if not self.enabled:
            return

        event_name = event.get("event")
        if event_name == "conversation_loaded":
            self.log(f"loaded conversation: {event.get('message_count', 0)} messages")
        elif event_name == "tools_registered":
            self.log(f"registered tools: {', '.join(event.get('tools', []))}")
        elif event_name == "graph_started":
            self.log("graph execution started")
        elif event_name == "tool_call_emitted":
            self.log(
                "model emitted tool call: "
                f"{event.get('tool')}({self._format_tool_args(event.get('args'))})"
            )
        elif event_name == "tool_completed":
            self.log(f"tool {event.get('tool')} returned: {self._summarize_content(event.get('output'))}")
        elif event_name == "final_answer":
            self.log(f"final answer: {self._summarize_content(event.get('content'))}")
        elif event_name == "run_failed":
            self.log(f"{event.get('stage')} failed: {event.get('error')}")

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
