"""Low-level Playwright browser actions for the browser subgraph."""

from __future__ import annotations

from pathlib import Path
import time
from time import sleep

from playwright.sync_api import Download, Page
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from agentbot.browser.session import (
    BrowserRuntimeSession,
    dispatch_runtime_action,
    record_runtime_event,
    wait_for_runtime_event,
)
from agentbot.browser.runtime import (
    ClickActionEvent,
    GoBackActionEvent,
    NavigateActionEvent,
    NewTabNavigateActionEvent,
    PressEnterActionEvent,
    ScrollActionEvent,
    SwitchTabActionEvent,
    TypeActionEvent,
    WaitActionEvent,
)
from agentbot.browser.views import (
    BrowserAction,
    BrowserActionResult,
    BrowserActionSequenceResult,
    BrowserInteractiveElement,
    BrowserStateSummary,
)


def execute_browser_action(
    runtime: BrowserRuntimeSession,
    *,
    action: BrowserAction,
    summary: BrowserStateSummary | None,
) -> BrowserActionResult:
    action_type = action.action_type
    created_at = time.time()
    result = None
    if action_type == "navigate":
        if not action.url:
            raise ValueError("Navigate action requires a target URL.")
        result = dispatch_runtime_action(runtime, NavigateActionEvent(created_at=created_at, url=action.url))
    elif action_type == "new_tab_navigate":
        if not action.url:
            raise ValueError("New-tab navigate action requires a target URL.")
        result = dispatch_runtime_action(runtime, NewTabNavigateActionEvent(created_at=created_at, url=action.url))
    elif action_type == "click":
        element = _find_element(runtime, summary, action.element_index)
        _assert_page_still_matches_observation(runtime, summary)
        result = dispatch_runtime_action(runtime, ClickActionEvent(created_at=created_at, element=element))
    elif action_type == "type":
        if not action.text:
            raise ValueError("Type action requires text.")
        element = _find_element(runtime, summary, action.element_index)
        _assert_page_still_matches_observation(runtime, summary)
        result = dispatch_runtime_action(runtime, TypeActionEvent(created_at=created_at, element=element, text=action.text))
    elif action_type == "press_enter":
        result = dispatch_runtime_action(runtime, PressEnterActionEvent(created_at=created_at))
    elif action_type == "scroll":
        direction = action.direction or "down"
        amount = max(100, int(action.amount or 600))
        result = dispatch_runtime_action(runtime, ScrollActionEvent(created_at=created_at, direction=direction, amount=amount))
    elif action_type == "wait":
        seconds = min(max(int(action.amount or 2), 1), 10)
        result = dispatch_runtime_action(runtime, WaitActionEvent(created_at=created_at, seconds=seconds))
    elif action_type == "go_back":
        result = dispatch_runtime_action(runtime, GoBackActionEvent(created_at=created_at))
    elif action_type == "switch_tab":
        result = dispatch_runtime_action(runtime, SwitchTabActionEvent(created_at=created_at, tab_id=action.tab_id))
    else:
        raise ValueError(f"Unsupported browser action: {action_type}")
    if result is None:
        raise ValueError(f"Browser runtime did not handle action: {action_type}")
    return result


def execute_browser_actions(
    runtime: BrowserRuntimeSession,
    *,
    actions: list[BrowserAction],
    summary: BrowserStateSummary | None,
) -> BrowserActionSequenceResult:
    results: list[BrowserActionResult] = []
    if not actions:
        raise ValueError("Browser action sequence must contain at least one action.")

    for action in actions:
        result = execute_browser_action(runtime, action=action, summary=summary)
        results.append(result)
        output = result.output or {}
        if bool(output.get("page_changed")) or bool(output.get("observation_stale")):
            return BrowserActionSequenceResult(
                results=results,
                interrupted=True,
                interruption_reason="The page changed after an action, so the remaining sequence was interrupted.",
            )

    return BrowserActionSequenceResult(results=results)


