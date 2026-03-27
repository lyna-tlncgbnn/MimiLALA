"""Execution event storage for one conversation alias."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentbot.memory.conversation import (
    DEFAULT_CONVERSATION_ALIAS,
    META_TYPE,
    WORKSPACE_DIR_NAME,
    ConversationMeta,
)

EXECUTIONS_DIR_NAME = "executions"
EVENT_TYPE = "event"


class ExecutionStore:
    """Append execution events under one conversation alias."""

    def __init__(self, workspace_root: Path | None = None, alias: str = DEFAULT_CONVERSATION_ALIAS):
        repo_root = Path(__file__).resolve().parents[2]
        self.workspace_root = workspace_root or (repo_root / WORKSPACE_DIR_NAME)
        self.alias = alias
        self.executions_dir = self.workspace_root / EXECUTIONS_DIR_NAME
        self.execution_path = self.executions_dir / f"{alias}.jsonl"

    def append_default_events(self, meta: ConversationMeta, events: list[dict[str, Any]]) -> None:
        """Append execution events, initializing the file with conversation meta if needed."""
        self.executions_dir.mkdir(parents=True, exist_ok=True)

        if not self.execution_path.exists():
            with self.execution_path.open("w", encoding="utf-8") as handle:
                handle.write(json.dumps(meta.to_record(), ensure_ascii=False) + "\n")
        else:
            existing_meta = self._read_meta()
            if existing_meta.get("conversation_id") != meta.conversation_id:
                raise ValueError("Execution file meta does not match the current conversation.")

        with self.execution_path.open("a", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _read_meta(self) -> dict[str, Any]:
        with self.execution_path.open(encoding="utf-8") as handle:
            first_line = handle.readline().strip()
        if not first_line:
            raise ValueError("Execution file is empty.")
        try:
            payload = json.loads(first_line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Execution file contains invalid JSON: {exc}") from exc
        if payload.get("type") != META_TYPE:
            raise ValueError("Execution file must start with a meta record.")
        return payload


def new_execution_id() -> str:
    """Create a stable identifier for one call to run_once()."""
    return f"exec_{uuid4().hex}"


def build_event(execution_id: str, event: str, **fields: Any) -> dict[str, Any]:
    """Create one execution event record."""
    payload: dict[str, Any] = {
        "type": EVENT_TYPE,
        "event_id": f"evt_{uuid4().hex}",
        "execution_id": execution_id,
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "event": event,
    }
    payload.update(fields)
    return payload
