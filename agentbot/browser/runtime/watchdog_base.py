from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentbot.browser.session import BrowserRuntimeSession


class BrowserRuntimeWatchdog:
    """Base class for runtime watchdogs."""

    def __init__(self, runtime: "BrowserRuntimeSession") -> None:
        self.runtime = runtime
        self.event_bus = runtime.event_bus

    def register(self) -> None:
        raise NotImplementedError
