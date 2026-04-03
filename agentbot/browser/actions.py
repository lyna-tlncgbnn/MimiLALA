"""Low-level Playwright browser actions for the browser subgraph."""

from __future__ import annotations

from pathlib import Path
from time import sleep

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from agentbot.browser.session import BrowserRuntimeSession, browser_output_dir
from agentbot.browser.views import BrowserAction, BrowserActionResult, BrowserInteractiveElement, BrowserStateSummary


def execute_browser_action(
    runtime: BrowserRuntimeSession,
    *,
    action: BrowserAction,
    summary: BrowserStateSummary | None,
) -> BrowserActionResult:
    action_type = action.action_type
    if action_type == "navigate":
        return _navigate(runtime, action.url)
    if action_type == "click":
        return _click(runtime, action, summary)
    if action_type == "type":
        return _type(runtime, action, summary)
    if action_type == "scroll":
        return _scroll(runtime, action)
    if action_type == "wait":
        return _wait(action)
    if action_type == "go_back":
        return _go_back(runtime)
    if action_type == "switch_tab":
        return _switch_tab(runtime, action.tab_id)
    raise ValueError(f"Unsupported browser action: {action_type}")


def capture_action_screenshot(runtime: BrowserRuntimeSession, *, suffix: str) -> Path | None:
    path = browser_output_dir() / f"{runtime.session_id}-{suffix}.png"
    try:
        runtime.page.screenshot(path=str(path), full_page=False, timeout=5000)
        return path
    except PlaywrightError:
        return None


def _navigate(runtime: BrowserRuntimeSession, url: str | None) -> BrowserActionResult:
    if not url:
        raise ValueError("Navigate action requires a target URL.")
    runtime.page.goto(url, wait_until="domcontentloaded", timeout=30000)
    return BrowserActionResult(
        action_type="navigate",
        success=True,
        summary_text=f"打开页面 {runtime.page.url}",
        output={"url": runtime.page.url},
    )


def _click(
    runtime: BrowserRuntimeSession,
    action: BrowserAction,
    summary: BrowserStateSummary | None,
) -> BrowserActionResult:
    element = _find_element(summary, action.element_index)
    locator = _locator_for_element(runtime, element)
    _prepare_locator_for_interaction(locator, expect_editable=False)
    before_tabs = len(runtime.context.pages)
    locator.click(timeout=10000, no_wait_after=True)
    _wait_for_page_settle(runtime)
    if len(runtime.context.pages) > before_tabs:
        runtime.page = runtime.context.pages[-1]
        runtime.page.bring_to_front()
        _wait_for_page_settle(runtime)
    label = _element_label(element)
    return BrowserActionResult(
        action_type="click",
        success=True,
        summary_text=f"点击元素 [{element.index}] {label}",
        output={"element_index": element.index, "label": label, "url": runtime.page.url},
    )


def _type(
    runtime: BrowserRuntimeSession,
    action: BrowserAction,
    summary: BrowserStateSummary | None,
) -> BrowserActionResult:
    if not action.text:
        raise ValueError("Type action requires text.")
    element = _find_element(summary, action.element_index)
    locator = _locator_for_element(runtime, element)
    _prepare_locator_for_interaction(locator, expect_editable=True)
    if element.tag == "select":
        try:
            locator.select_option(label=action.text, timeout=10000)
        except PlaywrightError:
            locator.select_option(value=action.text, timeout=10000)
    else:
        locator.click(timeout=10000)
        locator.fill(action.text, timeout=10000)
    _wait_for_page_settle(runtime)
    label = _element_label(element)
    return BrowserActionResult(
        action_type="type",
        success=True,
        summary_text=f"在元素 [{element.index}] {label} 中输入内容",
        output={"element_index": element.index, "label": label, "text": action.text},
    )


