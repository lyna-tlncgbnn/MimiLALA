"""Shared helpers for browser subgraph nodes."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from langchain_core.messages import BaseMessage

from agentbot.browser.views import (
    BrowserAction,
    BrowserActionSequenceResult,
    BrowserElementBounds,
    BrowserInteractiveElement,
    BrowserPageInfo,
    BrowserSemanticGroup,
    BrowserStateSummary,
    BrowserTabInfo,
)
from agentbot.graph.state import AgentGraphState

URL_PATTERN = re.compile(r"(?:https?|file)://[^\s)]+", re.IGNORECASE)
BROWSER_KEYWORDS = (
    "浏览器",
    "网页",
    "网站",
    "打开",
    "访问",
    "点击",
    "输入",
    "搜索",
    "browser",
    "web",
    "page",
    "website",
    "webpage",
    "open",
    "open url",
    "visit",
    "click",
    "type",
    "search",
)
DEFAULT_BROWSER_MAX_ACTIONS_PER_STEP = 3


def _friendly_browser_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()
    if "target page, context or browser has been closed" in lowered or "has been closed" in lowered:
        return "The browser window, page, or browser context was closed during execution."
    if "browser session not found" in lowered:
        return "The browser session is no longer available."
    if "not visible" in lowered:
        return "The target element is no longer visible."
    if "not attached" in lowered:
        return "The target element is no longer attached to the page."
    if "page changed since observation" in lowered:
        return "The page changed after observation; the agent needs a fresh observation before acting."
    if "timeout" in lowered:
        return f"Browser step timed out: {message}"
    return message


def _build_browser_progress_signal(
    *,
    action_type: str,
    action_reason: str,
    action_success: bool,
    action_output: dict[str, Any],
    loop_signal: str,
) -> str:
    if action_output.get("download"):
        return "The last browser action completed the requested download successfully."
    if action_output.get("download_started"):
        return "The last browser action already started the requested download. Do not click the download control again; wait or finish."
    if action_output.get("download_in_progress"):
        return "The requested download is already in progress. Do not retry the click; wait for the download to complete."
    if action_output.get("download_error"):
        return "The browser triggered the requested download, but saving the file failed. Do not keep clicking; inspect the download error and recover."
    if action_type == "done":
        return "The planner chose to stop and finalize the browser task."
    if not action_success:
        return "The last browser action failed and the next step should recover instead of repeating blindly."
    if action_output.get("page_changed"):
        return "The last browser action changed the page and created meaningful progress."
    if action_output.get("observation_stale"):
        return "The last browser action changed visible browser state and requires a fresh observation."
    if action_type in {"type", "click", "press_enter", "navigate", "new_tab_navigate", "switch_tab"}:
        return "The last browser action executed successfully, but the next observation must verify whether it truly advanced the task."
    if loop_signal:
        return f"Low progress signal detected: {loop_signal}"
    return f"The last browser action ({action_type}) completed with limited visible progress. Re-observe carefully before repeating it. Reason: {action_reason or 'n/a'}"


def _build_browser_recovery_nudges(
    *,
    loop_signal: str,
    progress_signal: str,
    consecutive_failures: int,
    action_count: int,
) -> list[str]:
    nudges: list[str] = []
    if consecutive_failures >= 2:
        nudges.append(
            f"REPLAN SUGGESTED: there have been {consecutive_failures} consecutive low-progress or failed browser steps. Change strategy instead of repeating the same action."
        )
    if loop_signal:
        nudges.append(
            f"LOOP DETECTION: {loop_signal} Avoid repeating the same scroll/wait/click pattern unless the page state clearly changed."
        )
    if progress_signal:
        nudges.append(f"PROGRESS CHECK: {progress_signal}")
    if action_count >= 3 and not nudges:
        nudges.append(
            "RECOVERY CHECK: if the current page still does not expose the target control clearly, try a different visible region or finish with an honest incomplete result."
        )
    return nudges[:4]


def _summary_from_state(payload: Any) -> BrowserStateSummary | None:
    if not isinstance(payload, dict):
        return None
    tabs = []
    for item in payload.get("tabs") or []:
        if isinstance(item, dict):
            tabs.append(
                BrowserTabInfo(
                    tab_id=str(item.get("tab_id") or "tab_1"),
                    url=str(item.get("url") or "about:blank"),
                    title=str(item.get("title") or "Untitled page"),
                    parent_tab_id=_optional_str(item.get("parent_tab_id")),
                )
            )
    page_info_payload = payload.get("page_info") or {}
    page_info = BrowserPageInfo(
        viewport_width=int(page_info_payload.get("viewport_width") or 1280),
        viewport_height=int(page_info_payload.get("viewport_height") or 720),
        scroll_x=int(page_info_payload.get("scroll_x") or 0),
        scroll_y=int(page_info_payload.get("scroll_y") or 0),
        pixels_above=int(page_info_payload.get("pixels_above") or 0),
        pixels_below=int(page_info_payload.get("pixels_below") or 0),
    )
    interactive_elements = []
    for item in payload.get("interactive_elements") or []:
        if isinstance(item, dict):
            bounds_payload = item.get("bounds") if isinstance(item.get("bounds"), dict) else {}
            interactive_elements.append(
                BrowserInteractiveElement(
                    index=int(item.get("index") or 0),
                    kind=str(item.get("kind") or "control"),
                    tag=str(item.get("tag") or "div"),
                    selector=str(item.get("selector") or ""),
                    frame_path=[str(part) for part in (item.get("frame_path") or []) if str(part).strip()],
                    text=str(item.get("text") or ""),
                    label_text=str(item.get("label_text") or ""),
                    href=str(item.get("href") or ""),
                    role=str(item.get("role") or ""),
                    ax_role=str(item.get("ax_role") or ""),
                    ax_name=str(item.get("ax_name") or ""),
                    input_type=str(item.get("input_type") or ""),
                    name=str(item.get("name") or ""),
                    placeholder=str(item.get("placeholder") or ""),
                    title=str(item.get("title") or ""),
                    aria_label=str(item.get("aria_label") or ""),
                    enabled=bool(item.get("enabled", True)),
                    visible=bool(item.get("visible", True)),
                    in_viewport=bool(item.get("in_viewport", True)),
                    disabled=bool(item.get("disabled", False)),
                    checked=bool(item.get("checked", False)),
                    expanded=bool(item.get("expanded", False)),
                    pressed=bool(item.get("pressed", False)),
                    iframe_hint=str(item.get("iframe_hint") or ""),
                    section_hint=str(item.get("section_hint") or ""),
                    landmark_hint=str(item.get("landmark_hint") or ""),
                    semantic_group=str(item.get("semantic_group") or ""),
                    semantic_score=float(item.get("semantic_score") or 0.0),
                    bounds=BrowserElementBounds(
                        x=float(bounds_payload.get("x") or 0.0),
                        y=float(bounds_payload.get("y") or 0.0),
                        width=float(bounds_payload.get("width") or 0.0),
                        height=float(bounds_payload.get("height") or 0.0),
                    ),
                )
            )
    semantic_groups = []
    for item in payload.get("semantic_groups") or []:
        if isinstance(item, dict):
            semantic_groups.append(
                BrowserSemanticGroup(
                    kind=str(item.get("kind") or "generic"),
                    label=str(item.get("label") or "Other interactive controls"),
                    element_indexes=[int(index) for index in (item.get("element_indexes") or []) if str(index).strip()],
                )
            )
    return BrowserStateSummary(
        url=str(payload.get("url") or "about:blank"),
        title=str(payload.get("title") or "Untitled page"),
        tabs=tabs,
        page_info=page_info,
        dom_summary=str(payload.get("dom_summary") or ""),
        interactive_elements=interactive_elements,
        semantic_groups=semantic_groups,
        prioritized_hints=[str(item) for item in (payload.get("prioritized_hints") or []) if str(item).strip()],
        screenshot_path=_optional_str(payload.get("screenshot_path")),
        observation_fingerprint=_optional_str(payload.get("observation_fingerprint")),
        iframe_summaries=[str(item) for item in (payload.get("iframe_summaries") or [])],
        recent_events=[str(item) for item in (payload.get("recent_events") or [])],
        browser_errors=[str(item) for item in (payload.get("browser_errors") or [])],
    )


def _action_summary_text(action: BrowserAction) -> str:
    if action.action_type == "done":
        return action.reason or "Finish the browser task."
    if action.action_type == "navigate":
        return f"Open page {action.url or '(missing url)'}"
    if action.action_type == "new_tab_navigate":
        return f"Open a new tab at {action.url or '(missing url)'}"
    if action.action_type == "click":
        return f"Click element [{action.element_index}]"
    if action.action_type == "type":
        return f"Type into element [{action.element_index}]"
    if action.action_type == "press_enter":
        return "Press Enter"
    if action.action_type == "scroll":
        return f"Scroll {action.direction or 'down'} by {action.amount or 600} pixels"
    if action.action_type == "wait":
        return f"Wait {action.amount or 2} seconds"
    if action.action_type == "go_back":
        return "Go back"
    if action.action_type == "switch_tab":
        return f"Switch to tab {action.tab_id or 'latest'}"
    return f"Execute {action.action_type}"


def _action_sequence_summary_text(actions: list[BrowserAction]) -> str:
    return " -> ".join(_action_summary_text(action) for action in actions)


def _sequence_result_summary_text(sequence_result: BrowserActionSequenceResult) -> str:
    summaries = [result.summary_text for result in sequence_result.results if result.summary_text]
    text = "\n".join(summaries) if summaries else "Browser action sequence finished."
    if sequence_result.interrupted and sequence_result.interruption_reason:
        text += f"\n\nSequence interrupted: {sequence_result.interruption_reason}"
    return text


def _latest_user_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if getattr(message, "type", None) == "human":
            content = getattr(message, "content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "".join(
                    str(item.get("text", "")) for item in content if isinstance(item, dict) and item.get("type") == "text"
                )
            return str(content)
    return ""


def _contains_browser_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in BROWSER_KEYWORDS)


def _extract_url(text: str) -> str | None:
    match = URL_PATTERN.search(text)
    return match.group(0) if match else None


def _extract_browser_task(text: str) -> str | None:
    normalized = text.strip()
    if not normalized:
        return None
    if _extract_url(normalized):
        return normalized
    if _contains_browser_keyword(normalized):
        return normalized
    return None


def _title_from_url(url: str) -> str:
    if url == "about:blank":
        return "Blank page"
    without_scheme = re.sub(r"^https?://", "", url)
    return without_scheme.split("/", 1)[0] or url


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "".join(parts)
    return str(content)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_str_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    items = [str(item).strip() for item in value if str(item).strip()]
    return items or None


def _page_title_from_summary(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    title = payload.get("title")
    if title is None:
        return None
    text = str(title).strip()
    return text or None


def _recent_repeated_action_count(state: AgentGraphState | dict[str, Any]) -> int:
    history = list((state.get("browser_action_history") if isinstance(state, dict) else state.get("browser_action_history")) or [])
    hashes = [str(item.get("action_hash") or "") for item in history if item.get("action_hash")]
    if not hashes:
        return 0
    last_hash = hashes[-1]
    return sum(1 for item in hashes if item == last_hash)


def _assess_browser_completion(
    *,
    requires_approval: bool,
    pending_action_type: str,
    pending_action_reason: str,
    action_count: int,
    max_actions: int,
    loop_signal: str,
    failure_reason: str,
    last_action_success: bool,
    last_action_output: dict[str, Any] | None = None,
) -> tuple[str, str | None]:
    action_output = last_action_output or {}
    if requires_approval:
        return "approval_required", None
    if failure_reason:
        return "failed", failure_reason
    if action_output.get("download"):
        return "completed", "The requested download completed successfully."
    if action_output.get("download_error"):
        message = str(action_output.get("download_error", {}).get("message") or "").strip()
        return "incomplete", message or "The download was triggered but failed while being saved."
    if action_output.get("download_started") or action_output.get("download_in_progress"):
        return "completed", "The requested download has already started; do not click the download button again."
    if not last_action_success:
        return "incomplete", "The last browser action failed."
    if pending_action_type != "done" and action_count >= max_actions:
        return "incomplete", f"Reached the configured browser action budget ({max_actions})."

    lowered_reason = pending_action_reason.lower()
    if "reached action budget" in lowered_reason:
        return "incomplete", pending_action_reason
    if loop_signal and pending_action_type == "done":
        return "incomplete", loop_signal
    return "completed", pending_action_reason or None


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
