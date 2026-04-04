"""Execution-side browser subgraph node helpers."""

from __future__ import annotations

from agentbot.browser.actions import capture_action_screenshot, execute_browser_actions
from agentbot.browser.loop_detection import compute_action_hash
from agentbot.browser.session import get_runtime_session
from agentbot.browser.views import BrowserAction
from agentbot.graph.browser_nodes_common import (
    _action_sequence_summary_text,
    _friendly_browser_error,
    _now_iso,
    _sequence_result_summary_text,
    _summary_from_state,
)
from agentbot.graph.state import AgentGraphState


def browser_act(state: AgentGraphState) -> dict[str, Any]:
    session_id = state.get("browser_session_id")
    if not session_id:
        raise RuntimeError("Browser session was not initialized before browser_act.")
    action_payloads = list(state.get("browser_pending_actions") or [])
    if not action_payloads:
        single_payload = state.get("browser_pending_action")
        if isinstance(single_payload, dict):
            action_payloads = [single_payload]
    if not action_payloads:
        raise RuntimeError("browser_act was called without pending browser actions.")

    actions = [BrowserAction(**payload) for payload in action_payloads]
    runtime = get_runtime_session(session_id)
    summary = _summary_from_state(state.get("browser_state_summary"))
    timestamp = _now_iso()

    sequence_result = execute_browser_actions(runtime, actions=actions, summary=summary)
    screenshot_path = capture_action_screenshot(runtime, suffix=f"action-{int(state.get('browser_action_count') or 0) + 1}")
    if screenshot_path is not None:
        for result in sequence_result.results:
            output = dict(result.output or {})
            output["screenshot_path"] = str(screenshot_path)
            result.output = output

    action_history = list(state.get("browser_action_history") or [])
    action_results_payload: list[dict[str, Any]] = []
    for action, payload, result in zip(actions, action_payloads, sequence_result.results):
        output_payload = dict(result.output or {})
        action_results_payload.append(
            {
                "action_type": result.action_type,
                "success": result.success,
                "summary_text": result.summary_text,
                "output": output_payload,
            }
        )
        action_history.append(
            {
                "action_type": action.action_type,
                "action_hash": compute_action_hash(payload),
                "reason": action.reason,
                "evaluation_previous_goal": str(state.get("browser_evaluation_previous_goal") or ""),
                "memory": str(state.get("browser_memory") or ""),
                "next_goal": str(state.get("browser_next_goal") or ""),
                "summary_text": result.summary_text,
                "output": output_payload,
            }
        )

    last_result = action_results_payload[-1] if action_results_payload else None
    return {
        "browser_action_history": action_history,
        "browser_last_action_result": last_result,
        "browser_last_action_results": action_results_payload,
        "browser_events": [
            {
                "event": "step_started",
                "step_key": "browser_act",
                "parent_step_key": state.get("browser_parent_step_key"),
                "step_type": "browser_action",
                "title": f"Execute browser step ({len(actions)} actions)",
                "status": "running",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": _action_sequence_summary_text(actions),
                "input": {"actions": action_payloads},
            },
            {
                "event": "step_completed",
                "step_key": "browser_act",
                "step_type": "browser_action",
                "title": f"Execute browser step ({len(actions)} actions)",
                "status": "completed",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": _sequence_result_summary_text(sequence_result),
                "output": {
                    "actions": action_payloads,
                    "results": action_results_payload,
                    "interrupted": sequence_result.interrupted,
                    "interruption_reason": sequence_result.interruption_reason,
                },
            },
        ],
    }


def build_failed_action_result(state: AgentGraphState, exc: Exception) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    action_payloads = list(state.get("browser_pending_actions") or [])
    if not action_payloads:
        single_payload = state.get("browser_pending_action")
        if isinstance(single_payload, dict):
            action_payloads = [single_payload]
    failed_payload = action_payloads[0] if action_payloads else {}
    failed_result = {
        "action_type": str(failed_payload.get("action_type") or "unknown"),
        "success": False,
        "summary_text": _friendly_browser_error(exc),
        "output": {"error": str(exc)},
    }
    action_history = list(state.get("browser_action_history") or [])
    action_history.append(
        {
            "action_type": failed_result["action_type"],
            "action_hash": compute_action_hash(failed_payload) if failed_payload else "",
            "reason": str(failed_payload.get("reason") or ""),
            "evaluation_previous_goal": str(state.get("browser_evaluation_previous_goal") or ""),
            "memory": str(state.get("browser_memory") or ""),
            "next_goal": str(state.get("browser_next_goal") or ""),
            "summary_text": failed_result["summary_text"],
            "output": failed_result["output"],
        }
    )
    return action_history, failed_result
