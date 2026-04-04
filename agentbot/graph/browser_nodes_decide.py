"""Planner-side browser subgraph node helpers."""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agentbot.browser.views import BrowserAction, BrowserStateSummary
from agentbot.graph.browser_nodes_common import (
    DEFAULT_BROWSER_MAX_ACTIONS_PER_STEP,
    _action_sequence_summary_text,
    _build_browser_recovery_nudges,
    _extract_url,
    _message_text,
    _now_iso,
    _optional_int,
    _optional_str,
    _optional_str_list,
    _parse_json_object,
    _summary_from_state,
)
from agentbot.graph.state import AgentGraphState
from agentbot.prompts.browser_subgraph import browser_done_action, build_browser_planner_prompt


def browser_decide(state: AgentGraphState, llm: BaseChatModel) -> dict[str, Any]:
    timestamp = _now_iso()
    browser_task = state.get("browser_task") or ""
    action_history = list(state.get("browser_action_history") or [])
    action_count = int(state.get("browser_action_count") or 0)
    max_actions = int(state.get("browser_max_actions") or 12)
    max_actions_per_step = max(1, int(state.get("browser_max_actions_per_step") or DEFAULT_BROWSER_MAX_ACTIONS_PER_STEP))
    summary = _summary_from_state(state.get("browser_state_summary"))
    planner_step = {
        "evaluation_previous_goal": str(state.get("browser_evaluation_previous_goal") or "").strip(),
        "memory": str(state.get("browser_memory") or "").strip(),
        "next_goal": str(state.get("browser_next_goal") or "").strip(),
    }
    current_plan = _normalize_browser_plan(state.get("browser_plan"))
    plan_description = _render_browser_plan_description(current_plan)
    recovery_nudges = _build_browser_recovery_nudges(
        loop_signal=str(state.get("browser_loop_signal") or "").strip(),
        progress_signal=str(state.get("browser_progress_signal") or "").strip(),
        consecutive_failures=int(state.get("browser_consecutive_failures") or 0),
        action_count=action_count,
    )

    if action_count >= max_actions:
        actions = [browser_done_action(reason=f"Reached action budget ({max_actions}).")]
        planner_step = {
            "evaluation_previous_goal": planner_step["evaluation_previous_goal"] or "The browser task reached the configured action budget before completion was verified. Verdict: Incomplete",
            "memory": planner_step["memory"] or "The browser task used the available browser action budget and should stop with an incomplete result.",
            "next_goal": "Finish and explain that the browser task stopped because the action budget was exhausted.",
        }
    elif state.get("browser_loop_signal") and action_count >= 2:
        actions = [browser_done_action(reason=str(state.get("browser_loop_signal")))]
        planner_step = {
            "evaluation_previous_goal": planner_step["evaluation_previous_goal"] or "Recent browser steps did not create meaningful progress. Verdict: Failure",
            "memory": planner_step["memory"] or "The browser task appears stuck on the current page and should stop instead of repeating similar actions.",
            "next_goal": "Finish and explain that the browser loop was stopped after repeated low-progress steps.",
        }
    else:
        planner_step = _plan_browser_step(
            llm=llm,
            task=browser_task,
            summary=summary,
            action_history=action_history,
            current_url=state.get("browser_current_url"),
            evaluation_previous_goal=planner_step["evaluation_previous_goal"],
            memory=planner_step["memory"],
            next_goal=planner_step["next_goal"],
            progress_signal=str(state.get("browser_progress_signal") or "").strip(),
            consecutive_failures=int(state.get("browser_consecutive_failures") or 0),
            recovery_nudges=recovery_nudges,
            plan_description=plan_description,
            max_actions_per_step=max_actions_per_step,
        )
        actions = planner_step["actions"]

    next_plan, next_plan_item = _update_browser_plan_from_model_output(
        current_plan=current_plan,
        plan_update=planner_step.get("plan_update"),
        current_plan_item=planner_step.get("current_plan_item"),
    )

    action_payloads = [asdict(action) for action in actions]
    output_payload = {
        "actions": action_payloads,
        "evaluation_previous_goal": planner_step["evaluation_previous_goal"],
        "memory": planner_step["memory"],
        "next_goal": planner_step["next_goal"],
        "current_plan_item": planner_step.get("current_plan_item"),
        "plan_update": planner_step.get("plan_update"),
    }
    decision_summary = (
        f"Evaluation: {planner_step['evaluation_previous_goal']}\n"
        f"Memory: {planner_step['memory']}\n"
        f"Next goal: {planner_step['next_goal']}\n"
        f"Actions: {_action_sequence_summary_text(actions)}"
    )
    return {
        "browser_pending_action": action_payloads[0],
        "browser_pending_actions": action_payloads,
        "browser_requires_approval": False,
        "browser_approval_reason": None,
        "browser_status": state.get("browser_status"),
        "browser_evaluation_previous_goal": planner_step["evaluation_previous_goal"],
        "browser_memory": planner_step["memory"],
        "browser_next_goal": planner_step["next_goal"],
        "browser_plan": next_plan,
        "browser_current_plan_item": next_plan_item,
        "browser_plan_generation_step": action_count if planner_step.get("plan_update") is not None else state.get("browser_plan_generation_step"),
        "browser_events": [
            {
                "event": "step_started",
                "step_key": "browser_decide",
                "parent_step_key": state.get("browser_parent_step_key"),
                "step_type": "browser_decide",
                "title": "Plan next browser action",
                "status": "running",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": "Plan the next browser action from the current page state.",
            },
            {
                "event": "step_completed",
                "step_key": "browser_decide",
                "step_type": "browser_decide",
                "title": "Plan next browser action",
                "status": "completed",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": decision_summary,
                "output": output_payload,
            },
        ],
    }


