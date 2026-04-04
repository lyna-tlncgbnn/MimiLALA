"""Browser subgraph nodes for browser-specialized execution."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage

from agentbot.browser.dom_service import capture_page_state, summarize_state_for_output
from agentbot.browser.loop_detection import compute_page_fingerprint, summarize_loop_signal
from agentbot.browser.session import close_browser_session, get_runtime_session, start_browser_session
from agentbot.config.settings import Settings
from agentbot.graph.browser_nodes_act import browser_act as _browser_act
from agentbot.graph.browser_nodes_act import build_failed_action_result
from agentbot.graph.browser_nodes_common import (
    DEFAULT_BROWSER_MAX_ACTIONS_PER_STEP,
    _assess_browser_completion,
    _contains_browser_keyword,
    _extract_browser_task,
    _extract_url,
    _friendly_browser_error,
    _latest_user_text,
    _now_iso,
    _page_title_from_summary,
    _recent_repeated_action_count,
    _title_from_url,
)
from agentbot.graph.browser_nodes_decide import browser_decide as _browser_decide
from agentbot.graph.browser_nodes_evaluate import browser_evaluate as _browser_evaluate
from agentbot.graph.state import AgentGraphState
from agentbot.storage.common import AGENTBOT_META_KEY


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
        download_start_timeout_seconds=4.0 if settings.browser is None else settings.browser.download_start_timeout_seconds,
        download_complete_timeout_seconds=30.0 if settings.browser is None else settings.browser.download_complete_timeout_seconds,
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
                    "download_start_timeout_seconds": 4.0 if settings.browser is None else settings.browser.download_start_timeout_seconds,
                    "download_complete_timeout_seconds": 30.0 if settings.browser is None else settings.browser.download_complete_timeout_seconds,
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


def browser_decide_safe(state: AgentGraphState, llm: BaseChatModel) -> dict[str, Any]:
    try:
        return _browser_decide(state, llm)
    except Exception as exc:
        return _browser_step_failure(
            state,
            step_key="browser_decide",
            step_type="browser_decide",
            title="Plan next browser action",
            exc=exc,
            update_state={
                "browser_pending_action": {"action_type": "done", "reason": "Browser planning failed."},
                "browser_pending_actions": [{"action_type": "done", "reason": "Browser planning failed."}],
                "browser_next_goal": "Stop and report that browser planning failed.",
            },
        )


def browser_act_safe(state: AgentGraphState) -> dict[str, Any]:
    try:
        return _browser_act(state)
    except Exception as exc:
        action_history, failed_result = build_failed_action_result(state, exc)
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


def browser_evaluate_safe(state: AgentGraphState) -> dict[str, Any]:
    try:
        return _browser_evaluate(state)
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
        last_action_output=last_action_result.get("output") if isinstance(last_action_result.get("output"), dict) else {},
    )

    if requires_approval:
        browser_result = f"浏览器任务在 {page_title or current_url} 处等待审批。"
    elif completion_status == "failed":
        browser_result = f"浏览器任务在 {page_title or current_url} 处失败。"
    elif completion_status == "incomplete":
        browser_result = f"浏览器任务在 {page_title or current_url} 处未能完成。"
    else:
        browser_result = f"浏览器任务在 {page_title or current_url} 处完成。"

    if finish_reason:
        browser_result += f"\n\n原因：{finish_reason}"
    if failure_step:
        browser_result += f"\n\n失败步骤：{failure_step}"
    if last_action_summary:
        browser_result += f"\n\n最近一步：{last_action_summary}"
    else:
        browser_result += f"\n\n当前页面：{current_url}"
    if loop_signal and requires_approval:
        browser_result += f"\n\n循环信号：{loop_signal}"
    if requires_approval and approval_reason:
        browser_result += f"\n\n需要审批：\n\n- {approval_reason}"
        if pending_actions:
            browser_result += f"\n待执行动作：{json.dumps(pending_actions, ensure_ascii=False)}"

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
        "浏览器任务已暂停"
        if requires_approval
        else ("浏览器任务已完成" if completion_status == "completed" else ("浏览器任务失败" if completion_status == "failed" else "浏览器任务未完成"))
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
                "title": "浏览器任务",
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
