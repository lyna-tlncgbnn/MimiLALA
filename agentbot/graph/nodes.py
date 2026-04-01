"""Graph nodes for the supervisor-first main chat graph."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.prebuilt import ToolNode

from agentbot.graph.state import AgentGraphState
from agentbot.graph.routes import get_latest_user_text
from agentbot.models.browser import BrowserTaskResult
from agentbot.models.supervisor import SupervisorDecision
from agentbot.prompts.supervisor.loader import load_supervisor_prompt


_URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)


def supervisor(state: AgentGraphState, llm: BaseChatModel):
    """Let the main agent decide whether to respond, use tools, or delegate to browser."""
    structured_llm = llm.with_structured_output(SupervisorDecision)
    decision = structured_llm.invoke(
        [
            SystemMessage(content=load_supervisor_prompt("system_prompt.md")),
            *state["messages"],
            HumanMessage(content=_build_supervisor_context_block(state)),
        ]
    )
    writer = get_stream_writer()
    writer(
        {
            "source": "supervisor",
            "event": "supervisor_decision_made",
            "decision": decision.decision,
            "reason": decision.reason,
            "browser_task": decision.browser_task,
        }
    )
    update: AgentGraphState = {
        "supervisor_decision": decision.model_dump(),
    }
    if decision.decision == "browser":
        update["browser_task_request"] = {
            "task": decision.browser_task,
            "start_url": _extract_start_url(decision.browser_task or ""),
        }
    return update


def respond(state: AgentGraphState):
    """Emit the final user-facing response chosen by the supervisor."""
    decision = SupervisorDecision.model_validate(state.get("supervisor_decision") or {})
    browser_task = state.get("browser_task_result")
    additional_kwargs: dict[str, Any] = {}
    additional_kwargs["response"] = {"text": decision.response or ""}
    additional_kwargs["state"] = {"kind": "final"}
    if decision.decision == "browser":
        additional_kwargs["delegation"] = {
            "target": "browser",
            "status": "completed" if browser_task and browser_task.get("status") == "completed" else "failed",
            "reason": decision.reason,
            "task": decision.browser_task,
        }
    if browser_task:
        additional_kwargs["browser_task"] = browser_task
    return {
        "messages": [
            AIMessage(
                content=decision.response or "",
                additional_kwargs=additional_kwargs,
            )
        ]
    }


def tool_chatbot(state: AgentGraphState, llm: BaseChatModel):
    """Run the tool-enabled main agent after the supervisor selected the tools path."""
    try:
        response = llm.invoke(state["messages"])
    except Exception as exc:
        raise RuntimeError(f"Model execution failed: {exc}") from exc
    if not isinstance(response, AIMessage):
        raise TypeError(f"Expected AIMessage from chat model, got {type(response).__name__}")
    response_text = _extract_message_text(response.content)
    response.additional_kwargs.setdefault("state", {"kind": "tooling" if response.tool_calls else "final"})
    if response_text:
        response.additional_kwargs.setdefault("response", {"text": response_text})
    return {"messages": [response]}


def execute_tools(state: AgentGraphState, tool_node: ToolNode):
    """Run the tool node and let handled tool errors flow back to the model."""
    return tool_node.invoke(state)


def call_browser_subgraph(
    state: AgentGraphState,
    llm: BaseChatModel,
    *,
    llm_config: dict[str, Any] | None = None,
):
    """Run the browser subgraph as a delegated worker and return control to the supervisor."""
    browser_task_request = state.get("browser_task_request") or {}
    task_text = str(browser_task_request.get("task") or get_latest_user_text(state)).strip()

    writer = get_stream_writer()
    writer(
        {
            "source": "browser_subgraph",
            "event": "browser_subgraph_started",
            "task": task_text,
        }
    )

    from agentbot.graph.browser_builder import build_browser_graph

    browser_graph = build_browser_graph(llm)
    final_values: dict[str, Any] | None = None
    planned_actions: dict[int, dict[str, Any]] = {}

    for chunk in browser_graph.stream(
        {
            "task": task_text,
            "start_url": browser_task_request.get("start_url") or _extract_start_url(task_text),
            "llm_config": llm_config,
            "max_steps": 6,
        },
        stream_mode=["updates", "values"],
        version="v2",
    ):
        event_type, payload = _normalize_stream_chunk(chunk)
        if event_type == "updates":
            for event in _browser_events_from_subgraph_updates(payload, planned_actions):
                writer(event)
        elif event_type == "values" and isinstance(payload, dict):
            final_values = payload

    result = BrowserTaskResult(
        status=str((final_values or {}).get("status", "failed")),
        final_response=(final_values or {}).get("final_response"),
        error_message=(final_values or {}).get("error_message"),
        current_url=(final_values or {}).get("current_url"),
        page_title=(final_values or {}).get("page_title"),
        step_count=int((final_values or {}).get("step_count", 0)),
        steps=(final_values or {}).get("steps", []),
    )

    writer(
        {
            "source": "browser_subgraph",
            "event": "browser_subgraph_completed"
            if result.status == "completed"
            else "browser_subgraph_failed",
            "status": result.status,
            "final_response": result.final_response,
            "error_message": result.error_message,
            "current_url": result.current_url,
            "page_title": result.page_title,
            "step_count": result.step_count,
        }
    )

    browser_task_result = {
        **result.model_dump(),
        "task": task_text,
    }
    return {
        "browser_task_result": browser_task_result,
    }


def _extract_start_url(task_text: str) -> str | None:
    match = _URL_PATTERN.search(task_text)
    return match.group(0) if match else None


def _build_supervisor_context_block(state: AgentGraphState) -> str:
    browser_result = state.get("browser_task_result")
    if browser_result:
        return (
            "<supervisor_context>\n"
            "A delegated browser task has already completed in this turn.\n"
            f"Browser task result: {browser_result}\n"
            "If the browser result is sufficient, choose respond and answer the user clearly.\n"
            "</supervisor_context>"
        )
    return (
        "<supervisor_context>\n"
        "Decide the next action for this turn based on the full conversation context.\n"
        "</supervisor_context>"
    )


def _normalize_stream_chunk(chunk: Any) -> tuple[str | None, Any]:
    if isinstance(chunk, tuple) and len(chunk) == 2 and isinstance(chunk[0], str):
        return chunk[0], chunk[1]
    if isinstance(chunk, dict):
        event_type = chunk.get("type")
        if isinstance(event_type, str):
            return event_type, chunk.get("data")
    return None, None


def _browser_events_from_subgraph_updates(
    payload: Any,
    planned_actions: dict[int, dict[str, Any]],
):
    if not isinstance(payload, dict):
        return

    for node_name, node_update in payload.items():
        if not isinstance(node_update, dict):
            continue

        if node_name == "browser_observe":
            yield {
                "source": "browser_subgraph",
                "event": "browser_observed",
                "current_url": node_update.get("current_url"),
                "page_title": node_update.get("page_title"),
            }
        elif node_name == "browser_plan":
            action = node_update.get("last_action") or {}
            steps = node_update.get("steps") or []
            step_number = len(steps) if steps else None
            if step_number is not None:
                planned_actions[step_number] = action
            yield {
                "source": "browser_subgraph",
                "event": "browser_action_planned",
                "step_number": step_number,
                "action": action,
            }
            yield {
                "source": "browser_subgraph",
                "event": "browser_action_started",
                "step_number": step_number,
                "action": action,
            }
        elif node_name == "browser_act":
            step_number = int(node_update.get("step_count", 0))
            yield {
                "source": "browser_subgraph",
                "event": "browser_action_finished",
                "step_number": step_number,
                "action": planned_actions.get(step_number),
                "result": node_update.get("last_action_result"),
                "status": node_update.get("status", "running"),
            }


def _browser_result_text(result: BrowserTaskResult) -> str:
    if result.status == "completed":
        return result.final_response or "Browser task completed."
    if result.final_response:
        return result.final_response
    return result.error_message or "Browser task failed."


def _extract_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                text_chunks.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                text_chunks.append(str(item.get("text", "")))
        return "".join(text_chunks).strip()
    return str(content) if content is not None else ""
