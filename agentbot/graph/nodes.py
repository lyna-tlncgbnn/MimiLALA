"""Graph nodes for the current minimal agent."""

from __future__ import annotations

from datetime import datetime

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import ToolNode

from agentbot.prompts.system import get_system_prompt
from agentbot.graph.state import MessagesState
from agentbot.storage.common import AGENTBOT_META_KEY, new_prefixed_id


def chatbot(state: MessagesState, llm: BaseChatModel):
    """Run the real chat model against the current message list."""
    try:
        response = llm.invoke(state["messages"])
    except Exception as exc:
        raise RuntimeError(f"Model execution failed: {exc}") from exc
    if not isinstance(response, AIMessage):
        raise TypeError(f"Expected AIMessage from chat model, got {type(response).__name__}")
    return {"messages": [response]}


def execute_tools(state: MessagesState, tool_node: ToolNode):
    """Run the tool node and let handled tool errors flow back to the model."""
    return tool_node.invoke(state)


def browser_summary(state: MessagesState, llm: BaseChatModel):
    """Summarize the browser subgraph result in the main graph voice."""
    prompt = _build_browser_summary_prompt(state)
    try:
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        get_system_prompt()
                        + " You are now summarizing the outcome of a browser-specialist subgraph for the user."
                    )
                ),
                HumanMessage(content=prompt),
            ]
        )
        if not isinstance(response, AIMessage):
            raise TypeError(f"Expected AIMessage from chat model, got {type(response).__name__}")
        return {"messages": [_ensure_message_metadata(response)]}
    except Exception:
        return {"messages": [_fallback_browser_summary_message(state)]}


def _build_browser_summary_prompt(state: MessagesState) -> str:
    browser_task = str(state.get("browser_task") or "").strip()
    browser_status = str(state.get("browser_status") or "unknown").strip()
    browser_result = str(state.get("browser_result") or "").strip()
    browser_failure_reason = str(state.get("browser_failure_reason") or "").strip()
    browser_failure_step = str(state.get("browser_failure_step") or "").strip()
    browser_evaluation_previous_goal = str(state.get("browser_evaluation_previous_goal") or "").strip()
    browser_memory = str(state.get("browser_memory") or "").strip()
    browser_next_goal = str(state.get("browser_next_goal") or "").strip()
    browser_progress_signal = str(state.get("browser_progress_signal") or "").strip()
    browser_plan = list(state.get("browser_plan") or [])
    browser_current_plan_item = state.get("browser_current_plan_item")
    current_url = str(state.get("browser_current_url") or "").strip()
    action_history = list(state.get("browser_action_history") or [])
    recent_actions = action_history[-5:]

    return (
        "Summarize the browser task result for the user in concise Chinese.\n\n"
        "Requirements:\n"
        "- Explain what was attempted.\n"
        "- State clearly whether the task completed, failed, or is still incomplete.\n"
        "- If it failed or stopped, explain where it got stuck.\n"
        "- If helpful, suggest one next step.\n"
        "- Do not mention internal graph/node/checkpoint terminology.\n"
        "- Do not claim success unless the browser result clearly shows completion.\n\n"
        f"User browser task:\n{browser_task or '(missing)'}\n\n"
        f"Browser status:\n{browser_status}\n\n"
        f"Current URL:\n{current_url or '(unknown)'}\n\n"
        f"Browser result:\n{browser_result or '(missing)'}\n\n"
        f"Failure reason:\n{browser_failure_reason or '(none)'}\n\n"
        f"Failure step:\n{browser_failure_step or '(none)'}\n\n"
        f"Evaluation of previous goal:\n{browser_evaluation_previous_goal or '(none)'}\n\n"
        f"Browser memory:\n{browser_memory or '(none)'}\n\n"
        f"Next goal before stop:\n{browser_next_goal or '(none)'}\n\n"
        f"Progress signal:\n{browser_progress_signal or '(none)'}\n\n"
        f"Browser plan:\n{browser_plan!r}\n\n"
        f"Current plan item:\n{browser_current_plan_item!r}\n\n"
        f"Recent browser actions:\n{recent_actions!r}\n"
    )


def _fallback_browser_summary_message(state: MessagesState) -> AIMessage:
    browser_task = str(state.get("browser_task") or "浏览器任务").strip()
    browser_status = str(state.get("browser_status") or "unknown").strip()
    browser_result = str(state.get("browser_result") or "").strip()
    browser_failure_reason = str(state.get("browser_failure_reason") or "").strip()
    browser_failure_step = str(state.get("browser_failure_step") or "").strip()

    if browser_status == "completed":
        content = f"我已经完成浏览器任务“{browser_task}”。\n\n{browser_result}"
    elif browser_status == "approval_required":
        content = f"浏览器任务“{browser_task}”已暂停，当前需要人工确认后才能继续。\n\n{browser_result}"
    elif browser_status == "failed":
        content = f"我尝试执行浏览器任务“{browser_task}”，但执行失败了。"
        if browser_failure_reason:
            content += f"\n\n原因：{browser_failure_reason}"
        if browser_failure_step:
            content += f"\n卡住位置：{browser_failure_step}"
        if browser_result:
            content += f"\n\n{browser_result}"
        content += "\n\n如果你愿意，我可以在恢复浏览器后重新尝试。"
    else:
        content = f"我尝试执行浏览器任务“{browser_task}”，但目前还没有确认任务完成。\n\n{browser_result or '浏览器任务已停止。'}"

    return AIMessage(
        content=content,
        additional_kwargs={
            AGENTBOT_META_KEY: {
                "message_id": new_prefixed_id("msg"),
                "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
        },
    )


def _ensure_message_metadata(message: AIMessage) -> AIMessage:
    metadata = dict(getattr(message, "additional_kwargs", {}).get(AGENTBOT_META_KEY) or {})
    if metadata.get("message_id") and metadata.get("timestamp"):
        return message
    enriched_kwargs = dict(getattr(message, "additional_kwargs", {}))
    enriched_kwargs[AGENTBOT_META_KEY] = {
        "message_id": str(metadata.get("message_id") or new_prefixed_id("msg")),
        "timestamp": str(metadata.get("timestamp") or datetime.now().astimezone().isoformat(timespec="seconds")),
    }
    return AIMessage(content=message.content, additional_kwargs=enriched_kwargs)
