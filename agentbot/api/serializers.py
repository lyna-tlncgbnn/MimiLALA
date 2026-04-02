"""Serialization helpers for API responses."""

from __future__ import annotations

from agentbot.services.conversations import message_to_api_dict
from agentbot.services.sqlite_conversations import TranscriptMessage
from agentbot.storage.models import ConversationRow, RunRow, RunStepRow


def serialize_sqlite_conversation(conversation: ConversationRow) -> dict:
    return {
        "conversation_id": conversation.conversation_id,
        "name": conversation.title,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


def serialize_messages(messages: list) -> list[dict]:
    return [message_to_api_dict(message) for message in messages]


def serialize_transcript_messages(messages: list[TranscriptMessage]) -> list[dict]:
    return [
        {
            "message_id": message.message_id,
            "run_id": message.run_id,
            "timestamp": message.created_at,
            "role": message.role,
            "content": message.content,
            "name": None,
            "tool_call_id": None,
            "tool_calls": None,
        }
        for message in messages
    ]


def serialize_run(run: RunRow) -> dict:
    return {
        "run_id": run.run_id,
        "conversation_id": run.conversation_id,
        "thread_id": run.thread_id,
        "status": run.status,
        "started_at": run.started_at,
        "ended_at": run.ended_at,
        "workflow_name": run.workflow_name,
        "user_message_id": run.user_message_id,
        "final_message_id": run.final_message_id,
        "error_message": run.error_message,
        "step_count": run.step_count,
        "visible_step_count": run.visible_step_count,
        "has_execution": run.has_execution,
    }


def serialize_run_step(step: RunStepRow) -> dict:
    return {
        "step_id": step.step_id,
        "run_id": step.run_id,
        "parent_step_id": step.parent_step_id,
        "step_type": step.step_type,
        "title": step.title,
        "status": step.status,
        "display_mode": step.display_mode,
        "sort_order": step.sort_order,
        "started_at": step.started_at,
        "ended_at": step.ended_at,
        "tool_name": step.tool_name,
        "tool_call_id": step.tool_call_id,
        "input_json": step.input_json,
        "output_json": step.output_json,
        "summary_text": step.summary_text,
    }
