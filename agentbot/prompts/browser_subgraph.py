"""Prompt helpers for browser subgraph planning."""

from __future__ import annotations

import json

from agentbot.browser.views import BrowserAction, BrowserStateSummary


def build_browser_planner_prompt(
    *,
    task: str,
    summary: BrowserStateSummary | None,
    action_history: list[dict] | None,
    current_url: str | None,
) -> str:
    history = json.dumps(action_history or [], ensure_ascii=False, indent=2)
    if summary is None:
        page_summary = "(no page summary yet)"
    else:
        page_summary = summary.dom_summary

    return (
        "You are the browser planner inside AgentBot.\n"
        "Decide the single next browser action needed to advance the task.\n"
        "Return JSON only. Do not wrap in markdown.\n\n"
        "Allowed action_type values:\n"
        '- "done"\n'
        '- "navigate"\n'
        '- "click"\n'
        '- "type"\n'
        '- "scroll"\n'
        '- "wait"\n'
        '- "go_back"\n'
        '- "switch_tab"\n\n'
        "Rules:\n"
        "- Prefer done when the current page already answers the task.\n"
        "- Use click/type only when the target element is visible in the interactive elements list.\n"
        "- Use element_index from the provided summary.\n"
        "- Use navigate only when you have a concrete URL.\n"
        "- Avoid destructive or account-affecting actions unless they are clearly required.\n"
        "- Keep actions minimal and safe.\n"
        "- If you are unsure, choose done.\n\n"
        "Return this JSON shape:\n"
        '{'
        '"action_type":"done|navigate|click|type|scroll|wait|go_back|switch_tab",'
        '"reason":"short reason",'
        '"url":null,'
        '"element_index":null,'
        '"text":null,'
        '"direction":null,'
        '"amount":null,'
        '"tab_id":null'
        '}\n\n'
        f"Task:\n{task}\n\n"
        f"Current URL:\n{current_url or '(unknown)'}\n\n"
        f"Current page summary:\n{page_summary}\n\n"
        f"Recent browser action history:\n{history}\n"
    )


def browser_done_action(*, reason: str) -> BrowserAction:
    return BrowserAction(action_type="done", reason=reason)
