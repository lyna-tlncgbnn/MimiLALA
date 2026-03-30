"""Execution event storage for one conversation."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentbot.memory.conversation import META_TYPE, WORKSPACE_DIR_NAME, ConversationMeta

EXECUTIONS_DIR_NAME = "executions"
EVENT_TYPE = "event"


class ExecutionStore:
    """Append execution events under one conversation id."""

    def __init__(self, workspace_root: Path | None = None):
        repo_root = Path(__file__).resolve().parents[2]
        self.workspace_root = workspace_root or (repo_root / WORKSPACE_DIR_NAME)
        self.executions_dir = self.workspace_root / EXECUTIONS_DIR_NAME
        self.legacy_default_execution_path = self.executions_dir / "default.jsonl"

    def append_events(self, meta: ConversationMeta, events: list[dict[str, Any]]) -> None:
        """Append execution events, initializing the file with execution meta if needed."""
        self.executions_dir.mkdir(parents=True, exist_ok=True)
        execution_path = self._execution_path(meta.conversation_id)

        if not execution_path.exists():
            self._migrate_legacy_execution_if_needed(meta)

        if not execution_path.exists():
            with execution_path.open("w", encoding="utf-8") as handle:
                handle.write(json.dumps(self._meta_record(meta), ensure_ascii=False) + "\n")
        else:
            existing_meta = self._read_meta(execution_path)
            if existing_meta.get("conversation_id") != meta.conversation_id:
                raise ValueError("Execution file meta does not match the current conversation.")

        with execution_path.open("a", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def delete_execution_file(self, conversation_id: str) -> None:
        """Delete one execution file if it exists."""
        path = self._execution_path(conversation_id)
        if path.exists():
            path.unlink()

    def _execution_path(self, conversation_id: str) -> Path:
        return self.executions_dir / f"{conversation_id}.jsonl"

    def _migrate_legacy_execution_if_needed(self, meta: ConversationMeta) -> None:
        if not self.legacy_default_execution_path.exists():
            return

        existing_meta = self._read_meta(self.legacy_default_execution_path)
        if existing_meta.get("conversation_id") != meta.conversation_id:
            return

        target_path = self._execution_path(meta.conversation_id)
        if target_path.exists():
            self.legacy_default_execution_path.unlink()
            return

        with self.legacy_default_execution_path.open(encoding="utf-8") as handle:
            lines = [line.rstrip("\n") for line in handle if line.strip()]

        if not lines:
            raise ValueError("Execution file is empty.")

        lines[0] = json.dumps(self._meta_record(meta), ensure_ascii=False)
        with target_path.open("w", encoding="utf-8") as handle:
            for line in lines:
                handle.write(line + "\n")

        self.legacy_default_execution_path.unlink()

    def _meta_record(self, meta: ConversationMeta) -> dict[str, str]:
        return {
            "type": META_TYPE,
            "conversation_id": meta.conversation_id,
            "created_at": meta.created_at,
        }

    def _read_meta(self, path: Path) -> dict[str, Any]:
        with path.open(encoding="utf-8") as handle:
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