def capture_action_screenshot(runtime: BrowserRuntimeSession, *, suffix: str) -> Path | None:
    path = runtime.artifacts_dir / f"{suffix}.png"
    try:
        runtime.page.screenshot(path=str(path), full_page=False, timeout=5000)
        return path
    except PlaywrightError:
        return None


def _navigate(runtime: BrowserRuntimeSession, url: str | None) -> BrowserActionResult:
    if not url:
        raise ValueError("Navigate action requires a target URL.")
    before_events = len(runtime.recent_events)
    before_url = runtime.page.url or ""
    runtime.page.goto(url, wait_until="domcontentloaded", timeout=30000)
    effects = _collect_post_action_effects(runtime, before_events=before_events, before_url=before_url)
    return BrowserActionResult(
        action_type="navigate",
        success=True,
        summary_text=_with_effect_suffix(f"Opened page {runtime.page.url}", effects),
        output={"url": runtime.page.url, **effects},
    )


def _new_tab_navigate(runtime: BrowserRuntimeSession, url: str | None) -> BrowserActionResult:
    if not url:
        raise ValueError("New-tab navigate action requires a target URL.")
    before_events = len(runtime.recent_events)
    page = runtime.context.new_page()
    runtime.page = page
    try:
        runtime.page.bring_to_front()
    except PlaywrightError:
        pass
    before_url = runtime.page.url or ""
    runtime.page.goto(url, wait_until="domcontentloaded", timeout=30000)
    effects = _collect_post_action_effects(runtime, before_events=before_events, before_url=before_url)
    return BrowserActionResult(
        action_type="new_tab_navigate",
        success=True,
        summary_text=_with_effect_suffix(f"Opened new tab {runtime.page.url}", effects),
        output={"tab_id": f"tab_{len(runtime.context.pages)}", "url": runtime.page.url, **effects},
    )


def _click(
    runtime: BrowserRuntimeSession,
    action: BrowserAction,
    summary: BrowserStateSummary | None,
) -> BrowserActionResult:
    element = _find_element(summary, action.element_index)
    _assert_page_still_matches_observation(runtime, summary)
    locator = _locator_for_element(runtime, element)
    _prepare_locator_for_interaction(locator, expect_editable=False)
    before_events = len(runtime.recent_events)
    before_tabs = len(runtime.context.pages)
    before_downloads = set(runtime.downloaded_files)
    before_url = runtime.page.url or ""
    _click_with_runtime_guards(
        runtime,
        locator=locator,
        before_tabs=before_tabs,
        before_downloads=before_downloads,
    )
    _wait_for_page_settle(runtime)
    if len(runtime.context.pages) > before_tabs:
        runtime.page = runtime.context.pages[-1]
        runtime.page.bring_to_front()
        _wait_for_page_settle(runtime)
    label = _element_label(element)
    effects = _collect_post_action_effects(runtime, before_events=before_events, before_url=before_url)
    return BrowserActionResult(
        action_type="click",
        success=True,
        summary_text=_with_effect_suffix(f"Clicked element [{element.index}] {label}", effects),
        output={"element_index": element.index, "label": label, "url": runtime.page.url, **effects},
    )


def _type(
    runtime: BrowserRuntimeSession,
    action: BrowserAction,
    summary: BrowserStateSummary | None,
) -> BrowserActionResult:
    if not action.text:
        raise ValueError("Type action requires text.")
    element = _find_element(summary, action.element_index)
    _assert_page_still_matches_observation(runtime, summary)
    locator = _locator_for_element(runtime, element)
    _prepare_locator_for_interaction(locator, expect_editable=True)
    before_events = len(runtime.recent_events)
    before_url = runtime.page.url or ""
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
    effects = _collect_post_action_effects(runtime, before_events=before_events, before_url=before_url)
    return BrowserActionResult(
        action_type="type",
        success=True,
        summary_text=_with_effect_suffix(f"Typed into element [{element.index}] {label}", effects),
        output={"element_index": element.index, "label": label, "text": action.text, **effects},
    )


