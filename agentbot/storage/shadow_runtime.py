"""SQLite runtime persistence helpers for runs, transcript rows, and run steps."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from agentbot.storage.common import AGENTBOT_META_KEY, new_prefixed_id
from agentbot.storage.db import AgentDatabase
from agentbot.storage.repositories import (
    ArtifactRepository,
    ConversationRepository,
    MessageRepository,
    RunRepository,
    RunStepRepository,
)


@dataclass(slots=True)
class ActiveRunShadow:
    run_id: str
    conversation_id: str
    user_message_id: str
    tool_steps: dict[str, str]
    named_steps: dict[str, str]
    next_sort_order: int


class RuntimeShadowWriter:
    """Persist run-oriented application data into SQLite."""

    def __init__(self, database: AgentDatabase | None = None):
        self.database = database or AgentDatabase()

    def sync_conversation(self, meta: Any) -> None:
        self.database.initialize()
        with self.database.connect() as connection:
            repo = ConversationRepository(connection)
            repo.upsert(
                conversation_id=_conversation_id(meta),
                title=_conversation_title(meta),
                created_at=_conversation_created_at(meta),
                updated_at=_conversation_updated_at(meta),
            )

    def sync_conversations(self, metas: list[Any]) -> None:
        self.database.initialize()
        with self.database.connect() as connection:
            repo = ConversationRepository(connection)
            for meta in metas:
                repo.upsert(
                    conversation_id=_conversation_id(meta),
                    title=_conversation_title(meta),
                    created_at=_conversation_created_at(meta),
                    updated_at=_conversation_updated_at(meta),
                )

    def delete_conversation(self, conversation_id: str) -> None:
        self.database.initialize()
        with self.database.connect() as connection:
            run_repo = RunRepository(connection)
            step_repo = RunStepRepository(connection)
            artifact_repo = ArtifactRepository(connection)
            message_repo = MessageRepository(connection)
            conversation_repo = ConversationRepository(connection)

            runs = run_repo.list_for_conversation(conversation_id)
            run_ids = [run.run_id for run in runs]
            artifact_repo.delete_for_run_ids(run_ids)
            step_repo.delete_for_run_ids(run_ids)
            message_repo.delete_for_conversation(conversation_id)
            run_repo.delete_for_conversation(conversation_id)
            conversation_repo.delete(conversation_id)

    def start_run(
        self,
        *,
        meta: Any,
        user_message_id: str,
        user_text: str,
        user_timestamp: str,
        workflow_name: str = "chat_turn",
    ) -> ActiveRunShadow | None:
        self.database.initialize()
        with self.database.connect() as connection:
            conversation_repo = ConversationRepository(connection)
            run_repo = RunRepository(connection)
            message_repo = MessageRepository(connection)

            conversation_repo.upsert(
                conversation_id=_conversation_id(meta),
                title=_conversation_title(meta),
                created_at=_conversation_created_at(meta),
                updated_at=max(_conversation_updated_at(meta), user_timestamp),
            )
            run_id = new_prefixed_id("run")
            run = run_repo.create(
                conversation_id=_conversation_id(meta),
                thread_id=run_id,
                status="running",
                workflow_name=workflow_name,
                user_message_id=user_message_id,
                run_id=run_id,
                started_at=user_timestamp,
            )
            message_repo.create(
                message_id=user_message_id,
                conversation_id=_conversation_id(meta),
                run_id=run.run_id,
                role="user",
                phase="final_answer",
                visibility="visible",
                content=_text_content_blocks(user_text),
                text_preview=user_text,
                created_at=user_timestamp,
            )
            return ActiveRunShadow(
                run_id=run.run_id,
                conversation_id=meta.conversation_id,
                user_message_id=user_message_id,
                tool_steps={},
                named_steps={},
                next_sort_order=1,
            )

    def record_step_started(
        self,
        active_run: ActiveRunShadow,
        *,
        step_key: str,
        step_type: str,
        title: str,
        timestamp: str,
        display_mode: str = "timeline",
        parent_step_key: str | None = None,
        summary_text: str | None = None,
        input_payload: Any = None,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
    ) -> ActiveRunShadow:
        parent_step_id = None
        if parent_step_key:
            parent_step_id = (
                active_run.named_steps.get(parent_step_key)
                or active_run.tool_steps.get(parent_step_key)
            )

        self.database.initialize()
        with self.database.connect() as connection:
            step_repo = RunStepRepository(connection)
            step = step_repo.create(
                run_id=active_run.run_id,
                step_type=step_type,
                title=title,
                status="running",
                display_mode=display_mode,
                sort_order=active_run.next_sort_order,
                parent_step_id=parent_step_id,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                input_payload=input_payload,
                summary_text=summary_text,
                started_at=timestamp,
            )

        active_run.named_steps[step_key] = step.step_id
        active_run.next_sort_order += 1
        return active_run

    def record_step_finished(
        self,
        active_run: ActiveRunShadow,
        *,
        step_key: str,
        timestamp: str,
        status: str = "completed",
        output_payload: Any = None,
        summary_text: str | None = None,
    ) -> ActiveRunShadow:
        step_id = active_run.named_steps.get(step_key) or active_run.tool_steps.get(step_key)
        if step_id is None:
            return active_run

        self.database.initialize()
        with self.database.connect() as connection:
            step_repo = RunStepRepository(connection)
            step_repo.update_status(
                step_id,
                status=status,
                output_payload=output_payload,
                summary_text=summary_text,
                ended_at=timestamp,
            )
        return active_run

    def record_artifact(
        self,
        active_run: ActiveRunShadow,
        *,
        artifact_type: str,
        name: str,
        uri: str,
        step_key: str | None = None,
        metadata: Any = None,
    ) -> str:
        step_id = None
        if step_key:
            step_id = active_run.named_steps.get(step_key) or active_run.tool_steps.get(step_key)

        self.database.initialize()
        with self.database.connect() as connection:
            artifact_repo = ArtifactRepository(connection)
            artifact = artifact_repo.create(
                run_id=active_run.run_id,
                step_id=step_id,
                artifact_type=artifact_type,
                name=name,
                uri=uri,
                metadata=metadata,
            )
        return artifact.artifact_id

    def record_tool_started(
        self,
        active_run: ActiveRunShadow,
        *,
        tool_call_id: str,
        tool_name: str,
        args: dict[str, Any],
        timestamp: str,
    ) -> ActiveRunShadow:
        self.database.initialize()
        with self.database.connect() as connection:
            step_repo = RunStepRepository(connection)
            step = step_repo.create(
                run_id=active_run.run_id,
                step_type="tool_call",
                title=f"Running {tool_name}",
                status="running",
                display_mode="timeline",
                sort_order=active_run.next_sort_order,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                input_payload=args,
                summary_text=_tool_summary(tool_name, args),
                started_at=timestamp,
            )
        active_run.tool_steps[tool_call_id] = step.step_id
        active_run.next_sort_order += 1
        return active_run

    def record_tool_finished(
        self,
        active_run: ActiveRunShadow,
        *,
        tool_call_id: str,
        tool_name: str,
        tool_output: str,
        timestamp: str,
        failed: bool = False,
    ) -> ActiveRunShadow:
        step_id = active_run.tool_steps.get(tool_call_id)
        if step_id is None:
            return active_run

        self.database.initialize()
        with self.database.connect() as connection:
            step_repo = RunStepRepository(connection)
            step_repo.update_status(
                step_id,
                status="failed" if failed else "completed",
                output_payload={"text": tool_output},
                summary_text=_tool_result_summary(tool_name, tool_output),
                ended_at=timestamp,
            )
        return active_run

    def complete_run(
        self,
        active_run: ActiveRunShadow,
        *,
        meta: Any,
        assistant_message_id: str,
        assistant_text: str,
        assistant_timestamp: str,
    ) -> None:
        self.database.initialize()
        with self.database.connect() as connection:
            conversation_repo = ConversationRepository(connection)
            message_repo = MessageRepository(connection)
            run_repo = RunRepository(connection)

            message_repo.create(
                message_id=assistant_message_id,
                conversation_id=_conversation_id(meta),
                run_id=active_run.run_id,
                role="assistant",
                phase="final_answer",
                visibility="visible",
                content=_text_content_blocks(assistant_text),
                text_preview=assistant_text,
                created_at=assistant_timestamp,
            )
            run_repo.update_status(
                active_run.run_id,
                status="completed",
                final_message_id=assistant_message_id,
                ended_at=assistant_timestamp,
            )
            conversation_repo.upsert(
                conversation_id=_conversation_id(meta),
                title=_conversation_title(meta),
                created_at=_conversation_created_at(meta),
                updated_at=max(_conversation_updated_at(meta), assistant_timestamp),
            )

    def fail_run(
        self,
        active_run: ActiveRunShadow,
        *,
        meta: Any,
        error_message: str,
        ended_at: str,
    ) -> None:
        self.database.initialize()
        with self.database.connect() as connection:
            conversation_repo = ConversationRepository(connection)
            run_repo = RunRepository(connection)

            run_repo.update_status(
                active_run.run_id,
                status="failed",
                error_message=error_message,
                ended_at=ended_at,
            )
            conversation_repo.upsert(
                conversation_id=_conversation_id(meta),
                title=_conversation_title(meta),
                created_at=_conversation_created_at(meta),
                updated_at=max(_conversation_updated_at(meta), ended_at),
            )

    def sync_completed_run_from_messages(
        self,
        *,
        meta: Any,
        user_message: HumanMessage,
        new_messages: list[BaseMessage],
        final_assistant_message: AIMessage | None,
        failed_error: str | None = None,
    ) -> None:
        user_metadata = _message_metadata(user_message)
        active_run = self.start_run(
            meta=meta,
            user_message_id=str(user_metadata["message_id"]),
            user_text=_stringify_content(user_message.content),
            user_timestamp=str(user_metadata["timestamp"]),
        )
        if active_run is None:
            return

        for message in new_messages:
            if isinstance(message, AIMessage) and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_call_id = str(tool_call.get("id") or "")
                    if not tool_call_id:
                        continue
                    self.record_tool_started(
                        active_run,
                        tool_call_id=tool_call_id,
                        tool_name=str(tool_call.get("name") or "unknown_tool"),
                        args=tool_call.get("args") or {},
                        timestamp=str(_message_metadata(message)["timestamp"]),
                    )
            elif getattr(message, "type", None) == "tool":
                tool_call_id = str(getattr(message, "tool_call_id", "") or "")
                if not tool_call_id:
                    continue
                self.record_tool_finished(
                    active_run,
                    tool_call_id=tool_call_id,
                    tool_name=str(getattr(message, "name", None) or "unknown_tool"),
                    tool_output=_stringify_content(message.content),
                    timestamp=str(_message_metadata(message)["timestamp"]),
                    failed=False,
                )

        if failed_error is not None:
            self.fail_run(
                active_run,
                meta=meta,
                error_message=failed_error,
                ended_at=user_metadata["timestamp"],
            )
            return

        if final_assistant_message is None:
            self.fail_run(
                active_run,
                meta=meta,
                error_message="No final assistant message was produced.",
                ended_at=user_metadata["timestamp"],
            )
            return

        assistant_metadata = _message_metadata(final_assistant_message)
        self.complete_run(
            active_run,
            meta=meta,
            assistant_message_id=str(assistant_metadata["message_id"]),
            assistant_text=_stringify_content(final_assistant_message.content),
            assistant_timestamp=str(assistant_metadata["timestamp"]),
        )


def _message_metadata(message: BaseMessage) -> dict[str, str]:
    metadata = dict(getattr(message, "additional_kwargs", {}).get(AGENTBOT_META_KEY) or {})
    return {
        "message_id": str(metadata.get("message_id") or ""),
        "timestamp": str(metadata.get("timestamp") or ""),
    }


def _stringify_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(part for part in parts if part).strip()
    return str(content) if content is not None else ""


def _text_content_blocks(text: str) -> list[dict[str, str]]:
    return [{"type": "text", "text": text}]


def _tool_summary(tool_name: str, args: dict[str, Any]) -> str:
    if not args:
        return f"Calling {tool_name}"
    return f"Calling {tool_name}: {json.dumps(args, ensure_ascii=False)}"


def _tool_result_summary(tool_name: str, output: str) -> str:
    preview = output.strip()
    if len(preview) > 140:
        preview = f"{preview[:137]}..."
    return f"{tool_name} finished: {preview}" if preview else f"{tool_name} finished"


def _conversation_id(meta: Any) -> str:
    return str(getattr(meta, "conversation_id"))


def _conversation_title(meta: Any) -> str:
    title = getattr(meta, "title", None)
    if title is not None:
        return str(title)
    name = getattr(meta, "name", None)
    if name is not None:
        return str(name)
    raise AttributeError("Conversation metadata object is missing both 'title' and 'name'.")


def _conversation_created_at(meta: Any) -> str:
    return str(getattr(meta, "created_at"))


def _conversation_updated_at(meta: Any) -> str:
    return str(getattr(meta, "updated_at"))
