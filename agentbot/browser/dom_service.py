"""Browser observation entrypoint built on raw capture + serialization."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from agentbot.browser.views import BrowserStateSummary

if TYPE_CHECKING:
    from agentbot.browser.session import BrowserRuntimeSession


def capture_page_state(runtime: "BrowserRuntimeSession") -> tuple[BrowserStateSummary, Path | None]:
    from agentbot.browser.session import request_browser_state

    return request_browser_state(runtime, include_screenshot=True)


def build_browser_state_summary(runtime: "BrowserRuntimeSession") -> BrowserStateSummary:
    summary, _ = capture_page_state(runtime)
    return summary


from agentbot.browser.observation_serialize import summarize_state_for_output


__all__ = ["build_browser_state_summary", "capture_page_state", "summarize_state_for_output"]