def _press_enter(runtime: BrowserRuntimeSession) -> BrowserActionResult:
    before_events = len(runtime.recent_events)
    before_tabs = len(runtime.context.pages)
    before_downloads = set(runtime.downloaded_files)
    before_url = runtime.page.url or ""
    runtime.page.keyboard.press("Enter")
    _wait_for_page_settle(runtime)
    popup_page = _wait_for_new_page(runtime, popup_pages=[], before_tabs=before_tabs, timeout_seconds=1.0)
    if popup_page is not None:
        runtime.page = popup_page
        try:
            runtime.page.bring_to_front()
        except PlaywrightError:
            pass
        _wait_for_page_settle(runtime)
    _wait_for_new_download_files(runtime, before_downloads=before_downloads, timeout_seconds=1.0)
    effects = _collect_post_action_effects(runtime, before_events=before_events, before_url=before_url)
    return BrowserActionResult(
        action_type="press_enter",
        success=True,
        summary_text=_with_effect_suffix("Pressed Enter on the active page", effects),
        output={"key": "Enter", **effects},
    )


def _scroll(runtime: BrowserRuntimeSession, action: BrowserAction) -> BrowserActionResult:
    direction = action.direction or "down"
    amount = max(100, int(action.amount or 600))
    delta = amount if direction == "down" else -amount
    before_events = len(runtime.recent_events)
    before_url = runtime.page.url or ""
    runtime.page.mouse.wheel(0, delta)
    _wait_for_page_settle(runtime)
    effects = _collect_post_action_effects(runtime, before_events=before_events, before_url=before_url, timeout_seconds=0.5)
    return BrowserActionResult(
        action_type="scroll",
        success=True,
        summary_text=_with_effect_suffix(
            f"Scrolled {'down' if delta > 0 else 'up'} by {abs(delta)} pixels",
            effects,
        ),
        output={"direction": direction, "amount": abs(delta), **effects},
    )


def _wait(action: BrowserAction) -> BrowserActionResult:
    seconds = min(max(int(action.amount or 2), 1), 10)
    sleep(seconds)
    return BrowserActionResult(
        action_type="wait",
        success=True,
        summary_text=f"Waited {seconds} seconds",
        output={"seconds": seconds},
    )


def _go_back(runtime: BrowserRuntimeSession) -> BrowserActionResult:
    before_events = len(runtime.recent_events)
    before_url = runtime.page.url or ""
    runtime.page.go_back(wait_until="domcontentloaded", timeout=15000)
    _wait_for_page_settle(runtime)
    effects = _collect_post_action_effects(runtime, before_events=before_events, before_url=before_url)
    return BrowserActionResult(
        action_type="go_back",
        success=True,
        summary_text=_with_effect_suffix(f"Navigated back to {runtime.page.url}", effects),
        output={"url": runtime.page.url, **effects},
    )


def _switch_tab(runtime: BrowserRuntimeSession, tab_id: str | None) -> BrowserActionResult:
    pages = runtime.context.pages
    if not pages:
        raise ValueError("No browser tabs available.")
    index = len(pages) - 1
    if tab_id:
        try:
            index = max(int(tab_id.split("_", 1)[1]) - 1, 0)
        except Exception as exc:
            raise ValueError(f"Invalid tab id: {tab_id}") from exc
    if index >= len(pages):
        raise ValueError(f"Tab {tab_id or 'latest'} does not exist.")
    before_events = len(runtime.recent_events)
    before_url = runtime.page.url or ""
    runtime.page = pages[index]
    runtime.page.bring_to_front()
    _wait_for_page_settle(runtime)
    effects = _collect_post_action_effects(runtime, before_events=before_events, before_url=before_url, timeout_seconds=0.5)
    return BrowserActionResult(
        action_type="switch_tab",
        success=True,
        summary_text=_with_effect_suffix(f"Switched to tab_{index + 1}: {runtime.page.url}", effects),
        output={"tab_id": f"tab_{index + 1}", "url": runtime.page.url, **effects},
    )


