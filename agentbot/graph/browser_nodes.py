"""Nodes for the browser subgraph."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agentbot.graph.browser_state import BrowserSubgraphState
from agentbot.models.browser import (
    BrowserActionPlan,
    BrowserActionResultModel,
    BrowserObservation,
    BrowserPlannerOutput,
    BrowserStepRecord,
)
from agentbot.prompts.browser_subgraph import get_browser_subgraph_system_prompt
from agentbot.services.browser_runtime import runtime_manager


def browser_enter(state: BrowserSubgraphState) -> BrowserSubgraphState:
    """Start a browser-use-backed worker session."""
    session_id = runtime_manager.create_session(
        state.get("start_url"),
        llm_config=state.get("llm_config"),
    )
    return {
        "browser_session_id": session_id,
        "status": "running",
        "step_count": 0,
        "steps": [],
        "error_message": None,
        "final_response": None,
    }


def browser_observe(state: BrowserSubgraphState) -> BrowserSubgraphState:
    """Capture a serializable browser observation."""
    session_id = _require_session_id(state)
    observation = runtime_manager.observe(session_id)
    return {
        "current_url": observation.url,
        "page_title": observation.title,
        "browser_state_summary": observation.model_dump(),
        "selector_map_digest": _build_selector_digest(observation),
    }


def browser_plan(state: BrowserSubgraphState, llm: BaseChatModel) -> BrowserSubgraphState:
    """Choose exactly one next browser action using browser-use style output."""
    structured_llm = llm.with_structured_output(BrowserPlannerOutput)
    observation = BrowserObservation.model_validate(state.get("browser_state_summary") or {})
    step_count = int(state.get("step_count", 0))
    max_steps = int(state.get("max_steps", 5))
    last_result = state.get("last_action_result") or {}

    prompt = [
        SystemMessage(
            content=get_browser_subgraph_system_prompt(max_steps),
        ),
        HumanMessage(
            content=(
                "<user_request>\n"
                f"{state['task']}\n"
                "</user_request>\n\n"
                "<agent_history>\n"
                f"{_build_agent_history(state)}\n"
                "</agent_history>\n\n"
                "<agent_state>\n"
                f"step_info: {step_count} / {max_steps}\n"
                f"last_action_result: {last_result}\n"
                "</agent_state>\n\n"
                "<browser_state>\n"
                f"Current URL: {observation.url}\n"
                f"Page title: {observation.title}\n"
                f"Recent browser events: {observation.recent_events or '(none)'}\n"
                "Interactive Elements:\n"
                f"{state.get('selector_map_digest', '') or '(none)'}\n\n"
                "Visible page content:\n"
                f"{observation.llm_representation[:12000]}\n"
                "</browser_state>"
            )
        ),
    ]
    planner_output = structured_llm.invoke(prompt)
    reason = planner_output.next_goal.strip() or planner_output.evaluation_previous_goal.strip()
    action = planner_output.action[0].to_execution_plan(reason=reason)
    return {
        "last_action": action.model_dump(),
        "steps": [
            *state.get("steps", []),
            BrowserStepRecord(
                step_number=step_count + 1,
                action=action,
                result=None,
            ).model_dump(),
        ],
    }


def browser_act(state: BrowserSubgraphState) -> BrowserSubgraphState:
    """Execute the planned browser action via the runtime bridge."""
    session_id = _require_session_id(state)
    action = BrowserActionPlan.model_validate(state.get("last_action") or {})
    result = runtime_manager.execute_action(session_id, action)
    steps = list(state.get("steps", []))
    if steps:
        steps[-1]["result"] = result.model_dump()
    update: BrowserSubgraphState = {
        "last_action_result": result.model_dump(),
        "step_count": int(state.get("step_count", 0)) + 1,
        "steps": steps,
    }
    if not result.success:
        update["status"] = "failed"
        update["error_message"] = result.error
    return update


def browser_finish(state: BrowserSubgraphState) -> BrowserSubgraphState:
    """Close the runtime session and produce the final task response."""
    session_id = state.get("browser_session_id")
    if session_id:
        runtime_manager.close_session(session_id)

    if state.get("status") == "failed":
        return {
            "final_response": state.get("final_response") or state.get("error_message"),
            "status": "failed",
        }

    last_action = state.get("last_action") or {}
    final_response = state.get("final_response")
    if not final_response and last_action.get("action_type") == "done":
        final_response = str(last_action.get("final_response") or "")
    if not final_response:
        last_result_payload = state.get("last_action_result") or {}
        if last_result_payload:
            last_result = BrowserActionResultModel.model_validate(last_result_payload)
            final_response = last_result.extracted_content or "Browser task completed."
        else:
            final_response = "Browser task completed."

    return {
        "final_response": final_response,
        "status": "completed",
    }


def _require_session_id(state: BrowserSubgraphState) -> str:
    session_id = state.get("browser_session_id")
    if not session_id:
        raise RuntimeError("Browser session has not been initialized.")
    return session_id


def _build_selector_digest(observation: BrowserObservation) -> str:
    lines: list[str] = []
    for item in observation.selector_preview:
        lines.append(
            f"[{item.get('index')}] <{item.get('tag')}> {str(item.get('label') or '').strip()}".strip()
        )
    return "\n".join(lines)


def _build_agent_history(state: BrowserSubgraphState) -> str:
    steps = state.get("steps", [])
    if not steps:
        return "No previous browser steps."

    history_lines: list[str] = []
    for raw_step in steps[-3:]:
        step = BrowserStepRecord.model_validate(raw_step)
        history_lines.append(f"<step_{step.step_number}>")
        history_lines.append(f"Next Goal: {step.action.reason}")
        history_lines.append(f"Action: {step.action.action_type}")
        if step.result is None:
            history_lines.append("Action Result: pending")
        else:
            outcome = step.result.error or step.result.extracted_content or "completed"
            history_lines.append(f"Action Result: {outcome}")
        history_lines.append(f"</step_{step.step_number}>")
    return "\n".join(history_lines)
