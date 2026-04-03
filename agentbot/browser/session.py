"""Playwright-backed browser session helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from agentbot.storage.paths import workspace_root


@dataclass(slots=True)
class BrowserSessionState:
    session_id: str
    current_url: str
    title: str


@dataclass(slots=True)
class BrowserRuntimeSession:
    session_id: str
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page


_SESSION_REGISTRY: dict[str, BrowserRuntimeSession] = {}


def browser_output_dir() -> Path:
    path = workspace_root() / "browser_artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def start_browser_session(*, initial_url: str, title: str, headless: bool = True) -> BrowserSessionState:
    session_id = f"browser_session_{uuid4().hex}"
    runtime = _create_runtime_session(session_id=session_id, initial_url=initial_url, headless=headless)
    _SESSION_REGISTRY[session_id] = runtime
    return BrowserSessionState(
        session_id=session_id,
        current_url=runtime.page.url or initial_url,
        title=runtime.page.title() or title,
    )


def get_runtime_session(session_id: str) -> BrowserRuntimeSession:
    runtime = _SESSION_REGISTRY.get(session_id)
    if runtime is None:
        raise ValueError(f"Browser session not found: {session_id}")
    return runtime


def close_browser_session(session_id: str) -> None:
    runtime = _SESSION_REGISTRY.pop(session_id, None)
    if runtime is None:
        return
    try:
        runtime.context.close()
    finally:
        try:
            runtime.browser.close()
        finally:
            runtime.playwright.stop()


def _create_runtime_session(*, session_id: str, initial_url: str, headless: bool) -> BrowserRuntimeSession:
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    if initial_url and initial_url != "about:blank":
        page.goto(initial_url, wait_until="domcontentloaded", timeout=30000)
    else:
        page.goto("about:blank")
    return BrowserRuntimeSession(
        session_id=session_id,
        playwright=playwright,
        browser=browser,
        context=context,
        page=page,
    )