def _find_element(
    runtime: BrowserRuntimeSession,
    summary: BrowserStateSummary | None,
    element_index: int | None,
) -> BrowserInteractiveElement:
    if element_index is None:
        raise ValueError("Browser action requires an element_index.")

    cached_element = runtime.cached_selector_map.get(element_index)
    if isinstance(cached_element, BrowserInteractiveElement):
        return cached_element

    if summary is None:
        raise ValueError("Browser action requires a current page summary.")
    for element in summary.interactive_elements:
        if element.index == element_index:
            return element
    raise ValueError(f"Element index {element_index} was not found in the current page summary.")


def _locator_for_element(runtime: BrowserRuntimeSession, element: BrowserInteractiveElement):
    if not element.selector:
        raise ValueError(f"Element {element.index} does not have a stable selector from the latest observation.")
    locator_context = runtime.page
    for frame_selector in element.frame_path:
        locator_context = locator_context.frame_locator(frame_selector)
    return locator_context.locator(element.selector).first


def _assert_page_still_matches_observation(runtime: BrowserRuntimeSession, summary: BrowserStateSummary | None) -> None:
    if summary is None:
        return
    observed_url = (summary.url or "").strip()
    current_url = (runtime.page.url or "").strip()
    if observed_url and current_url and observed_url != current_url:
        raise ValueError(
            f"Page changed since observation. Observed {observed_url}, current page is {current_url}. Re-observe before acting."
        )


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
        element.label_text,
        element.ax_name,
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
    if _page_is_closed(runtime.page):
        return
    try:
        runtime.page.wait_for_load_state("domcontentloaded", timeout=5000)
    except (PlaywrightTimeoutError, PlaywrightError):
        pass


def _click_with_runtime_guards(
    runtime: BrowserRuntimeSession,
    *,
    locator,
    before_tabs: int,
    before_downloads: set[str],
) -> None:
    source_page = runtime.page
    popup_pages: list[Page] = []
    download_items: list[Download] = []
    page_handler = _build_page_capture_handler(popup_pages)
    download_handler = _build_download_capture_handler(download_items)
    runtime.context.on("page", page_handler)
    source_page.on("download", download_handler)

    click_error: Exception | None = None
    try:
        try:
            locator.click(timeout=10000, no_wait_after=True)
        except Exception as exc:
            click_error = exc
    finally:
        runtime.context.remove_listener("page", page_handler)
        source_page.remove_listener("download", download_handler)

    if click_error is not None:
        raise click_error

    popup_page = _wait_for_new_page(runtime, popup_pages=popup_pages, before_tabs=before_tabs, timeout_seconds=1.5)
    if popup_page is not None:
        runtime.page = popup_page
        try:
            runtime.page.bring_to_front()
        except PlaywrightError:
            pass
        _wait_for_page_settle(runtime)

    _finalize_expected_download(runtime, download_items=download_items, before_downloads=before_downloads)
    _wait_for_new_download_files(runtime, before_downloads=before_downloads, timeout_seconds=1.5)


def _build_page_capture_handler(popup_pages: list[Page]):
    def _on_page(page: Page) -> None:
        popup_pages.append(page)

    return _on_page


def _build_download_capture_handler(download_items: list[Download]):
    def _on_download(download: Download) -> None:
        download_items.append(download)

    return _on_download


def _wait_for_new_page(
    runtime: BrowserRuntimeSession,
    *,
    popup_pages: list[Page],
    before_tabs: int,
    timeout_seconds: float,
) -> Page | None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if popup_pages:
            page = popup_pages[-1]
            record_runtime_event(
                runtime,
                "tab_created",
                f"Opened new tab: {page.url or 'about:blank'}",
                dedupe_recent=True,
            )
            return page
        if len(runtime.context.pages) > before_tabs:
            page = runtime.context.pages[-1]
            record_runtime_event(
                runtime,
                "tab_created",
                f"Opened new tab: {page.url or 'about:blank'}",
                dedupe_recent=True,
            )
            return page
        sleep(0.1)
    return None


