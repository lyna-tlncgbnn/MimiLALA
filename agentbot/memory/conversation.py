"""Conversation storage with file-level meta records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

DEFAULT_CONVERSATION_ALIAS = "default"
DEFAULT_CONVERSATION_NAME = "default"
WORKSPACE_DIR_NAME = "workspace"
CONVERSATIONS_DIR_NAME = "conversations"
LEGACY_SESSIONS_DIR_NAME = "sessions"
META_TYPE = "meta"
MESSAGE_TYPE = "message"
AGENTBOT_META_KEY = "_agentbot"


@dataclass(slots=True)
class ConversationMeta:
    """File-level metadata for one conversation."""

    conversation_id: str
    name: str
    created_at: str

    def to_record(self) -> dict[str, str]:
        return {
            "type": META_TYPE,
            "conversation_id": self.conversation_id,
            "name": self.name,
            "created_at": self.created_at,
        }


class ConversationStore:
    """Persist one named conversation as meta + message records."""

    def __init__(self, workspace_root: Path | None = None, alias: str = DEFAULT_CONVERSATION_ALIAS):
        repo_root = Path(__file__).resolve().parents[2]
        self.workspace_root = workspace_root or (repo_root / WORKSPACE_DIR_NAME)
        self.alias = alias
        self.conversations_dir = self.workspace_root / CONVERSATIONS_DIR_NAME
        self.legacy_sessions_dir = self.workspace_root / LEGACY_SESSIONS_DIR_NAME
        self.conversation_path = self.conversations_dir / f"{alias}.jsonl"
        self.legacy_session_path = self.legacy_sessions_dir / f"{alias}.jsonl"

    def load_default_conversation(self) -> tuple[ConversationMeta | None, list[BaseMessage]]:
        """Load the current conversation or fall back to the legacy session file."""
        if self.conversation_path.exists():
            return self._load_new_format()
        if self.legacy_session_path.exists():
            return None, self._load_legacy_messages()
        return None, []

    def create_default_meta(self) -> ConversationMeta:
        """Create a new meta record for the default conversation alias."""
        return ConversationMeta(
            conversation_id=_new_prefixed_id("conv"),
            name=DEFAULT_CONVERSATION_NAME,
            created_at=_now_iso(),
        )

    def save_default_conversation(
        self, meta: ConversationMeta, messages: list[BaseMessage]
    ) -> None:
        """Rewrite the conversation file using the new meta + message format."""
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        records = [meta.to_record()]
        for message in messages:
            if message.type == "system":
                continue
            records.append(_message_to_record(message))

        with self.conversation_path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _load_new_format(self) -> tuple[ConversationMeta, list[BaseMessage]]:
        with self.conversation_path.open(encoding="utf-8") as handle:
            lines = [line.strip() for line in handle if line.strip()]

        if not lines:
            raise ValueError("Conversation file is empty.")

        records = [_loads_json(line, self.conversation_path) for line in lines]
        meta_record = records[0]
        if meta_record.get("type") != META_TYPE:
            raise ValueError("Conversation file must start with a meta record.")

        meta = ConversationMeta(
            conversation_id=str(meta_record.get("conversation_id") or ""),
            name=str(meta_record.get("name") or DEFAULT_CONVERSATION_NAME),
            created_at=str(meta_record.get("created_at") or ""),
        )
        if not meta.conversation_id or not meta.created_at:
            raise ValueError("Conversation meta record is missing required fields.")

        messages = [_record_to_message(record) for record in records[1:]]
        return meta, messages

    def _load_legacy_messages(self) -> list[BaseMessage]:
        messages: list[BaseMessage] = []
        with self.legacy_session_path.open(encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Legacy session file contains invalid JSON on line {line_number}: {exc}"
                    ) from exc
                messages.append(_legacy_record_to_message(payload))
        return messages


def _loads_json(raw_line: str, path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(raw_line)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} contains invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain one JSON object per line.")
    return payload


def _legacy_record_to_message(payload: dict[str, Any]) -> BaseMessage:
    role = payload.get("role")
    content = payload.get("content", "")
    name = payload.get("name")
    metadata = _new_message_metadata()

    if role == "user":
        return HumanMessage(content=content, name=name, additional_kwargs={AGENTBOT_META_KEY: metadata})
    if role == "assistant":
        return AIMessage(
            content=content,
            name=name,
            tool_calls=list(payload.get("tool_calls") or []),
            additional_kwargs={AGENTBOT_META_KEY: metadata},
        )
    if role == "tool":
        tool_call_id = str(payload.get("tool_call_id") or "")
        return ToolMessage(
            content=content,
            tool_call_id=tool_call_id,
            name=name,
            additional_kwargs={AGENTBOT_META_KEY: metadata},
        )
    raise ValueError(f"Unsupported legacy session role: {role!r}")


def _record_to_message(payload: dict[str, Any]) -> BaseMessage:
    if payload.get("type") != MESSAGE_TYPE:
        raise ValueError(f"Unsupported conversation record type: {payload.get('type')!r}")

    role = payload.get("role")
    content = payload.get("content", "")
    name = payload.get("name")
    metadata = {
        "message_id": str(payload.get("message_id") or _new_prefixed_id("msg")),
        "timestamp": str(payload.get("timestamp") or _now_iso()),
    }
    additional_kwargs = {AGENTBOT_META_KEY: metadata}

    if role == "user":
        return HumanMessage(content=content, name=name, additional_kwargs=additional_kwargs)
    if role == "assistant":
        return AIMessage(
            content=content,
            name=name,
            tool_calls=list(payload.get("tool_calls") or []),
            additional_kwargs=additional_kwargs,
        )
    if role == "tool":
        tool_call_id = str(payload.get("tool_call_id") or "")
        return ToolMessage(
            content=content,
            tool_call_id=tool_call_id,
            name=name,
            additional_kwargs=additional_kwargs,
        )
    raise ValueError(f"Unsupported conversation message role: {role!r}")


def _message_to_record(message: BaseMessage) -> dict[str, Any]:
    metadata = _get_or_assign_message_metadata(message)

    if isinstance(message, HumanMessage):
        record: dict[str, Any] = {
            "type": MESSAGE_TYPE,
            "message_id": metadata["message_id"],
            "timestamp": metadata["timestamp"],
            "role": "user",
            "content": message.content,
        }
    elif isinstance(message, AIMessage):
        record = {
            "type": MESSAGE_TYPE,
            "message_id": metadata["message_id"],
            "timestamp": metadata["timestamp"],
            "role": "assistant",
            "content": message.content,
        }
        if message.tool_calls:
            record["tool_calls"] = message.tool_calls
    elif isinstance(message, ToolMessage):
        record = {
            "type": MESSAGE_TYPE,
            "message_id": metadata["message_id"],
            "timestamp": metadata["timestamp"],
            "role": "tool",
            "content": message.content,
            "tool_call_id": message.tool_call_id,
        }
    else:
        raise ValueError(f"Unsupported message type for conversation storage: {type(message).__name__}")

    if getattr(message, "name", None):
        record["name"] = message.name
    return record


def _get_or_assign_message_metadata(message: BaseMessage) -> dict[str, str]:
    metadata = dict(getattr(message, "additional_kwargs", {}).get(AGENTBOT_META_KEY) or {})
    if not metadata.get("message_id"):
        metadata["message_id"] = _new_prefixed_id("msg")
    if not metadata.get("timestamp"):
        metadata["timestamp"] = _now_iso()
    message.additional_kwargs[AGENTBOT_META_KEY] = metadata
    return metadata


def _new_message_metadata() -> dict[str, str]:
    return {"message_id": _new_prefixed_id("msg"), "timestamp": _now_iso()}


def _new_prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