def _scroll(runtime: BrowserRuntimeSession, action: BrowserAction) -> BrowserActionResult:
    direction = action.direction or "down"
    amount = max(100, int(action.amount or 600))
    delta = amount if direction == "down" else -amount
    runtime.page.mouse.wheel(0, delta)
    _wait_for_page_settle(runtime)
    return BrowserActionResult(
        action_type="scroll",
        success=True,
        summary_text=f"页面向{'下' if delta > 0 else '上'}滚动 {abs(delta)} 像素",
        output={"direction": direction, "amount": abs(delta)},
    )


def _wait(action: BrowserAction) -> BrowserActionResult:
    seconds = min(max(int(action.amount or 2), 1), 10)
    sleep(seconds)
    return BrowserActionResult(
        action_type="wait",
        success=True,
        summary_text=f"等待 {seconds} 秒",
        output={"seconds": seconds},
    )


def _go_back(runtime: BrowserRuntimeSession) -> BrowserActionResult:
    runtime.page.go_back(wait_until="domcontentloaded", timeout=15000)
    _wait_for_page_settle(runtime)
    return BrowserActionResult(
        action_type="go_back",
        success=True,
        summary_text=f"返回上一页，当前页面为 {runtime.page.url}",
        output={"url": runtime.page.url},
    )


def _switch_tab(runtime: BrowserRuntimeSession, tab_id: str | None) -> BrowserActionResult:
    pages = runtime.context.pages
    if not pages:
        raise ValueError("No browser tabs available.")
    index = len(pages) - 1
    if tab_id:
        try:
            index = max(int(tab_id.split("_", 1)[1]) - 1, 0)
        except Exception as exc:  # pragma: no cover - defensive parse
            raise ValueError(f"Invalid tab id: {tab_id}") from exc
    if index >= len(pages):
        raise ValueError(f"Tab {tab_id or 'latest'} does not exist.")
    runtime.page = pages[index]
    runtime.page.bring_to_front()
    _wait_for_page_settle(runtime)
    return BrowserActionResult(
        action_type="switch_tab",
        success=True,
        summary_text=f"切换到标签页 tab_{index + 1}: {runtime.page.url}",
        output={"tab_id": f"tab_{index + 1}", "url": runtime.page.url},
    )


def _find_element(summary: BrowserStateSummary | None, element_index: int | None) -> BrowserInteractiveElement:
    if summary is None:
        raise ValueError("Browser action requires a current page summary.")
    if element_index is None:
        raise ValueError("Browser action requires an element_index.")
    for element in summary.interactive_elements:
        if element.index == element_index:
            return element
    raise ValueError(f"Element index {element_index} was not found in the current page summary.")


def _locator_for_element(runtime: BrowserRuntimeSession, element: BrowserInteractiveElement):
    if not element.selector:
        raise ValueError(f"Element {element.index} does not have a stable selector from the latest observation.")
    return runtime.page.locator(element.selector).first


def _prepare_locator_for_interaction(locator, *, expect_editable: bool) -> None:
    try:
        locator.wait_for(state="attached", timeout=5000)
    except PlaywrightTimeoutError as exc:
        raise ValueError("Target element is no longer attached to the page. Re-observe the page before acting.") from exc

    try:
        locator.scroll_into_view_if_needed(timeout=5000)
    except PlaywrightError:
        pass

    try:
        locator.wait_for(state="visible", timeout=5000)
    except PlaywrightTimeoutError as exc:
        raise ValueError("Target element exists but is not visible. Re-observe or scroll before acting.") from exc

    if expect_editable:
        try:
            if not locator.is_editable(timeout=5000):
                raise ValueError("Target element is visible but not editable.")
        except PlaywrightTimeoutError:
            pass


def _element_label(element: BrowserInteractiveElement) -> str:
    for candidate in [
        element.text,
        element.aria_label,
        element.placeholder,
        element.name,
        element.title,
        element.href,
        element.tag,
    ]:
        if candidate:
            return candidate
    return "unnamed element"


def _wait_for_page_settle(runtime: BrowserRuntimeSession) -> None:
    try:
        runtime.page.wait_for_load_state("domcontentloaded", timeout=5000)
    except PlaywrightTimeoutError:
        pass
