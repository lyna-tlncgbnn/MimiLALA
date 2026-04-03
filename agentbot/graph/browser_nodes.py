"""Browser subgraph nodes for browser-specialized execution."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime
from typing import Any
from uuid import uuid4

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from agentbot.browser.actions import capture_action_screenshot, execute_browser_actions
from agentbot.browser.dom_service import capture_page_state, summarize_state_for_output
from agentbot.browser.loop_detection import compute_action_hash, compute_page_fingerprint, summarize_loop_signal
from agentbot.browser.session import close_browser_session, get_runtime_session, start_browser_session
from agentbot.browser.views import (
    BrowserAction,
    BrowserElementBounds,
    BrowserInteractiveElement,
    BrowserPageInfo,
    BrowserActionSequenceResult,
    BrowserSemanticGroup,
    BrowserStateSummary,
    BrowserTabInfo,
)
from agentbot.config.settings import Settings
from agentbot.graph.state import AgentGraphState
from agentbot.prompts.browser_subgraph import browser_done_action, build_browser_planner_prompt
from agentbot.storage.common import AGENTBOT_META_KEY

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
    "webpage",
    "website",
    "open url",
    "visit",
    "click",
    "type",
    "search",
)
DEFAULT_BROWSER_MAX_ACTIONS_PER_STEP = 3


def detect_browser_intent(state: AgentGraphState) -> dict[str, Any]:
    latest_user_text = _latest_user_text(state.get("messages", []))
    browser_task = _extract_browser_task(latest_user_text)
    if browser_task is None:
        return {
            "browser_task": None,
            "browser_intent_reason": None,
            "browser_status": None,
            "browser_events": [],
        }

    reason = "explicit browser keyword" if _contains_browser_keyword(latest_user_text) else "detected URL"
    return {
        "browser_task": browser_task,
        "browser_intent_reason": reason,
        "browser_status": "pending",
        "browser_events": [],
    }


def browser_prepare(state: AgentGraphState) -> dict[str, Any]:
    browser_task = state.get("browser_task") or "Open a web page"
    initial_url = _extract_url(browser_task) or "about:blank"
    settings = Settings.from_file()
    headless = True if settings.browser is None else settings.browser.headless
    max_actions = 12 if settings.browser is None else settings.browser.max_actions
    max_actions_per_step = (
        DEFAULT_BROWSER_MAX_ACTIONS_PER_STEP
        if settings.browser is None
        else settings.browser.max_actions_per_step
    )
    session = start_browser_session(
        initial_url=initial_url,
        title=_title_from_url(initial_url),
        mode="system" if settings.browser is None else settings.browser.mode,
        headless=headless,
        viewport_width=1280 if settings.browser is None else settings.browser.viewport_width,
        viewport_height=720 if settings.browser is None else settings.browser.viewport_height,
        window_width=1440 if settings.browser is None else settings.browser.window_width,
        window_height=900 if settings.browser is None else settings.browser.window_height,
        no_viewport=False if settings.browser is None else settings.browser.no_viewport,
        start_maximized=False if settings.browser is None else settings.browser.start_maximized,
        executable_path=None if settings.browser is None else settings.browser.executable_path,
        user_data_dir=None if settings.browser is None else settings.browser.user_data_dir,
        profile_directory=None if settings.browser is None else settings.browser.profile_directory,
        temp_profiles_dir=None if settings.browser is None else settings.browser.temp_profiles_dir,
        copy_local_profile=True if settings.browser is None else settings.browser.copy_local_profile,
        artifacts_dir=None if settings.browser is None else settings.browser.artifacts_dir,
        downloads_dir=None if settings.browser is None else settings.browser.downloads_dir,
        channel=None if settings.browser is None else settings.browser.channel,
    )
    timestamp = _now_iso()
    root_key = "browser_root"

    return {
        "browser_session_id": session.session_id,
        "browser_current_url": session.current_url,
        "browser_status": "running",
        "browser_parent_step_key": root_key,
        "browser_action_history": [],
        "browser_action_count": 0,
        "browser_max_actions": max_actions,
        "browser_max_actions_per_step": max_actions_per_step,
        "browser_pending_action": None,
        "browser_pending_actions": None,
        "browser_last_action_result": None,
        "browser_last_action_results": None,
        "browser_state_summary": None,
        "browser_page_fingerprint": None,
        "browser_stagnant_count": 0,
        "browser_loop_signal": None,
        "browser_requires_approval": False,
        "browser_approval_reason": None,
        "browser_failure_reason": None,
        "browser_failure_step": None,
        "browser_evaluation_previous_goal": None,
        "browser_memory": None,
        "browser_next_goal": None,
        "browser_progress_signal": None,
        "browser_consecutive_failures": 0,
        "browser_plan": None,
        "browser_current_plan_item": None,
        "browser_plan_generation_step": None,
        "browser_events": [
            {
                "event": "step_started",
                "step_key": root_key,
                "step_type": "browser_task",
                "title": "进入浏览器任务",
                "status": "running",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": browser_task,
            },
            {
                "event": "step_started",
                "step_key": "browser_prepare",
                "parent_step_key": root_key,
                "step_type": "browser_prepare",
                "title": "初始化浏览器会话",
                "status": "running",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": f"准备处理任务：{browser_task}",
            },
            {
                "event": "step_completed",
                "step_key": "browser_prepare",
                "step_type": "browser_prepare",
                "title": "初始化浏览器会话",
                "status": "completed",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": f"创建会话 {session.session_id}",
                "output": {
                    "session_id": session.session_id,
                    "initial_url": session.current_url,
                    "title": session.title,
                    "mode": session.mode,
                    "headless": session.headless,
                    "viewport_width": session.viewport_width,
                    "viewport_height": session.viewport_height,
                    "window_width": session.window_width,
                    "window_height": session.window_height,
                    "no_viewport": session.no_viewport,
                    "start_maximized": session.start_maximized,
                    "channel": session.channel,
                    "executable_path": session.executable_path,
                    "user_data_dir": session.user_data_dir,
                    "profile_directory": session.profile_directory,
                    "temp_profile_dir": session.temp_profile_dir,
                    "cdp_url": session.cdp_url,
                    "artifacts_dir": session.artifacts_dir,
                    "downloads_dir": session.downloads_dir,
                },
            },
        ],
    }


def browser_prepare_safe(state: AgentGraphState) -> dict[str, Any]:
    try:
        return browser_prepare(state)
    except Exception as exc:
        return _browser_step_failure(
            state,
            step_key="browser_prepare",
            step_type="browser_prepare",
            title="Initialize browser session",
            exc=exc,
            include_root_start=True,
            update_state={"browser_parent_step_key": state.get("browser_parent_step_key") or "browser_root"},
        )


def browser_observe(state: AgentGraphState) -> dict[str, Any]:
    session_id = state.get("browser_session_id")
    if not session_id:
        raise RuntimeError("Browser session was not initialized before browser_observe.")

    runtime = get_runtime_session(session_id)
    summary, screenshot_path = capture_page_state(runtime)
    timestamp = _now_iso()
    summary_output = summarize_state_for_output(summary, screenshot_path)
    new_fingerprint = summary.observation_fingerprint or compute_page_fingerprint(
        url=summary.url,
        dom_summary=summary.dom_summary,
        element_count=len(summary.interactive_elements),
    )
    previous_fingerprint = state.get("browser_page_fingerprint")
    stagnant_count = int(state.get("browser_stagnant_count") or 0)
    if previous_fingerprint and previous_fingerprint == new_fingerprint:
        stagnant_count += 1
    else:
        stagnant_count = 0
    loop_signal = summarize_loop_signal(
        repeated_action_count=_recent_repeated_action_count(state),
        stagnant_count=stagnant_count,
    )

    return {
        "browser_current_url": summary.url,
        "browser_summary": summary.dom_summary,
        "browser_state_summary": summary_output,
        "browser_page_fingerprint": new_fingerprint,
        "browser_stagnant_count": stagnant_count,
        "browser_loop_signal": loop_signal,
        "browser_events": [
            {
                "event": "step_started",
                "step_key": "browser_observe",
                "parent_step_key": state.get("browser_parent_step_key"),
                "step_type": "browser_observe",
                "title": "观察页面状态",
                "status": "running",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": f"读取页面 {summary.url}",
            },
            {
                "event": "step_completed",
                "step_key": "browser_observe",
                "step_type": "browser_observe",
                "title": "观察页面状态",
                "status": "completed",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": summary.dom_summary if not loop_signal else f"{summary.dom_summary}\n\nLoop signal: {loop_signal}",
                "output": summary_output,
            },
        ],
    }


def browser_observe_safe(state: AgentGraphState) -> dict[str, Any]:
    try:
        return browser_observe(state)
    except Exception as exc:
        return _browser_step_failure(
            state,
            step_key="browser_observe",
            step_type="browser_observe",
            title="Observe page state",
            exc=exc,
        )


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
    primary_action = actions[0]
    primary_action_payload = action_payloads[0]
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
        "browser_pending_action": primary_action_payload,
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


def browser_decide_safe(state: AgentGraphState, llm: BaseChatModel) -> dict[str, Any]:
    try:
        return browser_decide(state, llm)
    except Exception as exc:
        return _browser_step_failure(
            state,
            step_key="browser_decide",
            step_type="browser_decide",
            title="Plan next browser action",
            exc=exc,
            update_state={
                "browser_pending_action": asdict(browser_done_action(reason="Browser planning failed.")),
                "browser_pending_actions": [asdict(browser_done_action(reason="Browser planning failed."))],
                "browser_next_goal": "Stop and report that browser planning failed.",
            },
        )


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


def browser_act_safe(state: AgentGraphState) -> dict[str, Any]:
    try:
        return browser_act(state)
    except Exception as exc:
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
        return _browser_step_failure(
            state,
            step_key="browser_act",
            step_type="browser_action",
            title=f"Execute action: {failed_result['action_type']}",
            exc=exc,
            update_state={
                "browser_action_history": action_history,
                "browser_last_action_result": failed_result,
                "browser_last_action_results": [failed_result],
            },
        )


def browser_evaluate(state: AgentGraphState) -> dict[str, Any]:
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


def browser_evaluate_safe(state: AgentGraphState) -> dict[str, Any]:
    try:
        return browser_evaluate(state)
    except Exception as exc:
        return _browser_step_failure(
            state,
            step_key="browser_evaluate",
            step_type="browser_evaluate",
            title="Evaluate browser step",
            exc=exc,
        )


def browser_finish(state: AgentGraphState) -> dict[str, Any]:
    current_url = state.get("browser_current_url") or "about:blank"
    browser_summary = state.get("browser_summary") or ""
    action_history = list(state.get("browser_action_history") or [])
    requires_approval = bool(state.get("browser_requires_approval"))
    approval_reason = state.get("browser_approval_reason")
    pending_actions = list(state.get("browser_pending_actions") or [])
    if not pending_actions:
        pending_action = state.get("browser_pending_action") or {}
        if pending_action:
            pending_actions = [pending_action]
    primary_action = pending_actions[0] if pending_actions else {}
    pending_action_type = str(primary_action.get("action_type") or "")
    pending_action_reason = str(primary_action.get("reason") or "").strip()
    page_title = _page_title_from_summary(state.get("browser_state_summary"))
    action_count = int(state.get("browser_action_count") or 0)
    max_actions = int(state.get("browser_max_actions") or 12)
    loop_signal = str(state.get("browser_loop_signal") or "").strip()
    failure_reason = str(state.get("browser_failure_reason") or "").strip()
    failure_step = str(state.get("browser_failure_step") or "").strip()
    last_action_result = state.get("browser_last_action_result") or {}
    last_action_success = bool(last_action_result.get("success", True))

    last_action_summary = ""
    for item in reversed(action_history):
        summary_text = str(item.get("summary_text") or "").strip()
        if summary_text:
            last_action_summary = summary_text
            break

    completion_status, finish_reason = _assess_browser_completion(
        requires_approval=requires_approval,
        pending_action_type=pending_action_type,
        pending_action_reason=pending_action_reason,
        action_count=action_count,
        max_actions=max_actions,
        loop_signal=loop_signal,
        failure_reason=failure_reason,
        last_action_success=last_action_success,
    )

    if requires_approval:
        browser_result = f"????????????????????? {page_title or current_url}?"
    elif completion_status == "failed":
        browser_result = f"??????????????? {page_title or current_url}?"
    elif completion_status == "incomplete":
        browser_result = f"?????????????????????? {page_title or current_url}?"
    else:
        browser_result = f"?????????????? {page_title or current_url}?"

    if finish_reason:
        browser_result += f"\n\n?????{finish_reason}"
    if failure_step:
        browser_result += f"\n\n?????{failure_step}"
    if last_action_summary:
        browser_result += f"\n\n?????{last_action_summary}"
    else:
        browser_result += f"\n\n?????{current_url}"
    if loop_signal and requires_approval:
        browser_result += f"\n\n???????{loop_signal}"
    if requires_approval and approval_reason:
        browser_result += f"\n\n??????\n\n???{approval_reason}"
        if pending_actions:
            browser_result += f"\n???{json.dumps(pending_actions, ensure_ascii=False)}"

    timestamp = _now_iso()
    final_message_id = f"msg_{uuid4().hex}"
    final_message = AIMessage(
        content=browser_result,
        additional_kwargs={
            AGENTBOT_META_KEY: {
                "message_id": final_message_id,
                "timestamp": timestamp,
            }
        },
    )
    session_id = state.get("browser_session_id")
    settings = Settings.from_file()
    close_on_finish = True if settings.browser is None else settings.browser.close_on_finish
    if session_id and close_on_finish:
        close_browser_session(session_id)

    root_step_status = "paused" if requires_approval else ("completed" if completion_status == "completed" else "failed")
    root_summary_text = (
        "???????????"
        if requires_approval
        else (
            "???????"
            if completion_status == "completed"
            else ("???????" if completion_status == "failed" else "????????")
        )
    )

    return {
        "browser_status": completion_status,
        "browser_result": browser_result,
        "messages": [final_message],
        "browser_events": [
            {
                "event": "step_started",
                "step_key": "browser_finish",
                "parent_step_key": state.get("browser_parent_step_key"),
                "step_type": "browser_finish",
                "title": "Summarize browser result",
                "status": "running",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": "Finalize the browser subgraph output.",
            },
            {
                "event": "step_completed",
                "step_key": "browser_finish",
                "step_type": "browser_finish",
                "title": "Summarize browser result",
                "status": "completed",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": browser_result,
                "output": {
                    "browser_result": browser_result,
                    "browser_status": completion_status,
                    "finish_reason": finish_reason,
                    "failure_reason": failure_reason or None,
                    "failure_step": failure_step or None,
                    "page_title": page_title,
                    "current_url": current_url,
                    "browser_summary": browser_summary,
                    "action_history": action_history,
                    "pending_actions": pending_actions,
                },
            },
            {
                "event": "step_completed",
                "step_key": state.get("browser_parent_step_key") or "browser_root",
                "step_type": "browser_task",
                "title": "???????",
                "status": root_step_status,
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": root_summary_text,
                "output": {
                    "browser_result": browser_result,
                    "browser_status": completion_status,
                    "finish_reason": finish_reason,
                    "failure_reason": failure_reason or None,
                    "failure_step": failure_step or None,
                    "requires_approval": requires_approval,
                    "approval_reason": approval_reason,
                    "pending_actions": pending_actions,
                },
            },
        ],
    }


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
) -> tuple[str, str | None]:
    if requires_approval:
        return "approval_required", None
    if failure_reason:
        return "failed", failure_reason
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


def _browser_step_failure(
    state: AgentGraphState,
    *,
    step_key: str,
    step_type: str,
    title: str,
    exc: Exception,
    include_root_start: bool = False,
    update_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    timestamp = _now_iso()
    reason = _friendly_browser_error(exc)
    root_key = str(state.get("browser_parent_step_key") or "browser_root")
    events: list[dict[str, Any]] = []

    if include_root_start:
        events.append(
            {
                "event": "step_started",
                "step_key": root_key,
                "step_type": "browser_task",
                "title": "进入浏览器任务",
                "status": "running",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": str(state.get("browser_task") or "Browser task"),
            }
        )

    events.append(
        {
            "event": "step_started",
            "step_key": step_key,
            "parent_step_key": root_key,
            "step_type": step_type,
            "title": title,
            "status": "running",
            "display_mode": "timeline",
            "timestamp": timestamp,
            "summary_text": title,
        }
    )
    events.append(
        {
            "event": "step_completed",
            "step_key": step_key,
            "step_type": step_type,
            "title": title,
            "status": "failed",
            "display_mode": "timeline",
            "timestamp": timestamp,
            "summary_text": reason,
            "output": {"error": str(exc), "friendly_error": reason},
        }
    )

    payload = {
        "browser_status": "failed",
        "browser_failure_reason": reason,
        "browser_failure_step": step_type,
        "browser_evaluation_previous_goal": f"{title} could not be completed. Verdict: Failure",
        "browser_memory": f"Browser step failure at {step_type}: {reason}",
        "browser_next_goal": "Stop the browser task and report the failure cleanly.",
        "browser_progress_signal": "The browser loop should stop because the latest step failed.",
        "browser_consecutive_failures": int(state.get("browser_consecutive_failures") or 0) + 1,
        "browser_events": events,
    }
    if update_state:
        payload.update(update_state)
    return payload


def _friendly_browser_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()
    if 'target page, context or browser has been closed' in lowered or 'has been closed' in lowered:
        return 'The browser window, page, or browser context was closed during execution.'
    if 'browser session not found' in lowered:
        return 'The browser session is no longer available.'
    if 'not visible' in lowered:
        return 'The target element is no longer visible.'
    if 'not attached' in lowered:
        return 'The target element is no longer attached to the page.'
    if 'page changed since observation' in lowered:
        return 'The page changed after observation; the agent needs a fresh observation before acting.'
    if 'timeout' in lowered:
        return f'Browser step timed out: {message}'
    return message


def _build_browser_progress_signal(
    *,
    action_type: str,
    action_reason: str,
    action_success: bool,
    action_output: dict[str, Any],
    loop_signal: str,
) -> str:
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
        return BrowserAction(
            action_type="scroll",
            reason=str(params.get("reason") or ""),
            direction=_optional_str(params.get("direction")),
            amount=_optional_int(params.get("amount")),
        )
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
                        actions=[
                            BrowserAction(
                                action_type="type",
                                reason="Fallback matched first visible input-like element.",
                                element_index=element.index,
                                text=input_text,
                            )
                        ],
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


def _sensitive_action_reason_for_sequence(
    actions: list[BrowserAction],
    summary: BrowserStateSummary | None,
) -> tuple[str | None, int | None]:
    for index, action in enumerate(actions):
        reason = _sensitive_action_reason(action, summary)
        if reason:
            return reason, index
    return None, None


def _sensitive_action_reason(action: BrowserAction, summary: BrowserStateSummary | None) -> str | None:
    action_reason = (action.reason or "").lower()
    sensitive_words = [
        "submit",
        "send",
        "confirm",
        "delete",
        "remove",
        "pay",
        "purchase",
        "checkout",
        "login",
        "log in",
        "sign in",
        "sign up",
        "register",
        "注册",
        "提交",
        "发送",
        "确认",
        "删除",
        "支付",
        "登录",
    ]
    safe_click_tags = {"input", "textarea", "select"}
    safe_click_kinds = {"input", "textarea", "select"}

    if action.action_type == "type" and summary is not None and action.element_index is not None:
        for element in summary.interactive_elements:
            if element.index != action.element_index:
                continue
            sensitive_markers = [
                element.input_type.lower(),
                element.name.lower(),
                element.placeholder.lower(),
                element.text.lower(),
                element.aria_label.lower(),
                element.ax_name.lower(),
            ]
            if any(marker in {"password", "passwd"} for marker in sensitive_markers if marker):
                return "Password-like input requires approval."

    if action.action_type == "click" and summary is not None and action.element_index is not None:
        for element in summary.interactive_elements:
            if element.index != action.element_index:
                continue

            if element.tag in safe_click_tags or element.kind in safe_click_kinds:
                return None

            primary_label = " ".join(
                part
                for part in [
                    element.text,
                    element.aria_label,
                    element.ax_name,
                    element.placeholder,
                    element.name,
                    element.title,
                ]
                if part
            ).strip().lower()
            href = (element.href or "").strip().lower()
            role_signal = " ".join(
                part for part in [element.role, element.ax_role, element.tag, element.kind] if part
            ).lower()

            is_sensitive_control = any(word in primary_label or word in href for word in sensitive_words)
            looks_like_action_control = any(
                marker in role_signal for marker in ["button", "link", "menuitem", "tab", "control"]
            )

            if is_sensitive_control and looks_like_action_control:
                return f"Sensitive button or link requires approval: {primary_label[:80] or href[:80] or 'unnamed element'}."

    if action.action_type in {"click", "type"} and any(word in action_reason for word in sensitive_words):
        if any(
            safe_phrase in action_reason
            for safe_phrase in [
                "activate",
                "focus",
                "open input",
                "departure city",
                "出发城市",
                "输入框",
            ]
        ):
            return None
        return "The planned browser action looks sensitive and requires approval."

    return None

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


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
