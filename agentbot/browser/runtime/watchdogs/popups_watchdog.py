from __future__ import annotations

from agentbot.browser.runtime.events import PageClosedEvent, PageCreatedEvent
from agentbot.browser.runtime.watchdog_base import BrowserRuntimeWatchdog


class PopupsWatchdog(BrowserRuntimeWatchdog):
    def register(self) -> None:
        self.event_bus.register(PageCreatedEvent, self._on_page_created)
        self.event_bus.register(PageClosedEvent, self._on_page_closed)

    def _on_page_created(self, event: PageCreatedEvent) -> None:
        from agentbot.browser.session import record_runtime_event

        record_runtime_event(
            self.runtime,
            "tab_created",
            f"Opened new tab: {event.page.url or 'about:blank'}",
            dedupe_recent=True,
        )

    def _on_page_closed(self, event: PageClosedEvent) -> None:
        from agentbot.browser.session import record_runtime_event

        record_runtime_event(
            self.runtime,
            "page_closed",
            f"Closed page: {event.page_url or 'about:blank'}",
            dedupe_recent=True,
        )
