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

from agentbot.browser.actions import capture_action_screenshot, execute_browser_action
from agentbot.browser.dom_service import capture_page_state, summarize_state_for_output
from agentbot.browser.loop_detection import compute_action_hash, compute_page_fingerprint, summarize_loop_signal
from agentbot.browser.session import close_browser_session, get_runtime_session, start_browser_session
from agentbot.browser.views import (
    BrowserAction,
    BrowserElementBounds,
    BrowserInteractiveElement,
    BrowserPageInfo,
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
    session = start_browser_session(
        initial_url=initial_url,
        title=_title_from_url(initial_url),
        headless=headless,
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
        "browser_max_actions": 4,
        "browser_pending_action": None,
        "browser_last_action_result": None,
        "browser_state_summary": None,
        "browser_page_fingerprint": None,
        "browser_stagnant_count": 0,
        "browser_loop_signal": None,
        "browser_requires_approval": False,
        "browser_approval_reason": None,
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
                    "headless": headless,
                },
            },
        ],
    }


def browser_observe(state: AgentGraphState) -> dict[str, Any]:
    session_id = state.get("browser_session_id")
    if not session_id:
        raise RuntimeError("Browser session was not initialized before browser_observe.")

    runtime = get_runtime_session(session_id)
    summary, screenshot_path = capture_page_state(runtime)
    timestamp = _now_iso()
    summary_output = summarize_state_for_output(summary, screenshot_path)
    new_fingerprint = compute_page_fingerprint(
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


def browser_decide(state: AgentGraphState, llm: BaseChatModel) -> dict[str, Any]:
    timestamp = _now_iso()
    browser_task = state.get("browser_task") or ""
    action_history = list(state.get("browser_action_history") or [])
    action_count = int(state.get("browser_action_count") or 0)
    max_actions = int(state.get("browser_max_actions") or 4)
    summary = _summary_from_state(state.get("browser_state_summary"))

    if action_count >= max_actions:
        action = browser_done_action(reason=f"Reached action budget ({max_actions}).")
    elif state.get("browser_loop_signal") and action_count >= 2:
        action = browser_done_action(reason=str(state.get("browser_loop_signal")))
    else:
        action = _plan_browser_action(
            llm=llm,
            task=browser_task,
            summary=summary,
            action_history=action_history,
            current_url=state.get("browser_current_url"),
        )

    approval_reason = _sensitive_action_reason(action, summary)
    if approval_reason:
        action.approval_required = True
        action.approval_reason = approval_reason

    action_payload = asdict(action)
    return {
        "browser_pending_action": action_payload,
        "browser_requires_approval": bool(approval_reason),
        "browser_approval_reason": approval_reason,
        "browser_status": "approval_required" if approval_reason else state.get("browser_status"),
        "browser_events": [
            {
                "event": "step_started",
                "step_key": "browser_decide",
                "parent_step_key": state.get("browser_parent_step_key"),
                "step_type": "browser_decide",
                "title": "决定下一步动作",
                "status": "running",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": "根据当前页面状态规划下一步浏览器动作",
            },
            {
                "event": "step_completed",
                "step_key": "browser_decide",
                "step_type": "browser_decide",
                "title": "决定下一步动作",
                "status": "completed",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": (
                    f"{_action_summary_text(action)}\n\n需要人工确认：{approval_reason}"
                    if approval_reason
                    else _action_summary_text(action)
                ),
                "output": action_payload,
            },
        ],
    }


