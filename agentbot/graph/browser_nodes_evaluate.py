"""Evaluation-side browser subgraph node helpers."""

from __future__ import annotations

from agentbot.browser.loop_detection import summarize_loop_signal
from agentbot.graph.browser_nodes_common import (
    _build_browser_progress_signal,
    _now_iso,
    _recent_repeated_action_count,
)
from agentbot.graph.state import AgentGraphState


def browser_evaluate(state: AgentGraphState) -> dict[str, object]:
    timestamp = _now_iso()
    action_payloads = list(state.get("browser_pending_actions") or [])
    if not action_payloads:
        single_payload = state.get("browser_pending_action")
        if isinstance(single_payload, dict):
            action_payloads = [single_payload]
    primary_action = action_payloads[0] if action_payloads else {}
    action_type = str(primary_action.get("action_type") or "")
    action_count = int(state.get("browser_action_count") or 0)
    last_action_results = list(state.get("browser_last_action_results") or [])
    executed_count = sum(1 for item in last_action_results if str(item.get("action_type") or "") != "done")
    next_count = action_count + executed_count
    max_actions = int(state.get("browser_max_actions") or 12)
    last_action_result = last_action_results[-1] if last_action_results else (state.get("browser_last_action_result") or {})
    last_action_success = bool(last_action_result.get("success", False))
    last_action_output = last_action_result.get("output") or {}
    interrupted = any(bool((item.get("output") or {}).get("observation_stale")) for item in last_action_results)

    if action_type == "done":
        summary_text = "The browser subgraph decided to stop and finalize the current result."
    elif next_count >= max_actions:
        summary_text = f"Executed {next_count} browser actions and reached the current budget limit."
    elif interrupted:
        summary_text = f"Executed {executed_count} browser actions and interrupted the sequence after page-state changes."
    else:
        summary_text = f"The browser step finished. Prepare to observe the page again ({next_count}/{max_actions})."

    loop_signal = summarize_loop_signal(
        repeated_action_count=_recent_repeated_action_count(
            {
                "browser_action_history": state.get("browser_action_history"),
                "browser_pending_actions": action_payloads,
            }
        ),
        stagnant_count=int(state.get("browser_stagnant_count") or 0),
    ) or state.get("browser_loop_signal")
    progress_signal = _build_browser_progress_signal(
        action_type=str(last_action_result.get("action_type") or action_type),
        action_reason=str(primary_action.get("reason") or ""),
        action_success=last_action_success,
        action_output=last_action_output if isinstance(last_action_output, dict) else {},
        loop_signal=str(loop_signal or ""),
    )
    consecutive_failures = int(state.get("browser_consecutive_failures") or 0)
    if action_type == "done":
        consecutive_failures = 0
    elif last_action_success and "failure" not in progress_signal.lower():
        consecutive_failures = 0
    else:
        consecutive_failures += 1

    return {
        "browser_action_count": next_count,
        "browser_loop_signal": loop_signal,
        "browser_progress_signal": progress_signal,
        "browser_consecutive_failures": consecutive_failures,
        "browser_events": [
            {
                "event": "step_started",
                "step_key": "browser_evaluate",
                "parent_step_key": state.get("browser_parent_step_key"),
                "step_type": "browser_evaluate",
                "title": "Evaluate browser step",
                "status": "running",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": "Evaluate whether the last browser step created useful progress.",
            },
            {
                "event": "step_completed",
                "step_key": "browser_evaluate",
                "step_type": "browser_evaluate",
                "title": "Evaluate browser step",
                "status": "completed",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": f"{summary_text}\n\nProgress signal: {progress_signal}",
                "output": {
                    "action_count": next_count,
                    "max_actions": max_actions,
                    "pending_action_type": action_type,
                    "pending_action_count": len(action_payloads),
                    "executed_action_count": executed_count,
                    "loop_signal": loop_signal,
                    "progress_signal": progress_signal,
                    "consecutive_failures": consecutive_failures,
                },
            },
        ],
    }
