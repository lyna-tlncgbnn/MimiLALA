"""Helpers for translating graph update payloads into runtime persistence and UI events."""

from __future__ import annotations

from typing import Any, Iterator
from uuid import uuid4

from langchain_core.messages import AIMessage, ToolMessage

from agentbot.storage.common import AGENTBOT_META_KEY
from agentbot.storage.shadow_runtime import ActiveRunShadow, RuntimeShadowWriter
from agentbot.tools.infra.error_handling import is_tool_error_output


def apply_runtime_events_from_updates(
    payload: Any,
    active_run: ActiveRunShadow,
    runtime_writer: RuntimeShadowWriter,
    emitted_tool_calls: set[str],
) -> tuple[ActiveRunShadow, list[dict[str, Any]]]:
    events = list(
        _iter_runtime_events_from_updates(
            payload,
            active_run,
            runtime_writer,
            emitted_tool_calls,
        )
    )
    return active_run, events


def _iter_runtime_events_from_updates(
    payload: Any,
    active_run: ActiveRunShadow,
    runtime_writer: RuntimeShadowWriter,
    emitted_tool_calls: set[str],
) -> Iterator[dict[str, Any]]:
    if not isinstance(payload, dict):
        return

    for node_update in payload.values():
        if not isinstance(node_update, dict):
            continue

        browser_events = node_update.get("browser_events")
        if isinstance(browser_events, list):
            for browser_event in browser_events:
                if not isinstance(browser_event, dict):
                    continue
                browser_ui_event = _apply_browser_event(active_run, runtime_writer, browser_event)
                if browser_ui_event is not None:
                    yield browser_ui_event

        messages = node_update.get("messages")
        if messages is None:
            continue
        if not isinstance(messages, list):
            messages = [messages]

        for message in messages:
            if isinstance(message, AIMessage) and message.tool_calls:
                metadata = _message_metadata(message)
                for tool_call in message.tool_calls:
                    tool_call_id = str(tool_call.get("id") or _new_prefixed_id("call"))
                    if tool_call_id in emitted_tool_calls:
                        continue
                    emitted_tool_calls.add(tool_call_id)
                    active_run = runtime_writer.record_tool_started(
                        active_run,
                        tool_call_id=tool_call_id,
                        tool_name=str(tool_call.get("name") or "unknown_tool"),
                        args=tool_call.get("args") or {},
                        timestamp=metadata["timestamp"],
                    )
                    step_id = active_run.tool_steps.get(tool_call_id)
                    yield _ui_event(
                        "step_started",
                        run_id=active_run.run_id,
                        step_id=step_id,
                        step_type="tool_call",
                        title=f"Running {str(tool_call.get('name') or 'unknown_tool')}",
                        status="running",
                        display_mode="timeline",
                        tool_name=str(tool_call.get("name") or "unknown_tool"),
                        tool_call_id=tool_call_id,
                        args=tool_call.get("args") or {},
                        timestamp=metadata["timestamp"],
                    )
            elif isinstance(message, ToolMessage):
                metadata = _message_metadata(message)
                tool_output = _stringify_message_content(message.content)
                failed = is_tool_error_output(tool_output)
                active_run = runtime_writer.record_tool_finished(
                    active_run,
                    tool_call_id=str(message.tool_call_id or ""),
                    tool_name=message.name or "unknown_tool",
                    tool_output=tool_output,
                    timestamp=metadata["timestamp"],
                    failed=failed,
                )
                step_id = active_run.tool_steps.get(str(message.tool_call_id or ""))
                yield _ui_event(
                    "step_completed",
                    run_id=active_run.run_id,
                    step_id=step_id,
                    step_type="tool_call",
                    title=f"Running {message.name or 'unknown_tool'}",
                    status="failed" if failed else "completed",
                    tool_name=message.name or "unknown_tool",
                    tool_call_id=str(message.tool_call_id or ""),
                    output=tool_output,
                    timestamp=metadata["timestamp"],
                )


