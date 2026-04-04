from __future__ import annotations

from agentbot.browser.runtime.events import NavigationCompletedEvent
from agentbot.browser.runtime.watchdog_base import BrowserRuntimeWatchdog


class NavigationWatchdog(BrowserRuntimeWatchdog):
    def register(self) -> None:
        self.event_bus.register(NavigationCompletedEvent, self._on_navigation_completed)

    def _on_navigation_completed(self, event: NavigationCompletedEvent) -> None:
        from agentbot.browser.session import record_runtime_event

        record_runtime_event(
            self.runtime,
            "navigation",
            f"Navigated to {event.url or 'about:blank'}",
            dedupe_recent=True,
        )