def _plan_browser_step(
    *,
    llm: BaseChatModel,
    task: str,
    summary: BrowserStateSummary | None,
    action_history: list[dict[str, Any]],
    current_url: str | None,
    evaluation_previous_goal: str | None,
    memory: str | None,
    next_goal: str | None,
    progress_signal: str | None,
    consecutive_failures: int,
    recovery_nudges: list[str],
    plan_description: str | None,
    max_actions_per_step: int,
) -> dict[str, Any]:
    prompt = build_browser_planner_prompt(
        task=task,
        summary=summary,
        action_history=action_history,
        current_url=current_url,
        evaluation_previous_goal=evaluation_previous_goal,
        memory=memory,
        next_goal=next_goal,
        progress_signal=progress_signal,
        consecutive_failures=consecutive_failures,
        recovery_nudges=recovery_nudges,
        plan_description=plan_description,
        max_actions_per_step=max_actions_per_step,
    )
    try:
        response = llm.invoke(
            [
                SystemMessage(content="You are a precise browser planner that returns JSON only."),
                HumanMessage(content=prompt),
            ]
        )
    except Exception:
        return _fallback_browser_step(task=task, summary=summary, action_history=action_history)

    raw_text = _message_text(response)
    try:
        payload = _parse_json_object(raw_text)
        actions = _parse_browser_actions_payload(payload.get("action"), max_actions_per_step=max_actions_per_step)
        return {
            "evaluation_previous_goal": str(payload.get("evaluation_previous_goal") or "Previous step still needs verification. Verdict: Uncertain").strip(),
            "memory": str(payload.get("memory") or "").strip() or "No browser memory recorded for this step.",
            "next_goal": str(payload.get("next_goal") or "").strip() or "Continue the browser task with the next justified action.",
            "current_plan_item": _optional_int(payload.get("current_plan_item")),
            "plan_update": _optional_str_list(payload.get("plan_update")),
            "actions": actions,
        }
    except Exception:
        return _fallback_browser_step(task=task, summary=summary, action_history=action_history)


