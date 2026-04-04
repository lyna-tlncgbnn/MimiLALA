from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from .events import BrowserRuntimeEvent

EventHandler = Callable[[BrowserRuntimeEvent], Any]


class BrowserRuntimeEventBus:
    """Small synchronous event bus for browser runtime events."""

    def __init__(self) -> None:
        self._handlers: dict[type[BrowserRuntimeEvent], list[EventHandler]] = defaultdict(list)

    def register(self, event_type: type[BrowserRuntimeEvent], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def emit(self, event: BrowserRuntimeEvent) -> list[Any]:
        results: list[Any] = []
        for registered_type, handlers in self._handlers.items():
            if isinstance(event, registered_type):
                for handler in handlers:
                    results.append(handler(event))
        return results

    def request(self, event: BrowserRuntimeEvent) -> Any:
        result: Any = None
        for registered_type, handlers in self._handlers.items():
            if isinstance(event, registered_type):
                for handler in handlers:
                    candidate = handler(event)
                    if candidate is not None:
                        result = candidate
        return result