def _finalize_expected_download(
    runtime: BrowserRuntimeSession,
    *,
    download_items: list[Download],
    before_downloads: set[str],
) -> None:
    if _wait_for_new_download_files(runtime, before_downloads=before_downloads, timeout_seconds=1.0):
        return
    if not download_items:
        return
    try:
        download = download_items[-1]
        suggested = download.suggested_filename or "download"
        destination = _unique_download_destination(runtime, suggested)
        download.save_as(str(destination))
        destination_str = str(destination)
        if destination_str not in runtime.downloaded_files:
            runtime.downloaded_files.append(destination_str)
        record_runtime_event(runtime, "download", f"Downloaded file: {destination.name} -> {destination}", dedupe_recent=True)
    except Exception as exc:
        record_runtime_event(runtime, "download_error", f"Download handling failed: {exc}", dedupe_recent=True)


def _wait_for_new_download_files(
    runtime: BrowserRuntimeSession,
    *,
    before_downloads: set[str],
    timeout_seconds: float,
) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        current_downloads = set(runtime.downloaded_files)
        new_items = sorted(current_downloads - before_downloads)
        if new_items:
            for item in new_items:
                filename = Path(item).name
                record_runtime_event(runtime, "download", f"Downloaded file: {filename} -> {item}", dedupe_recent=True)
            return True
        sleep(0.1)
    return False


def _unique_download_destination(runtime: BrowserRuntimeSession, filename: str) -> Path:
    target = runtime.downloads_dir / filename
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    counter = 1
    while True:
        candidate = runtime.downloads_dir / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _collect_post_action_effects(
    runtime: BrowserRuntimeSession,
    *,
    before_events: int,
    before_url: str,
    timeout_seconds: float = 1.0,
) -> dict:
    event_matches = wait_for_runtime_event(
        runtime,
        since_index=before_events,
        event_types={"navigation", "download", "dialog", "tab_created"},
        timeout_seconds=timeout_seconds,
    )
    current_url = _safe_page_url(runtime.page)
    page_changed = bool(before_url and current_url and before_url != current_url)
    recent_messages = [event.get("message", "") for event in event_matches if event.get("message")]
    downloads = [event.get("message", "") for event in event_matches if event.get("type") == "download"]
    dialogs = [event.get("message", "") for event in event_matches if event.get("type") == "dialog"]
    tab_events = [event.get("message", "") for event in event_matches if event.get("type") == "tab_created"]
    navigation_events = [event.get("message", "") for event in event_matches if event.get("type") == "navigation"]
    observation_stale = page_changed or bool(downloads or dialogs or tab_events or navigation_events)
    return {
        "page_changed": page_changed,
        "observation_stale": observation_stale,
        "recent_events": recent_messages,
        "downloads": downloads,
        "dialogs": dialogs,
        "tab_events": tab_events,
        "navigation_events": navigation_events,
    }


def _with_effect_suffix(summary_text: str, effects: dict) -> str:
    parts = [summary_text]
    if effects.get("page_changed"):
        parts.append("Page changed after the action.")
    if effects.get("tab_events"):
        parts.append(str(effects["tab_events"][0]))
    if effects.get("downloads"):
        parts.append(str(effects["downloads"][0]))
    if effects.get("dialogs"):
        parts.append(str(effects["dialogs"][0]))
    return " ".join(part for part in parts if part)


def _page_is_closed(page: Page) -> bool:
    try:
        return page.is_closed()
    except Exception:
        return True


def _safe_page_url(page: Page) -> str:
    if _page_is_closed(page):
        return ""
    try:
        return page.url or ""
    except Exception:
        return ""