def _parse_browser_actions_payload(raw_actions: Any, *, max_actions_per_step: int) -> list[BrowserAction]:
    if not isinstance(raw_actions, list) or not raw_actions:
        raise ValueError("Browser planner output must include a non-empty action list.")

    parsed_actions = [_browser_action_from_payload(item) for item in raw_actions][:max_actions_per_step]
    if not parsed_actions:
        raise ValueError("Browser planner output produced no usable actions.")
    if any(action.action_type == "done" for action in parsed_actions[1:]):
        raise ValueError("Done may only appear as the only action in a browser step.")
    if parsed_actions[0].action_type == "done" and len(parsed_actions) > 1:
        raise ValueError("Done may not be combined with other browser actions.")
    return parsed_actions


def _browser_action_from_payload(raw_action: Any) -> BrowserAction:
    if not isinstance(raw_action, dict):
        raise ValueError("Browser action payload must be an object.")

    if "action_type" in raw_action:
        return BrowserAction(
            action_type=str(raw_action.get("action_type") or "done"),
            reason=str(raw_action.get("reason") or ""),
            url=_optional_str(raw_action.get("url")),
            element_index=_optional_int(raw_action.get("element_index")),
            text=_optional_str(raw_action.get("text")),
            direction=_optional_str(raw_action.get("direction")),
            amount=_optional_int(raw_action.get("amount")),
            tab_id=_optional_str(raw_action.get("tab_id")),
        )

    if len(raw_action) != 1:
        raise ValueError("Nested browser-use style action must have exactly one tool key.")

    tool_name, tool_payload = next(iter(raw_action.items()))
    params = tool_payload if isinstance(tool_payload, dict) else {}
    tool_name = str(tool_name or "").strip().lower()

    if tool_name == "navigate":
        return BrowserAction(action_type="navigate", reason=str(params.get("reason") or ""), url=_optional_str(params.get("url")))
    if tool_name == "new_tab_navigate":
        return BrowserAction(action_type="new_tab_navigate", reason=str(params.get("reason") or ""), url=_optional_str(params.get("url")))
    if tool_name == "click":
        return BrowserAction(action_type="click", reason=str(params.get("reason") or ""), element_index=_optional_int(params.get("index") or params.get("element_index")))
    if tool_name in {"input", "type"}:
        return BrowserAction(
            action_type="type",
            reason=str(params.get("reason") or ""),
            element_index=_optional_int(params.get("index") or params.get("element_index")),
            text=_optional_str(params.get("text") or params.get("value")),
        )
    if tool_name == "press_enter":
        return BrowserAction(action_type="press_enter", reason=str(params.get("reason") or ""))
    if tool_name == "scroll":
        return BrowserAction(action_type="scroll", reason=str(params.get("reason") or ""), direction=_optional_str(params.get("direction")), amount=_optional_int(params.get("amount")))
    if tool_name == "wait":
        return BrowserAction(action_type="wait", reason=str(params.get("reason") or ""), amount=_optional_int(params.get("seconds") or params.get("amount")))
    if tool_name == "go_back":
        return BrowserAction(action_type="go_back", reason=str(params.get("reason") or ""))
    if tool_name == "switch_tab":
        return BrowserAction(action_type="switch_tab", reason=str(params.get("reason") or ""), tab_id=_optional_str(params.get("tab_id")))
    if tool_name == "done":
        return BrowserAction(action_type="done", reason=str(params.get("text") or params.get("reason") or ""))
    raise ValueError(f"Unsupported browser action payload: {tool_name}")