def browser_act(state: AgentGraphState) -> dict[str, Any]:
    session_id = state.get("browser_session_id")
    if not session_id:
        raise RuntimeError("Browser session was not initialized before browser_act.")
    action_payload = state.get("browser_pending_action")
    if not isinstance(action_payload, dict):
        raise RuntimeError("browser_act was called without a pending browser action.")

    action = BrowserAction(**action_payload)
    runtime = get_runtime_session(session_id)
    summary = _summary_from_state(state.get("browser_state_summary"))
    timestamp = _now_iso()

    result = execute_browser_action(runtime, action=action, summary=summary)
    screenshot_path = capture_action_screenshot(runtime, suffix=f"action-{int(state.get('browser_action_count') or 0) + 1}")
    output_payload = dict(result.output or {})
    if screenshot_path is not None:
        output_payload["screenshot_path"] = str(screenshot_path)

    action_history = list(state.get("browser_action_history") or [])
    action_history.append(
        {
            "action_type": action.action_type,
            "action_hash": compute_action_hash(action_payload),
            "reason": action.reason,
            "summary_text": result.summary_text,
            "output": output_payload,
        }
    )

    return {
        "browser_action_history": action_history,
        "browser_last_action_result": {
            "action_type": result.action_type,
            "success": result.success,
            "summary_text": result.summary_text,
            "output": output_payload,
        },
        "browser_events": [
            {
                "event": "step_started",
                "step_key": "browser_act",
                "parent_step_key": state.get("browser_parent_step_key"),
                "step_type": "browser_action",
                "title": f"执行动作: {action.action_type}",
                "status": "running",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": _action_summary_text(action),
                "input": action_payload,
            },
            {
                "event": "step_completed",
                "step_key": "browser_act",
                "step_type": "browser_action",
                "title": f"执行动作: {action.action_type}",
                "status": "completed",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": result.summary_text,
                "output": output_payload,
            },
        ],
    }


def browser_evaluate(state: AgentGraphState) -> dict[str, Any]:
    timestamp = _now_iso()
    action_payload = state.get("browser_pending_action") or {}
    action_type = str(action_payload.get("action_type") or "")
    action_count = int(state.get("browser_action_count") or 0)
    next_count = action_count + (0 if action_type == "done" else 1)
    max_actions = int(state.get("browser_max_actions") or 4)
    if action_type == "done":
        summary_text = "浏览器子图决定结束并输出结果"
    elif next_count >= max_actions:
        summary_text = f"已执行 {next_count} 步动作，达到当前预算上限"
    else:
        summary_text = f"浏览器动作已完成，准备重新观察页面（已执行 {next_count}/{max_actions}）"
    loop_signal = summarize_loop_signal(
        repeated_action_count=_recent_repeated_action_count(
            {
                "browser_action_history": state.get("browser_action_history"),
                "browser_pending_action": state.get("browser_pending_action"),
            }
        ),
        stagnant_count=int(state.get("browser_stagnant_count") or 0),
    ) or state.get("browser_loop_signal")

    return {
        "browser_action_count": next_count,
        "browser_loop_signal": loop_signal,
        "browser_events": [
            {
                "event": "step_started",
                "step_key": "browser_evaluate",
                "parent_step_key": state.get("browser_parent_step_key"),
                "step_type": "browser_evaluate",
                "title": "评估动作结果",
                "status": "running",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": "评估是否继续浏览器交互",
            },
            {
                "event": "step_completed",
                "step_key": "browser_evaluate",
                "step_type": "browser_evaluate",
                "title": "评估动作结果",
                "status": "completed",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": summary_text,
                "output": {
                    "action_count": next_count,
                    "max_actions": max_actions,
                    "pending_action_type": action_type,
                    "loop_signal": loop_signal,
                },
            },
        ],
    }


