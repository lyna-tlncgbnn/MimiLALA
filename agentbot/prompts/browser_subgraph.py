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
    evaluation_previous_goal: str | None,
    memory: str | None,
    next_goal: str | None,
    progress_signal: str | None,
    consecutive_failures: int | None,
    recovery_nudges: list[str] | None,
    plan_description: str | None,
    max_actions_per_step: int,
) -> str:
    history = json.dumps(action_history or [], ensure_ascii=False, indent=2)
    page_summary = summary.dom_summary if summary is not None else "(no page summary yet)"
    recent_events = summary.recent_events if summary is not None else []
    tabs = summary.tabs if summary is not None else []
    prioritized_hints = summary.prioritized_hints if summary is not None else []
    semantic_groups = summary.semantic_groups if summary is not None else []
    nudges = recovery_nudges or []

    return (
        "You are the browser planner inside AgentBot. "
        "You operate in an iterative browser loop inspired by browser-use, and you must return a browser-use style action list as JSON together with concise browser-agent state.\n\n"
        "<mission>\n"
        "- Accomplish the user's browser task safely and efficiently.\n"
        "- Think in short browser steps: observe, choose one useful action, then let the next observation verify it.\n"
        "- Prefer actions that create clear progress on the current page.\n"
        "</mission>\n\n"
        "<state>\n"
        f"User request:\n{task}\n\n"
        f"Current URL:\n{current_url or '(unknown)'}\n\n"
        f"Open tabs:\n{_render_tabs(tabs)}\n\n"
        f"Recent browser events:\n{_render_recent_events(recent_events)}\n\n"
        f"Evaluation of previous goal:\n{evaluation_previous_goal or '(none yet)'}\n\n"
        f"Planner memory:\n{memory or '(empty)'}\n\n"
        f"Current next goal:\n{next_goal or '(not set yet)'}\n\n"
        f"Progress signal:\n{progress_signal or '(none)'}\n\n"
        f"Consecutive failures:\n{int(consecutive_failures or 0)}\n\n"
        f"Current plan:\n{plan_description or '(no plan yet)'}\n\n"
        f"Recovery nudges:\n{_render_recovery_nudges(nudges)}\n\n"
        f"Prioritized page hints:\n{_render_prioritized_hints(prioritized_hints)}\n\n"
        f"Semantic groups:\n{_render_semantic_groups(semantic_groups)}\n\n"
        f"Current browser state:\n{page_summary}\n\n"
        f"Recent browser action history:\n{history}\n"
        "</state>\n\n"
        "<allowed_actions>\n"
        '- "done": finish because the task is complete, impossible, or unsafe to continue.\n'
        '- "navigate": open a concrete URL in the current tab.\n'
        '- "new_tab_navigate": open a concrete URL in a new tab. Prefer this for research or when preserving the current page matters.\n'
        '- "click": click a visible indexed element from the interactive elements list.\n'
        '- "type": type text into a visible indexed input-like element.\n'
        '- "press_enter": press Enter on the active page or focused control. Use this after typing search terms when submit depends on Enter.\n'
        '- "scroll": scroll up or down.\n'
        '- "wait": wait briefly for page load, suggestions, or async UI changes.\n'
        '- "go_back": go back in browser history.\n'
        '- "switch_tab": switch to an existing tab id.\n'
        "</allowed_actions>\n\n"
        "<rules>\n"
        "- Return JSON only. Do not wrap in markdown.\n"
        f"- Return 1 to {max_actions_per_step} actions in the action list.\n"
        "- The action list must never be empty.\n"
        '- If you choose "done", it must be the only action in the list.\n'
        "- Only use element_index values that are explicitly present in the interactive elements list.\n"
        "- Only click or type into visible indexed elements from the current summary.\n"
        "- Prefer using the current page state over guessing hidden page structure.\n"
        "- If the page already answers the user request, choose done.\n"
        "- If a popup, modal, cookie banner, dialog blocker, or overlay is visible, handle it before doing other work.\n"
        "- If the previous type action likely triggered suggestions or a combobox dropdown, inspect the new elements first. Click the correct suggestion when available.\n"
        "- If typing into search or autocomplete did not submit yet and no better indexed suggestion is visible, use press_enter.\n"
        "- If the page is still loading or a dynamic update is in progress, use wait.\n"
        "- If research is needed on another site, prefer new_tab_navigate instead of losing the current page.\n"
        "- If the user gave explicit step-by-step instructions, follow them closely and do not skip steps.\n"
        "- If the user gave filters or criteria, apply filters before browsing many results.\n"
        "- Do not log in, submit forms, purchase, delete, or confirm sensitive actions unless clearly required.\n"
        "- Break loops: if the same action failed repeatedly or the URL has not meaningfully changed for several steps, choose a different action.\n"
        "- Explicitly judge whether the previous step succeeded, failed, or is still uncertain before choosing the next action.\n"
        "- Update memory with concrete progress, blockers, and what has already been tried.\n"
        "- Use next_goal to describe the immediate browser objective for this step only.\n"
        "- If consecutive failures are increasing, stop repeating exploratory scroll/wait patterns and try a different page area or a more direct control.\n"
        "- If you are unsure and cannot justify a safe next browser action, choose done with a brief reason.\n"
        "- Combine actions only when they form one clear short sequence on the current page.\n"
        "- If typing may reveal suggestions, you may stop after type and let the next observation verify the dropdown before clicking again.\n"
        "- If any earlier action in the sequence would likely change the page or visible state, do not assume later actions will still be valid.\n"
        "</rules>\n\n"
        "<planning>\n"
        "- For simple tasks, you may act directly without plan_update.\n"
        "- For complex browser tasks, you may provide plan_update as a short todo list.\n"
        "- If a plan already exists, you may set current_plan_item to the 0-based item you are working on now.\n"
        "- Only update the plan when needed. Do not rewrite it every step.\n"
        "- Completing all plan items does not by itself prove the user task is complete.\n"
        "</planning>\n\n"
        "<done_rules>\n"
        "- Use done only when the task is actually complete, impossible, unsafe, or the page clearly cannot advance further.\n"
        "- Before done, verify that the visible page state really satisfies the user's request.\n"
        "- Never claim success from memory alone; rely on the current browser state and recent action results.\n"
        "</done_rules>\n\n"
        "Return this JSON shape:\n"
        "{"
        '"evaluation_previous_goal":"one sentence with verdict",'
        '"memory":"1-3 short sentences of browser memory",'
        '"next_goal":"one sentence immediate goal",'
        '"current_plan_item":null,'
        '"plan_update":null,'
        '"action":['
        "{"
        '"action_type":"done|navigate|new_tab_navigate|click|type|press_enter|scroll|wait|go_back|switch_tab",'
        '"reason":"short reason",'
        '"url":null,'
        '"element_index":null,'
        '"text":null,'
        '"direction":null,'
        '"amount":null,'
        '"tab_id":null'
        "}"
        "]"
        "}\n\n"
        "<action_selection_hints>\n"
        "- Use type when entering text into an indexed input.\n"
        "- Use type plus press_enter or type plus click when the current page clearly supports immediate submission.\n"
        "- Use click for visible search buttons, suggestions, close buttons, tabs, links, filters, and dismiss actions.\n"
        "- Use scroll only when the needed element or information is not visible yet.\n"
        "- Use switch_tab only when the needed tab already exists in Open tabs.\n"
        "</action_selection_hints>\n"
    )


def browser_done_action(*, reason: str) -> BrowserAction:
    return BrowserAction(action_type="done", reason=reason)


def _render_recent_events(events: list[str]) -> str:
    if not events:
        return "- none"
    return "\n".join(f"- {event}" for event in events[-6:])


def _render_tabs(tabs: list) -> str:
    if not tabs:
        return "- none"
    return "\n".join(f"- {tab.tab_id}: {tab.title} ({tab.url})" for tab in tabs)


def _render_prioritized_hints(hints: list[str]) -> str:
    if not hints:
        return "- none"
    return "\n".join(f"- {item}" for item in hints[:6])


def _render_semantic_groups(groups: list) -> str:
    if not groups:
        return "- none"
    return "\n".join(f"- {group.label}: {group.element_indexes}" for group in groups[:6])


def _render_recovery_nudges(nudges: list[str]) -> str:
    if not nudges:
        return "- none"
    return "\n".join(f"- {item}" for item in nudges[:6])