def _fallback_browser_step(
    *,
    task: str,
    summary: BrowserStateSummary | None,
    action_history: list[dict[str, Any]],
) -> dict[str, Any]:
    lowered = task.lower()
    if summary is None:
        url = _extract_url(task)
        if url:
            return _wrap_fallback_step(
                actions=[BrowserAction(action_type="navigate", reason="Fallback navigate to detected URL.", url=url)],
                evaluation="No page summary was available yet. Verdict: Uncertain",
                memory="The browser task has not collected a usable page summary yet.",
                next_goal="Open the detected URL to begin the browser task.",
            )
        return _wrap_fallback_step(
            actions=[browser_done_action(reason="No browser summary available.")],
            evaluation="No page summary was available. Verdict: Failure",
            memory="The browser task could not inspect the current page state.",
            next_goal="Stop and report that browser observation was unavailable.",
        )

    if not action_history and ("click" in lowered):
        for element in summary.interactive_elements:
            if element.text and element.text.lower() in lowered:
                return _wrap_fallback_step(
                    actions=[BrowserAction(action_type="click", reason="Fallback matched visible element text.", element_index=element.index)],
                    evaluation="No previous browser step has been verified yet. Verdict: Uncertain",
                    memory="Fallback planning matched a visible element from the current page summary.",
                    next_goal="Click the matched visible element to start making progress on the browser task.",
                )

    if not action_history and ("search" in lowered):
        text_match = re.search(r'"([^"]+)"', task)
        input_text = text_match.group(1) if text_match else None
        if input_text:
            for element in summary.interactive_elements:
                if element.kind in {"input", "textarea", "select"}:
                    return _wrap_fallback_step(
                        actions=[BrowserAction(action_type="type", reason="Fallback matched first visible input-like element.", element_index=element.index, text=input_text)],
                        evaluation="No previous browser step has been verified yet. Verdict: Uncertain",
                        memory="Fallback planning chose the first visible input-like element from the current summary.",
                        next_goal="Type the requested text into the matched form control.",
                    )

    return _wrap_fallback_step(
        actions=[browser_done_action(reason="Fallback chose done.")],
        evaluation="The planner could not justify a safe next browser action from the current state. Verdict: Failure",
        memory="Fallback planning did not find a reliable next browser action in the current page summary.",
        next_goal="Stop and report that the browser task needs a different strategy.",
    )


def _wrap_fallback_step(*, actions: list[BrowserAction], evaluation: str, memory: str, next_goal: str) -> dict[str, Any]:
    return {
        "evaluation_previous_goal": evaluation,
        "memory": memory,
        "next_goal": next_goal,
        "current_plan_item": None,
        "plan_update": None,
        "actions": actions,
    }


def _normalize_browser_plan(raw_plan: Any) -> list[dict[str, Any]] | None:
    if not isinstance(raw_plan, list):
        return None
    normalized: list[dict[str, Any]] = []
    for item in raw_plan:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        status = str(item.get("status") or "pending").strip().lower()
        if status not in {"pending", "current", "done", "skipped"}:
            status = "pending"
        normalized.append({"text": text, "status": status})
    return normalized or None


def _render_browser_plan_description(plan: list[dict[str, Any]] | None) -> str | None:
    if not plan:
        return None
    markers = {"done": "[x]", "current": "[>]", "pending": "[ ]", "skipped": "[-]"}
    lines = []
    for index, item in enumerate(plan):
        marker = markers.get(str(item.get("status") or "pending"), "[ ]")
        lines.append(f"{marker} {index}: {str(item.get('text') or '').strip()}")
    return "\n".join(lines)


def _update_browser_plan_from_model_output(
    *,
    current_plan: list[dict[str, Any]] | None,
    plan_update: list[str] | None,
    current_plan_item: int | None,
) -> tuple[list[dict[str, Any]] | None, int | None]:
    if plan_update is not None:
        next_plan = [{"text": step_text, "status": "pending"} for step_text in plan_update if step_text.strip()]
        if next_plan:
            next_plan[0]["status"] = "current"
            return next_plan, 0
        return None, None

    if not current_plan:
        return None, None

    next_plan = [{"text": str(item.get("text") or ""), "status": str(item.get("status") or "pending")} for item in current_plan]
    if current_plan_item is None:
        return next_plan, _current_browser_plan_index(next_plan)

    new_index = max(0, min(current_plan_item, len(next_plan) - 1))
    old_index = _current_browser_plan_index(next_plan)
    if old_index is None:
        old_index = 0

    for idx, item in enumerate(next_plan):
        if idx < new_index and item["status"] in {"pending", "current"}:
            item["status"] = "done"
        elif idx == new_index:
            item["status"] = "current"
        elif item["status"] == "current":
            item["status"] = "pending"
    return next_plan, new_index


def _current_browser_plan_index(plan: list[dict[str, Any]]) -> int | None:
    for index, item in enumerate(plan):
        if str(item.get("status") or "") == "current":
            return index
    return None