def browser_finish(state: AgentGraphState) -> dict[str, Any]:
    current_url = state.get("browser_current_url") or "about:blank"
    browser_summary = state.get("browser_summary") or ""
    action_history = list(state.get("browser_action_history") or [])
    requires_approval = bool(state.get("browser_requires_approval"))
    approval_reason = state.get("browser_approval_reason")
    pending_action = state.get("browser_pending_action") or {}
    page_title = _page_title_from_summary(state.get("browser_state_summary"))
    last_action_summary = ""
    for item in reversed(action_history):
        summary_text = str(item.get("summary_text") or "").strip()
        if summary_text:
            last_action_summary = summary_text
            break
    if requires_approval:
        browser_result = f"浏览器任务已暂停，等待人工确认。当前页面为 {page_title or current_url}。"
    else:
        browser_result = f"已完成浏览器任务，当前页面为 {page_title or current_url}。"
        if last_action_summary:
            browser_result += f"\n\n最后一步：{last_action_summary}"
        else:
            browser_result += f"\n\n当前地址：{current_url}"
    if state.get("browser_loop_signal") and requires_approval:
        browser_result += f"\n\n循环检测提示：{state.get('browser_loop_signal')}"
    if requires_approval and approval_reason:
        browser_result += f"\n\n待确认动作：\n- 原因：{approval_reason}"
        if pending_action:
            browser_result += f"\n- 动作：{json.dumps(pending_action, ensure_ascii=False)}"

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
    if session_id:
        close_browser_session(session_id)

    return {
        "browser_status": "approval_required" if requires_approval else "completed",
        "browser_result": browser_result,
        "messages": [final_message],
        "browser_events": [
            {
                "event": "step_started",
                "step_key": "browser_finish",
                "parent_step_key": state.get("browser_parent_step_key"),
                "step_type": "browser_finish",
                "title": "汇总浏览器结果",
                "status": "running",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": "整理浏览器子图输出",
            },
            {
                "event": "step_completed",
                "step_key": "browser_finish",
                "step_type": "browser_finish",
                "title": "汇总浏览器结果",
                "status": "completed",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": browser_result,
                "output": {
                    "browser_result": browser_result,
                    "page_title": page_title,
                    "current_url": current_url,
                    "browser_summary": browser_summary,
                    "action_history": action_history,
                },
            },
            {
                "event": "step_completed",
                "step_key": state.get("browser_parent_step_key") or "browser_root",
                "step_type": "browser_task",
                "title": "进入浏览器任务",
                "status": "paused" if requires_approval else "completed",
                "display_mode": "timeline",
                "timestamp": timestamp,
                "summary_text": "浏览器任务等待人工确认" if requires_approval else "浏览器任务完成",
                "output": {
                    "browser_result": browser_result,
                    "requires_approval": requires_approval,
                    "approval_reason": approval_reason,
                },
            },
        ],
    }


def _plan_browser_action(
    *,
    llm: BaseChatModel,
    task: str,
    summary: BrowserStateSummary | None,
    action_history: list[dict[str, Any]],
    current_url: str | None,
) -> BrowserAction:
    prompt = build_browser_planner_prompt(
        task=task,
        summary=summary,
        action_history=action_history,
        current_url=current_url,
    )
    try:
        response = llm.invoke(
            [
                SystemMessage(content="You are a precise browser planner that returns JSON only."),
                HumanMessage(content=prompt),
            ]
        )
    except Exception:
        return _fallback_browser_action(task=task, summary=summary, action_history=action_history)

    raw_text = _message_text(response)
    try:
        payload = _parse_json_object(raw_text)
        return BrowserAction(
            action_type=str(payload.get("action_type") or "done"),
            reason=str(payload.get("reason") or ""),
            url=_optional_str(payload.get("url")),
            element_index=_optional_int(payload.get("element_index")),
            text=_optional_str(payload.get("text")),
            direction=_optional_str(payload.get("direction")),
            amount=_optional_int(payload.get("amount")),
            tab_id=_optional_str(payload.get("tab_id")),
        )
    except Exception:
        return _fallback_browser_action(task=task, summary=summary, action_history=action_history)


