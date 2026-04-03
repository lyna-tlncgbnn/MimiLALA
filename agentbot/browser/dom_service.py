"""Browser observation entrypoint built on raw capture + serialization."""

from __future__ import annotations

from pathlib import Path

from agentbot.browser.observation_capture import capture_raw_observation
from agentbot.browser.observation_serialize import serialize_raw_observation, summarize_state_for_output
from agentbot.browser.session import BrowserRuntimeSession
from agentbot.browser.views import BrowserStateSummary


def capture_page_state(runtime: BrowserRuntimeSession) -> tuple[BrowserStateSummary, Path | None]:
    raw_observation = capture_raw_observation(runtime)
    summary = serialize_raw_observation(raw_observation)

    screenshot_path = runtime.artifacts_dir / "page.png"
    try:
        runtime.page.screenshot(path=str(screenshot_path), full_page=False, timeout=5000)
        screenshot_path_value: Path | None = screenshot_path
    except Exception:
        screenshot_path_value = None
    return summary, screenshot_path_value


__all__ = ["capture_page_state", "summarize_state_for_output"]
