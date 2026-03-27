"""Minimal JSONL-backed session storage for Phase 3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

DEFAULT_SESSION_NAME = "default"
WORKSPACE_DIR_NAME = "workspace"
SESSIONS_DIR_NAME = "sessions"


class SessionStore:
    """Persist the default session history under the local workspace directory."""

    def __init__(self, workspace_root: Path | None = None):
        repo_root = Path(__file__).resolve().parents[2]
        self.workspace_root = workspace_root or (repo_root / WORKSPACE_DIR_NAME)
        self.sessions_dir = self.workspace_root / SESSIONS_DIR_NAME
        self.session_path = self.sessions_dir / f"{DEFAULT_SESSION_NAME}.jsonl"

    def load_default_session(self) -> list[BaseMessage]:
        """Load persisted session messages, treating missing files as a new session."""
        if not self.session_path.exists():
            return []

        content = self.session_path.read_text(encoding="utf-8").strip()
        if not content:
            return []

        messages: list[BaseMessage] = []
        with self.session_path.open(encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Session file contains invalid JSON on line {line_number}: {exc}"
                    ) from exc
                messages.append(_record_to_message(payload))
        return messages

    def save_default_session(self, messages: list[BaseMessage]) -> None:
        """Save the latest conversation history for the default session."""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        serializable = [
            _message_to_record(message)
            for message in messages
            if not _should_skip_message(message)
        ]
        with self.session_path.open("w", encoding="utf-8") as handle:
            for record in serializable:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _should_skip_message(message: BaseMessage) -> bool:
    """Avoid persisting system prompt messages; they are re-injected every run."""
    return message.type == "system"


def _record_to_message(payload: dict[str, Any]) -> BaseMessage:
    role = payload.get("role")
    content = payload.get("content", "")
    name = payload.get("name")

    if role == "user":
        return HumanMessage(content=content, name=name)
    if role == "assistant":
        return AIMessage(
            content=content,
            name=name,
            tool_calls=list(payload.get("tool_calls") or []),
        )
    if role == "tool":
        tool_call_id = str(payload.get("tool_call_id") or "")
        return ToolMessage(content=content, tool_call_id=tool_call_id, name=name)
    raise ValueError(f"Unsupported session role: {role!r}")


def _message_to_record(message: BaseMessage) -> dict[str, Any]:
    """Serialize the small subset of message fields that Phase 3 actually uses."""
    if isinstance(message, HumanMessage):
        record: dict[str, Any] = {"role": "user", "content": message.content}
    elif isinstance(message, AIMessage):
        record = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            record["tool_calls"] = message.tool_calls
    elif isinstance(message, ToolMessage):
        record = {
            "role": "tool",
            "content": message.content,
            "tool_call_id": message.tool_call_id,
        }
    else:
        raise ValueError(f"Unsupported message type for session storage: {type(message).__name__}")

    if getattr(message, "name", None):
        record["name"] = message.name
    return record