def _fallback_browser_action(
    *,
    task: str,
    summary: BrowserStateSummary | None,
    action_history: list[dict[str, Any]],
) -> BrowserAction:
    lowered = task.lower()
    if summary is None:
        url = _extract_url(task)
        if url:
            return BrowserAction(action_type="navigate", reason="Fallback navigate to detected URL.", url=url)
        return browser_done_action(reason="No browser summary available.")

    if not action_history and ("点击" in task or "click" in lowered):
        for element in summary.interactive_elements:
            if element.text and element.text.lower() in lowered:
                return BrowserAction(action_type="click", reason="Fallback matched visible element text.", element_index=element.index)

    if not action_history and ("输入" in task or "search" in lowered or "搜索" in task):
        text_match = re.search(r"[“\"]([^”\"]+)[”\"]", task)
        input_text = text_match.group(1) if text_match else None
        if input_text:
            for element in summary.interactive_elements:
                if element.kind in {"input", "textarea", "select"}:
                    return BrowserAction(
                        action_type="type",
                        reason="Fallback matched first visible input-like element.",
                        element_index=element.index,
                        text=input_text,
                    )

    return browser_done_action(reason="Fallback chose done.")


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
                    text=str(item.get("text") or ""),
                    href=str(item.get("href") or ""),
                    role=str(item.get("role") or ""),
                    input_type=str(item.get("input_type") or ""),
                    name=str(item.get("name") or ""),
                    placeholder=str(item.get("placeholder") or ""),
                    title=str(item.get("title") or ""),
                    aria_label=str(item.get("aria_label") or ""),
                    enabled=bool(item.get("enabled", True)),
                    visible=bool(item.get("visible", True)),
                    in_viewport=bool(item.get("in_viewport", True)),
                    bounds=BrowserElementBounds(
                        x=float(bounds_payload.get("x") or 0.0),
                        y=float(bounds_payload.get("y") or 0.0),
                        width=float(bounds_payload.get("width") or 0.0),
                        height=float(bounds_payload.get("height") or 0.0),
                    ),
                )
            )
    return BrowserStateSummary(
        url=str(payload.get("url") or "about:blank"),
        title=str(payload.get("title") or "Untitled page"),
        tabs=tabs,
        page_info=page_info,
        dom_summary=str(payload.get("dom_summary") or ""),
        interactive_elements=interactive_elements,
        screenshot_path=_optional_str(payload.get("screenshot_path")),
        browser_errors=[str(item) for item in (payload.get("browser_errors") or [])],
    )


def _action_summary_text(action: BrowserAction) -> str:
    if action.action_type == "done":
        return action.reason or "结束浏览器子图"
    if action.action_type == "navigate":
        return f"准备打开页面 {action.url or '(missing url)'}"
    if action.action_type == "click":
        return f"准备点击元素 [{action.element_index}]"
    if action.action_type == "type":
        return f"准备在元素 [{action.element_index}] 输入内容"
    if action.action_type == "scroll":
        return f"准备向{action.direction or 'down'}滚动 {action.amount or 600} 像素"
    if action.action_type == "wait":
        return f"准备等待 {action.amount or 2} 秒"
    if action.action_type == "go_back":
        return "准备返回上一页"
    if action.action_type == "switch_tab":
        return f"准备切换到标签页 {action.tab_id or 'latest'}"
    return f"准备执行动作 {action.action_type}"


def _sensitive_action_reason(action: BrowserAction, summary: BrowserStateSummary | None) -> str | None:
    action_reason = (action.reason or "").lower()
    generic_sensitive_words = [
        "submit",
        "send",
        "confirm",
        "delete",
        "remove",
        "pay",
        "purchase",
        "checkout",
        "login",
        "sign in",
        "注册",
        "提交",
        "发送",
        "确认",
        "删除",
        "支付",
        "登录",
    ]

    if action.action_type == "type" and summary is not None and action.element_index is not None:
        for element in summary.interactive_elements:
            if element.index != action.element_index:
                continue
            sensitive_markers = [
                element.input_type.lower(),
                element.name.lower(),
                element.placeholder.lower(),
                element.text.lower(),
            ]
            if any(marker in {"password", "passwd"} for marker in sensitive_markers if marker):
                return "即将向密码类输入框写入内容，后续建议接入人工确认。"

    if action.action_type == "click" and summary is not None and action.element_index is not None:
        for element in summary.interactive_elements:
            if element.index != action.element_index:
                continue
            label = " ".join(
                part for part in [element.text, element.placeholder, element.name, element.href] if part
            ).lower()
            if any(word in label for word in generic_sensitive_words):
                return f"即将点击敏感按钮或链接：{label[:80] or 'unnamed element'}。"

    if action.action_type in {"click", "type"} and any(word in action_reason for word in generic_sensitive_words):
        return "模型规划了疑似敏感页面动作，后续建议接入人工确认。"

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
