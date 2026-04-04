from __future__ import annotations

import threading
import time
from time import sleep
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from agentbot.browser.runtime.events import (
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
from agentbot.browser.runtime.watchdog_base import BrowserRuntimeWatchdog
from agentbot.browser.views import BrowserActionResult


class DefaultActionWatchdog(BrowserRuntimeWatchdog):
    def register(self) -> None:
        self.event_bus.register(NavigateActionEvent, self.on_navigate)
        self.event_bus.register(NewTabNavigateActionEvent, self.on_new_tab_navigate)
        self.event_bus.register(ClickActionEvent, self.on_click)
        self.event_bus.register(TypeActionEvent, self.on_type)
        self.event_bus.register(PressEnterActionEvent, self.on_press_enter)
        self.event_bus.register(ScrollActionEvent, self.on_scroll)
        self.event_bus.register(WaitActionEvent, self.on_wait)
        self.event_bus.register(GoBackActionEvent, self.on_go_back)
        self.event_bus.register(SwitchTabActionEvent, self.on_switch_tab)

    def on_navigate(self, event: NavigateActionEvent) -> BrowserActionResult:
        before_events = len(self.runtime.recent_events)
        before_url = self.runtime.page.url or ""
        self.runtime.page.goto(event.url, wait_until="domcontentloaded", timeout=30000)
        effects = self._collect_post_action_effects(before_events=before_events, before_url=before_url)
        return BrowserActionResult(
            action_type="navigate",
            success=True,
            summary_text=self._with_effect_suffix(f"Opened page {self.runtime.page.url}", effects),
            output={"url": self.runtime.page.url, **effects},
        )

    def on_new_tab_navigate(self, event: NewTabNavigateActionEvent) -> BrowserActionResult:
        before_events = len(self.runtime.recent_events)
        page = self.runtime.context.new_page()
        self.runtime.page = page
        try:
            self.runtime.page.bring_to_front()
        except PlaywrightError:
            pass
        before_url = self.runtime.page.url or ""
        self.runtime.page.goto(event.url, wait_until="domcontentloaded", timeout=30000)
        effects = self._collect_post_action_effects(before_events=before_events, before_url=before_url)
        return BrowserActionResult(
            action_type="new_tab_navigate",
            success=True,
            summary_text=self._with_effect_suffix(f"Opened new tab {self.runtime.page.url}", effects),
            output={"tab_id": f"tab_{len(self.runtime.context.pages)}", "url": self.runtime.page.url, **effects},
        )

    def on_click(self, event: ClickActionEvent) -> BrowserActionResult:
        locator = self._locator_for_element(event.element)
        self._prepare_locator_for_interaction(locator, expect_editable=False)
        before_events = len(self.runtime.recent_events)
        before_url = self.runtime.page.url or ""
        before_tabs = len(self.runtime.context.pages)

        metadata = self._execute_click_with_download_detection(locator=locator, before_tabs=before_tabs)
        self._wait_for_page_settle()
        label = self._element_label(event.element)
        effects = self._collect_post_action_effects(
            before_events=before_events,
            before_url=before_url,
            timeout_seconds=1.5,
        )
        output = {
            "element_index": event.element.index,
            "label": label,
            "url": self._safe_page_url(),
            **effects,
            **metadata,
        }
        return BrowserActionResult(
            action_type="click",
            success=True,
            summary_text=self._with_effect_suffix(f"Clicked element [{event.element.index}] {label}", output),
            output=output,
        )

    def on_type(self, event: TypeActionEvent) -> BrowserActionResult:
        locator = self._locator_for_element(event.element)
        self._prepare_locator_for_interaction(locator, expect_editable=True)
        before_events = len(self.runtime.recent_events)
        before_url = self.runtime.page.url or ""
        if event.element.tag == "select":
            try:
                locator.select_option(label=event.text, timeout=10000)
            except PlaywrightError:
                locator.select_option(value=event.text, timeout=10000)
        else:
            locator.click(timeout=10000)
            locator.fill(event.text, timeout=10000)
        self._wait_for_page_settle()
        label = self._element_label(event.element)
        effects = self._collect_post_action_effects(before_events=before_events, before_url=before_url)
        return BrowserActionResult(
            action_type="type",
            success=True,
            summary_text=self._with_effect_suffix(f"Typed into element [{event.element.index}] {label}", effects),
            output={"element_index": event.element.index, "label": label, "text": event.text, **effects},
        )

    def on_press_enter(self, _event: PressEnterActionEvent) -> BrowserActionResult:
        before_events = len(self.runtime.recent_events)
        before_url = self.runtime.page.url or ""
        self.runtime.page.keyboard.press("Enter")
        self._wait_for_page_settle()
        effects = self._collect_post_action_effects(before_events=before_events, before_url=before_url, timeout_seconds=1.5)
        return BrowserActionResult(
            action_type="press_enter",
            success=True,
            summary_text=self._with_effect_suffix("Pressed Enter on the active page", effects),
            output={"key": "Enter", **effects},
        )

    def on_scroll(self, event: ScrollActionEvent) -> BrowserActionResult:
        delta = event.amount if event.direction == "down" else -event.amount
        before_events = len(self.runtime.recent_events)
        before_url = self.runtime.page.url or ""
        self.runtime.page.mouse.wheel(0, delta)
        self._wait_for_page_settle()
        effects = self._collect_post_action_effects(before_events=before_events, before_url=before_url, timeout_seconds=0.5)
        return BrowserActionResult(
            action_type="scroll",
            success=True,
            summary_text=self._with_effect_suffix(
                f"Scrolled {'down' if delta > 0 else 'up'} by {abs(delta)} pixels",
                effects,
            ),
            output={"direction": event.direction, "amount": abs(delta), **effects},
        )

    def on_wait(self, event: WaitActionEvent) -> BrowserActionResult:
        sleep(event.seconds)
        return BrowserActionResult(
            action_type="wait",
            success=True,
            summary_text=f"Waited {event.seconds} seconds",
            output={"seconds": event.seconds},
        )

    def on_go_back(self, _event: GoBackActionEvent) -> BrowserActionResult:
        before_events = len(self.runtime.recent_events)
        before_url = self.runtime.page.url or ""
        self.runtime.page.go_back(wait_until="domcontentloaded", timeout=15000)
        self._wait_for_page_settle()
        effects = self._collect_post_action_effects(before_events=before_events, before_url=before_url)
        return BrowserActionResult(
            action_type="go_back",
            success=True,
            summary_text=self._with_effect_suffix(f"Navigated back to {self.runtime.page.url}", effects),
            output={"url": self.runtime.page.url, **effects},
        )

    def on_switch_tab(self, event: SwitchTabActionEvent) -> BrowserActionResult:
        pages = self.runtime.context.pages
        if not pages:
            raise ValueError("No browser tabs available.")
        index = len(pages) - 1
        if event.tab_id:
            try:
                index = max(int(event.tab_id.split("_", 1)[1]) - 1, 0)
            except Exception as exc:
                raise ValueError(f"Invalid tab id: {event.tab_id}") from exc
        if index >= len(pages):
            raise ValueError(f"Tab {event.tab_id or 'latest'} does not exist.")
        before_events = len(self.runtime.recent_events)
        before_url = self.runtime.page.url or ""
        self.runtime.page = pages[index]
        self.runtime.page.bring_to_front()
        self._wait_for_page_settle()
        effects = self._collect_post_action_effects(before_events=before_events, before_url=before_url, timeout_seconds=0.5)
        return BrowserActionResult(
            action_type="switch_tab",
            success=True,
            summary_text=self._with_effect_suffix(f"Switched to tab_{index + 1}: {self.runtime.page.url}", effects),
            output={"tab_id": f"tab_{index + 1}", "url": self.runtime.page.url, **effects},
        )

    def _execute_click_with_download_detection(self, *, locator, before_tabs: int) -> dict[str, Any]:
        download_started = threading.Event()
        download_completed = threading.Event()
        download_info: dict[str, Any] = {}

        def on_download_start(info: dict[str, Any]) -> None:
            download_info.update(
                {
                    "guid": info.get("guid", ""),
                    "url": info.get("url", ""),
                    "suggested_filename": info.get("suggested_filename", "download"),
                }
            )
            download_started.set()

        def on_download_complete(info: dict[str, Any]) -> None:
            if download_info.get("guid") and info.get("guid") and info.get("guid") != download_info.get("guid"):
                return
            download_info.update(info)
            download_completed.set()

        self.runtime.downloads_watchdog.register_download_callbacks(
            on_start=on_download_start,
            on_complete=on_download_complete,
        )
        try:
            locator.click(timeout=10000, no_wait_after=True)
            popup_page = self._wait_for_new_page(before_tabs=before_tabs, timeout_seconds=1.5)
            if popup_page is not None:
                self.runtime.page = popup_page
                try:
                    popup_page.bring_to_front()
                except PlaywrightError:
                    pass
                self._wait_for_page_settle()

            metadata: dict[str, Any] = {}
            if download_started.wait(timeout=self.runtime.download_start_timeout_seconds):
                download_id = str(download_info.get("guid") or self.runtime.latest_download_id or "")
                metadata["download_started"] = {
                    "file_name": download_info.get("suggested_filename", "download"),
                    "url": download_info.get("url", ""),
                }
                try:
                    completed_info = self.runtime.downloads_watchdog.finalize_download(download_id)
                    metadata["download"] = {
                        "path": completed_info.get("path", ""),
                        "file_name": completed_info.get("file_name", download_info.get("suggested_filename", "download")),
                        "file_size": int(completed_info.get("file_size") or 0),
                        "file_type": completed_info.get("file_type"),
                        "mime_type": completed_info.get("mime_type"),
                    }
                    download_completed.set()
                except Exception as exc:
                    active = self.runtime.active_downloads.get(download_id, {})
                    metadata["download_error"] = {
                        "file_name": download_info.get("suggested_filename", "download"),
                        "state": str(active.get("state") or "error"),
                        "message": str(exc),
                    }
            return metadata
        finally:
            self.runtime.downloads_watchdog.unregister_download_callbacks(
                on_start=on_download_start,
                on_complete=on_download_complete,
            )

    def _locator_for_element(self, element):
        if not element.selector:
            raise ValueError(f"Element {element.index} does not have a stable selector from the latest observation.")
        locator_context = self.runtime.page
        for frame_selector in element.frame_path:
            locator_context = locator_context.frame_locator(frame_selector)
        return locator_context.locator(element.selector).first

    def _prepare_locator_for_interaction(self, locator, *, expect_editable: bool) -> None:
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

    def _wait_for_page_settle(self) -> None:
        if self._page_is_closed():
            return
        try:
            self.runtime.page.wait_for_load_state("domcontentloaded", timeout=5000)
        except (PlaywrightTimeoutError, PlaywrightError):
            pass

    def _wait_for_new_page(self, *, before_tabs: int, timeout_seconds: float):
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if len(self.runtime.context.pages) > before_tabs:
                return self.runtime.context.pages[-1]
            sleep(0.1)
        return None

    def _collect_post_action_effects(
        self,
        *,
        before_events: int,
        before_url: str,
        timeout_seconds: float = 1.0,
    ) -> dict[str, Any]:
        from agentbot.browser.session import wait_for_runtime_event

        event_matches = wait_for_runtime_event(
            self.runtime,
            since_index=before_events,
            event_types={
                "navigation",
                "download",
                "download_started",
                "download_error",
                "dialog",
                "tab_created",
                "page_closed",
                "active_page_closed",
                "browser_closed",
            },
            timeout_seconds=timeout_seconds,
        )
        current_url = self._safe_page_url()
        page_changed = bool(before_url and current_url and before_url != current_url)
        recent_messages = [event.get("message", "") for event in event_matches if event.get("message")]
        downloads = [event.get("message", "") for event in event_matches if event.get("type") == "download"]
        download_started = [event.get("message", "") for event in event_matches if event.get("type") == "download_started"]
        download_errors = [event.get("message", "") for event in event_matches if event.get("type") == "download_error"]
        dialogs = [event.get("message", "") for event in event_matches if event.get("type") == "dialog"]
        tab_events = [event.get("message", "") for event in event_matches if event.get("type") == "tab_created"]
        navigation_events = [event.get("message", "") for event in event_matches if event.get("type") == "navigation"]
        page_closed_events = [event.get("message", "") for event in event_matches if event.get("type") == "page_closed"]
        active_page_closed_events = [event.get("message", "") for event in event_matches if event.get("type") == "active_page_closed"]
        browser_closed_events = [event.get("message", "") for event in event_matches if event.get("type") == "browser_closed"]
        observation_stale = page_changed or bool(
            downloads
            or download_started
            or download_errors
            or dialogs
            or tab_events
            or navigation_events
            or page_closed_events
            or active_page_closed_events
            or browser_closed_events
        )
        return {
            "page_changed": page_changed,
            "observation_stale": observation_stale,
            "recent_events": recent_messages,
            "downloads": downloads,
            "download_started_events": download_started,
            "download_error_events": download_errors,
            "dialogs": dialogs,
            "tab_events": tab_events,
            "navigation_events": navigation_events,
            "page_closed_events": page_closed_events,
            "active_page_closed_events": active_page_closed_events,
            "browser_closed_events": browser_closed_events,
        }

    def _with_effect_suffix(self, summary_text: str, effects: dict[str, Any]) -> str:
        parts = [summary_text]
        if effects.get("page_changed"):
            parts.append("Page changed after the action.")
        if effects.get("tab_events"):
            parts.append(str(effects["tab_events"][0]))
        if effects.get("download_started_events"):
            parts.append(str(effects["download_started_events"][0]))
        if effects.get("downloads"):
            parts.append(str(effects["downloads"][0]))
        if effects.get("download_error_events"):
            parts.append(str(effects["download_error_events"][0]))
        if effects.get("dialogs"):
            parts.append(str(effects["dialogs"][0]))
        if effects.get("active_page_closed_events"):
            parts.append(str(effects["active_page_closed_events"][0]))
        if effects.get("browser_closed_events"):
            parts.append(str(effects["browser_closed_events"][0]))
        return " ".join(part for part in parts if part)

    def _page_is_closed(self) -> bool:
        try:
            return self.runtime.page.is_closed()
        except Exception:
            return True

    def _safe_page_url(self) -> str:
        if self._page_is_closed():
            return ""
        try:
            return self.runtime.page.url or ""
        except Exception:
            return ""

    def _element_label(self, element) -> str:
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
