from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from agentbot.browser.runtime.events import (
    BrowserStateRequestEvent,
    ClickActionEvent,
    DialogHandledEvent,
    DownloadCompletedEvent,
    DownloadStartedEvent,
    GoBackActionEvent,
    NavigateActionEvent,
    NavigationCompletedEvent,
    NewTabNavigateActionEvent,
    PageClosedEvent,
    PageCreatedEvent,
    PressEnterActionEvent,
    ScrollActionEvent,
    SwitchTabActionEvent,
    TypeActionEvent,
    WaitActionEvent,
)
from agentbot.browser.runtime.watchdog_base import BrowserRuntimeWatchdog

if TYPE_CHECKING:
    from agentbot.browser.observation_capture import BrowserRawObservation
    from agentbot.browser.views import BrowserStateSummary


class DOMWatchdog(BrowserRuntimeWatchdog):
    """Build and cache planner-facing browser state via the runtime bus."""

    def register(self) -> None:
        self.event_bus.register(BrowserStateRequestEvent, self.on_browser_state_request)

        invalidating_events = (
            NavigateActionEvent,
            NewTabNavigateActionEvent,
            ClickActionEvent,
            TypeActionEvent,
            PressEnterActionEvent,
            ScrollActionEvent,
            WaitActionEvent,
            GoBackActionEvent,
            SwitchTabActionEvent,
            PageCreatedEvent,
            PageClosedEvent,
            NavigationCompletedEvent,
            DownloadStartedEvent,
            DownloadCompletedEvent,
            DialogHandledEvent,
        )
        for event_type in invalidating_events:
            self.event_bus.register(event_type, self.invalidate_cache)

    def on_browser_state_request(
        self,
        event: BrowserStateRequestEvent,
    ) -> tuple["BrowserStateSummary", Path | None]:
        if self.runtime.downloads_watchdog is not None:
            self.runtime.downloads_watchdog.reconcile_active_downloads()

        if self.runtime.cached_browser_state is not None and (
            not event.include_screenshot or self.runtime.cached_screenshot_path is not None
        ):
            return self.runtime.cached_browser_state, self.runtime.cached_screenshot_path

        raw_observation = self._capture_raw_observation()
        if not event.include_recent_events:
            raw_observation.recent_events = []
        summary = self._serialize_raw_observation(raw_observation)

        screenshot_path: Path | None = None
        if event.include_screenshot:
            screenshot_path = self._capture_screenshot()
            summary.screenshot_path = str(screenshot_path) if screenshot_path is not None else None

        self.runtime.cached_raw_observation = raw_observation
        self.runtime.cached_browser_state = summary
        self.runtime.cached_selector_map = {item.index: item for item in summary.interactive_elements}
        self.runtime.cached_screenshot_path = screenshot_path
        self.runtime.cached_observation_at = time.time()
        return summary, screenshot_path

    def invalidate_cache(self, _event) -> None:
        self.runtime.cached_raw_observation = None
        self.runtime.cached_browser_state = None
        self.runtime.cached_selector_map = {}
        self.runtime.cached_screenshot_path = None
        self.runtime.cached_observation_at = None

    def _capture_raw_observation(self) -> "BrowserRawObservation":
        from agentbot.browser.observation_capture import capture_raw_observation

        return capture_raw_observation(self.runtime)

    def _serialize_raw_observation(self, raw_observation: "BrowserRawObservation") -> "BrowserStateSummary":
        from agentbot.browser.observation_serialize import serialize_raw_observation

        return serialize_raw_observation(raw_observation)

    def _capture_screenshot(self) -> Path | None:
        screenshot_path = self.runtime.artifacts_dir / "page.png"
        try:
            self.runtime.page.screenshot(path=str(screenshot_path), full_page=False, timeout=5000)
            return screenshot_path
        except Exception:
            return None
