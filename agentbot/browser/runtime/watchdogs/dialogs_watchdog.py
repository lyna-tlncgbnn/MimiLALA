from __future__ import annotations

from agentbot.browser.runtime.events import DialogHandledEvent
from agentbot.browser.runtime.watchdog_base import BrowserRuntimeWatchdog


class DialogsWatchdog(BrowserRuntimeWatchdog):
    def register(self) -> None:
        self.event_bus.register(DialogHandledEvent, self._on_dialog_handled)

    def _on_dialog_handled(self, event: DialogHandledEvent) -> None:
        from agentbot.browser.session import record_runtime_event

        formatted = f"{event.dialog_type}: {event.message}"
        self.runtime.closed_popup_messages.append(formatted)
        record_runtime_event(
            self.runtime,
            "dialog",
            f"Handled dialog {formatted}",
            dedupe_recent=True,
        )
