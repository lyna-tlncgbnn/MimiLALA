"""Dataclasses for the redesigned storage layer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConversationRow:
    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    archived_at: str | None = None


@dataclass(slots=True)
class MessageRow:
    message_id: str
    conversation_id: str
    run_id: str | None
    role: str
    phase: str
    visibility: str
    content_json: str
    text_preview: str
    created_at: str


@dataclass(slots=True)
class RunRow:
    run_id: str
    conversation_id: str
    thread_id: str
    status: str
    started_at: str
    user_message_id: str | None = None
    final_message_id: str | None = None
    workflow_name: str | None = None
    ended_at: str | None = None
    error_message: str | None = None
    step_count: int = 0
    visible_step_count: int = 0
    has_execution: bool = False


@dataclass(slots=True)
class RunStepRow:
    step_id: str
    run_id: str
    step_type: str
    title: str
    status: str
    display_mode: str
    sort_order: int
    started_at: str
    parent_step_id: str | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    input_json: str | None = None
    output_json: str | None = None
    summary_text: str | None = None
    ended_at: str | None = None


@dataclass(slots=True)
class ArtifactRow:
    artifact_id: str
    run_id: str
    artifact_type: str
    name: str
    uri: str
    created_at: str
    step_id: str | None = None
    metadata_json: str | None = None
