"""Conversation storage with file-level meta records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

DEFAULT_CONVERSATION_NAME = "default"
DEFAULT_CONVERSATION_POINTER_FILE = "default.json"
WORKSPACE_DIR_NAME = "workspace"
CONVERSATIONS_DIR_NAME = "conversations"
LEGACY_SESSIONS_DIR_NAME = "sessions"
META_TYPE = "meta"
MESSAGE_TYPE = "message"
AGENTBOT_META_KEY = "_agentbot"
ASSISTANT_RESPONSE_KEY = "response"
ASSISTANT_DELEGATION_KEY = "delegation"
ASSISTANT_BROWSER_TASK_KEY = "browser_task"
ASSISTANT_STATE_KEY = "state"
ASSISTANT_METADATA_KEY = "metadata"


@dataclass(slots=True)
class ConversationMeta:
    """File-level metadata for one conversation."""

    conversation_id: str
    name: str
    created_at: str
    updated_at: str

    def to_record(self) -> dict[str, str]:
        return {
            "type": META_TYPE,
            "conversation_id": self.conversation_id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ConversationStore:
    """Persist conversations as one meta + message JSONL file per conversation."""

    def __init__(self, workspace_root: Path | None = None):
        repo_root = Path(__file__).resolve().parents[2]
        self.workspace_root = workspace_root or (repo_root / WORKSPACE_DIR_NAME)
        self.conversations_dir = self.workspace_root / CONVERSATIONS_DIR_NAME
        self.legacy_sessions_dir = self.workspace_root / LEGACY_SESSIONS_DIR_NAME
        self.default_pointer_path = self.conversations_dir / DEFAULT_CONVERSATION_POINTER_FILE
        self.legacy_default_conversation_path = self.conversations_dir / "default.jsonl"
        self.legacy_default_session_path = self.legacy_sessions_dir / "default.jsonl"

    def ensure_default_conversation(self) -> ConversationMeta:
        """Return the default conversation, migrating legacy data if needed."""
        self._migrate_legacy_default_conversation_if_needed()

        default_conversation_id = self._read_default_conversation_id()
        if default_conversation_id:
            try:
                return self.get_conversation_meta(default_conversation_id)
            except FileNotFoundError:
                pass

        existing_default = self._find_existing_default_conversation()
        if existing_default is not None:
            self._write_default_conversation_id(existing_default.conversation_id)
            return existing_default

        meta = self._create_conversation(DEFAULT_CONVERSATION_NAME)
        self._write_conversation_file(meta, [])
        self._write_default_conversation_id(meta.conversation_id)
        return meta

    def load_default_conversation(self) -> tuple[ConversationMeta, list[BaseMessage]]:
        """Load the current default conversation."""
        meta = self.ensure_default_conversation()
        return self.get_conversation(meta.conversation_id)

    def create_conversation(self, name: str | None = None) -> ConversationMeta:
        """Create an empty conversation and persist its meta file."""
        meta = self._create_conversation(name or self._default_generated_name())
        self._write_conversation_file(meta, [])
        return meta

    def list_conversations(self) -> list[ConversationMeta]:
        """List every stored conversation sorted by most recent update first."""
        conversations: list[ConversationMeta] = []
        if not self.conversations_dir.exists():
            return conversations

        for path in self.conversations_dir.glob("*.jsonl"):
            conversations.append(self._load_meta_from_path(path))

        return sorted(
            conversations,
            key=lambda meta: (meta.updated_at, meta.created_at, meta.conversation_id),
            reverse=True,
        )

    def get_conversation(self, conversation_id: str) -> tuple[ConversationMeta, list[BaseMessage]]:
        """Load one conversation file by conversation id."""
        path = self._conversation_path(conversation_id)
        if not path.exists():
            raise FileNotFoundError(f"Conversation not found: {conversation_id}")
        return self._load_conversation_from_path(path)

    def get_conversation_meta(self, conversation_id: str) -> ConversationMeta:
        """Load only the meta for one conversation."""
        path = self._conversation_path(conversation_id)
        if not path.exists():
            raise FileNotFoundError(f"Conversation not found: {conversation_id}")
        return self._load_meta_from_path(path)

    def rename_conversation(self, conversation_id: str, new_name: str) -> ConversationMeta:
        """Rename a conversation and bump updated_at."""
        meta, messages = self.get_conversation(conversation_id)
        updated_meta = ConversationMeta(
            conversation_id=meta.conversation_id,
            name=new_name,
            created_at=meta.created_at,
            updated_at=_now_iso(),
        )
        self._write_conversation_file(updated_meta, messages)
        return updated_meta

    def delete_conversation(self, conversation_id: str) -> None:
        """Delete one conversation file."""
        path = self._conversation_path(conversation_id)
        if not path.exists():
            raise FileNotFoundError(f"Conversation not found: {conversation_id}")
        path.unlink()

        default_conversation_id = self._read_default_conversation_id()
        if default_conversation_id == conversation_id and self.default_pointer_path.exists():
            self.default_pointer_path.unlink()

    def append_message_to_conversation(
        self, conversation_id: str, message: BaseMessage
    ) -> ConversationMeta:
        """Append one message to a conversation."""
        meta, messages = self.get_conversation(conversation_id)
        messages.append(message)
        return self.replace_conversation_messages(conversation_id, messages, existing_meta=meta)

    def replace_conversation_messages(
        self,
        conversation_id: str,
        messages: list[BaseMessage],
        existing_meta: ConversationMeta | None = None,
    ) -> ConversationMeta:
        """Rewrite one conversation with the provided messages."""
        meta = existing_meta or self.get_conversation_meta(conversation_id)
        updated_meta = ConversationMeta(
            conversation_id=meta.conversation_id,
            name=meta.name,
            created_at=meta.created_at,
            updated_at=_updated_at_for_messages(messages, fallback=meta.updated_at or meta.created_at),
        )
        self._write_conversation_file(updated_meta, messages)
        return updated_meta

    def _create_conversation(self, name: str) -> ConversationMeta:
        timestamp = _now_iso()
        return ConversationMeta(
            conversation_id=_new_prefixed_id("conv"),
            name=name,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def _find_existing_default_conversation(self) -> ConversationMeta | None:
        for meta in self.list_conversations():
            if meta.name == DEFAULT_CONVERSATION_NAME:
                return meta
        return None

    def _migrate_legacy_default_conversation_if_needed(self) -> None:
        if self._read_default_conversation_id():
            return

        if self.legacy_default_conversation_path.exists():
            meta, messages = self._load_conversation_from_path(self.legacy_default_conversation_path)
            migrated_meta = ConversationMeta(
                conversation_id=meta.conversation_id,
                name=meta.name or DEFAULT_CONVERSATION_NAME,
                created_at=meta.created_at,
                updated_at=meta.updated_at or _updated_at_for_messages(messages, fallback=meta.created_at),
            )
            self._write_conversation_file(migrated_meta, messages)
            if self.legacy_default_conversation_path != self._conversation_path(meta.conversation_id):
                self.legacy_default_conversation_path.unlink()
            self._write_default_conversation_id(migrated_meta.conversation_id)
            return

        if self.legacy_default_session_path.exists():
            messages = self._load_legacy_messages(self.legacy_default_session_path)
            meta = self._create_conversation(DEFAULT_CONVERSATION_NAME)
            migrated_meta = ConversationMeta(
                conversation_id=meta.conversation_id,
                name=meta.name,
                created_at=meta.created_at,
                updated_at=_updated_at_for_messages(messages, fallback=meta.created_at),
            )
            self._write_conversation_file(migrated_meta, messages)
            self._write_default_conversation_id(migrated_meta.conversation_id)

    def _conversation_path(self, conversation_id: str) -> Path:
        return self.conversations_dir / f"{conversation_id}.jsonl"

    def _write_conversation_file(self, meta: ConversationMeta, messages: list[BaseMessage]) -> None:
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        path = self._conversation_path(meta.conversation_id)
        records = [meta.to_record()]
        for message in messages:
            if message.type == "system":
                continue
            records.append(_message_to_record(message))

        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _load_conversation_from_path(self, path: Path) -> tuple[ConversationMeta, list[BaseMessage]]:
        with path.open(encoding="utf-8") as handle:
            lines = [line.strip() for line in handle if line.strip()]

        if not lines:
            raise ValueError(f"Conversation file is empty: {path}")

        records = [_loads_json(line, path) for line in lines]
        meta = _meta_from_record(records[0])
        messages = [_record_to_message(record) for record in records[1:]]
        return meta, messages

    def _load_meta_from_path(self, path: Path) -> ConversationMeta:
        with path.open(encoding="utf-8") as handle:
            first_line = handle.readline().strip()
        if not first_line:
            raise ValueError(f"Conversation file is empty: {path}")
        return _meta_from_record(_loads_json(first_line, path))

    def _read_default_conversation_id(self) -> str | None:
        if not self.default_pointer_path.exists():
            return None
        payload = _loads_json(self.default_pointer_path.read_text(encoding="utf-8"), self.default_pointer_path)
        conversation_id = str(payload.get("conversation_id") or "").strip()
        return conversation_id or None

    def _write_default_conversation_id(self, conversation_id: str) -> None:
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        payload = {"conversation_id": conversation_id}
        self.default_pointer_path.write_text(
            json.dumps(payload, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _default_generated_name(self) -> str:
        return f"Conversation {_display_now()}"

    def _load_legacy_messages(self, path: Path) -> list[BaseMessage]:
        messages: list[BaseMessage] = []
        with path.open(encoding="utf-8") as handle:
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


def _meta_from_record(meta_record: dict[str, Any]) -> ConversationMeta:
    if meta_record.get("type") != META_TYPE:
        raise ValueError("Conversation file must start with a meta record.")

    meta = ConversationMeta(
        conversation_id=str(meta_record.get("conversation_id") or ""),
        name=str(meta_record.get("name") or DEFAULT_CONVERSATION_NAME),
        created_at=str(meta_record.get("created_at") or ""),
        updated_at=str(meta_record.get("updated_at") or meta_record.get("created_at") or ""),
    )
    if not meta.conversation_id or not meta.created_at:
        raise ValueError("Conversation meta record is missing required fields.")
    return meta


def _legacy_record_to_message(payload: dict[str, Any]) -> BaseMessage:
    role = payload.get("role")
    content = payload.get("content", "")
    name = payload.get("name")
    metadata = _new_message_metadata()

    if role == "user":
        return HumanMessage(content=content, name=name, additional_kwargs={AGENTBOT_META_KEY: metadata})
    if role == "assistant":
        additional_kwargs = {AGENTBOT_META_KEY: metadata}
        if payload.get("response") is not None:
            additional_kwargs[ASSISTANT_RESPONSE_KEY] = payload.get("response")
        if payload.get("delegation") is not None:
            additional_kwargs[ASSISTANT_DELEGATION_KEY] = payload.get("delegation")
        if payload.get("browser_task") is not None:
            additional_kwargs[ASSISTANT_BROWSER_TASK_KEY] = payload.get("browser_task")
        if payload.get("state") is not None:
            additional_kwargs[ASSISTANT_STATE_KEY] = payload.get("state")
        if payload.get("metadata") is not None:
            additional_kwargs[ASSISTANT_METADATA_KEY] = payload.get("metadata")
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
        if payload.get("response") is not None:
            additional_kwargs[ASSISTANT_RESPONSE_KEY] = payload.get("response")
        if payload.get("delegation") is not None:
            additional_kwargs[ASSISTANT_DELEGATION_KEY] = payload.get("delegation")
        if payload.get("browser_task") is not None:
            additional_kwargs[ASSISTANT_BROWSER_TASK_KEY] = payload.get("browser_task")
        if payload.get("state") is not None:
            additional_kwargs[ASSISTANT_STATE_KEY] = payload.get("state")
        if payload.get("metadata") is not None:
            additional_kwargs[ASSISTANT_METADATA_KEY] = payload.get("metadata")
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
        response_payload = _assistant_response_payload(message)
        record = {
            "type": MESSAGE_TYPE,
            "message_id": metadata["message_id"],
            "timestamp": metadata["timestamp"],
            "role": "assistant",
            "content": message.content,
        }
        if response_payload is not None:
            record["response"] = response_payload
        if message.tool_calls:
            record["tool_calls"] = message.tool_calls
        if ASSISTANT_DELEGATION_KEY in message.additional_kwargs:
            record["delegation"] = message.additional_kwargs[ASSISTANT_DELEGATION_KEY]
        if ASSISTANT_BROWSER_TASK_KEY in message.additional_kwargs:
            record["browser_task"] = message.additional_kwargs[ASSISTANT_BROWSER_TASK_KEY]
        if ASSISTANT_STATE_KEY in message.additional_kwargs:
            record["state"] = message.additional_kwargs[ASSISTANT_STATE_KEY]
        if ASSISTANT_METADATA_KEY in message.additional_kwargs:
            record["metadata"] = message.additional_kwargs[ASSISTANT_METADATA_KEY]
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


def _assistant_response_payload(message: AIMessage) -> dict[str, Any] | None:
    response = message.additional_kwargs.get(ASSISTANT_RESPONSE_KEY)
    if isinstance(response, dict):
        return response

    if isinstance(message.content, str) and message.content:
        return {"text": message.content}
    if isinstance(message.content, list):
        text = "".join(
            item if isinstance(item, str) else str(item.get("text", ""))
            for item in message.content
            if isinstance(item, str) or (isinstance(item, dict) and item.get("type") == "text")
        ).strip()
        if text:
            return {"text": text}
    return None


def _new_message_metadata() -> dict[str, str]:
    return {"message_id": _new_prefixed_id("msg"), "timestamp": _now_iso()}


def _updated_at_for_messages(messages: list[BaseMessage], fallback: str) -> str:
    for message in reversed(messages):
        if message.type == "system":
            continue
        metadata = _get_or_assign_message_metadata(message)
        if metadata.get("timestamp"):
            return metadata["timestamp"]
    return fallback


def _new_prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _display_now() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