def _apply_browser_event(
    active_run: ActiveRunShadow,
    runtime_writer: RuntimeShadowWriter,
    browser_event: dict[str, Any],
) -> dict[str, Any] | None:
    event_name = str(browser_event.get("event") or "").strip()
    step_key = str(browser_event.get("step_key") or "").strip()
    if not event_name or not step_key:
        return None

    step_type = str(browser_event.get("step_type") or "browser_step")
    title = str(browser_event.get("title") or step_type)
    timestamp = str(browser_event.get("timestamp") or "")
    display_mode = str(browser_event.get("display_mode") or "timeline")
    summary_text = (
        str(browser_event.get("summary_text"))
        if browser_event.get("summary_text") is not None
        else None
    )

    if event_name == "step_started":
        active_run = runtime_writer.record_step_started(
            active_run,
            step_key=step_key,
            step_type=step_type,
            title=title,
            timestamp=timestamp,
            display_mode=display_mode,
            parent_step_key=_optional_string(browser_event.get("parent_step_key")),
            summary_text=summary_text,
            input_payload=browser_event.get("input"),
        )
        return _ui_event(
            "step_started",
            run_id=active_run.run_id,
            step_id=active_run.named_steps.get(step_key),
            step_type=step_type,
            title=title,
            status="running",
            display_mode=display_mode,
            tool_name=browser_event.get("tool_name") or step_type,
            tool_call_id=step_key,
            args=browser_event.get("input") or {},
            timestamp=timestamp,
        )

    if event_name == "step_completed":
        output_payload = browser_event.get("output")
        output_payload = _persist_browser_artifacts(
            active_run,
            runtime_writer,
            step_key=step_key,
            step_type=step_type,
            output_payload=output_payload,
        )
        active_run = runtime_writer.record_step_finished(
            active_run,
            step_key=step_key,
            timestamp=timestamp,
            status=str(browser_event.get("status") or "completed"),
            output_payload=output_payload,
            summary_text=summary_text,
        )
        return _ui_event(
            "step_completed",
            run_id=active_run.run_id,
            step_id=active_run.named_steps.get(step_key),
            step_type=step_type,
            title=title,
            status=str(browser_event.get("status") or "completed"),
            tool_name=browser_event.get("tool_name") or step_type,
            tool_call_id=step_key,
            output=_stringify_message_content(output_payload),
            timestamp=timestamp,
        )

    return None


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _ui_event(event: str, **payload: Any) -> dict[str, Any]:
    return {"event": event, "data": payload}


def _persist_browser_artifacts(
    active_run: ActiveRunShadow,
    runtime_writer: RuntimeShadowWriter,
    *,
    step_key: str,
    step_type: str,
    output_payload: Any,
) -> Any:
    if not isinstance(output_payload, dict):
        return output_payload

    enriched = dict(output_payload)
    artifact_ids: list[str] = []

    screenshot_path = enriched.get("screenshot_path")
    if isinstance(screenshot_path, str) and screenshot_path.strip():
        artifact_ids.append(
            runtime_writer.record_artifact(
                active_run,
                artifact_type="browser_screenshot",
                name=f"{step_type}_screenshot",
                uri=screenshot_path,
                step_key=step_key,
                metadata={"step_type": step_type},
            )
        )

    if step_type == "browser_observe":
        dom_summary = enriched.get("dom_summary")
        url = enriched.get("url")
        if isinstance(dom_summary, str) and dom_summary.strip():
            artifact_ids.append(
                runtime_writer.record_artifact(
                    active_run,
                    artifact_type="browser_page_summary",
                    name="browser_observe_summary",
                    uri=f"run://{active_run.run_id}/steps/{step_key}/page-summary",
                    step_key=step_key,
                    metadata={
                        "url": url,
                        "title": enriched.get("title"),
                        "dom_summary": dom_summary,
                    },
                )
            )

    if artifact_ids:
        enriched["artifact_ids"] = artifact_ids
    return enriched


def _message_metadata(message) -> dict[str, str]:
    metadata = dict(getattr(message, "additional_kwargs", {}).get(AGENTBOT_META_KEY) or {})
    return {
        "message_id": str(metadata.get("message_id") or _new_prefixed_id("msg")),
        "timestamp": str(metadata.get("timestamp") or ""),
    }


def _stringify_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                text_chunks.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                text_chunks.append(str(item.get("text", "")))
        return "\n".join(chunk for chunk in text_chunks if chunk).strip()
    if isinstance(content, dict):
        return str(content)
    return str(content) if content is not None else ""


def _new_prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
