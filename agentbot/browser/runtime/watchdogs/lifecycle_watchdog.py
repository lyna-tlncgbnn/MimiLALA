from __future__ import annotations

from agentbot.browser.runtime.events import BrowserClosedEvent, PageClosedEvent, PageCreatedEvent
from agentbot.browser.runtime.watchdog_base import BrowserRuntimeWatchdog


class LifecycleWatchdog(BrowserRuntimeWatchdog):
    def register(self) -> None:
        self.event_bus.register(PageCreatedEvent, self._on_page_created)
        self.event_bus.register(PageClosedEvent, self._on_page_closed)
        self.event_bus.register(BrowserClosedEvent, self._on_browser_closed)

    def _on_page_created(self, event: PageCreatedEvent) -> None:
        from agentbot.browser.session import record_runtime_event

        record_runtime_event(
            self.runtime,
            "page_created",
            f"Created page: {event.page.url or 'about:blank'}",
            dedupe_recent=True,
        )

    def _on_page_closed(self, event: PageClosedEvent) -> None:
        from agentbot.browser.session import record_runtime_event

        event_type = "active_page_closed" if event.is_active_page else "page_closed"
        prefix = "Closed active page" if event.is_active_page else "Closed page"
        record_runtime_event(
            self.runtime,
            event_type,
            f"{prefix}: {event.page_url or 'about:blank'}",
            dedupe_recent=True,
        )

    def _on_browser_closed(self, event: BrowserClosedEvent) -> None:
        from agentbot.browser.session import record_runtime_event

        message = "Browser closed"
        if event.reason:
            message = f"{message}: {event.reason}"
        record_runtime_event(
            self.runtime,
            "browser_closed",
            message,
            dedupe_recent=True,
        )
