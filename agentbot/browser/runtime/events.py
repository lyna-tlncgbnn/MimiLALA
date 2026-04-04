from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.sync_api import Download, Page

from agentbot.browser.views import BrowserInteractiveElement


@dataclass(slots=True)
class BrowserRuntimeEvent:
    created_at: float


@dataclass(slots=True)
class NavigateActionEvent(BrowserRuntimeEvent):
    url: str


@dataclass(slots=True)
class NewTabNavigateActionEvent(BrowserRuntimeEvent):
    url: str


@dataclass(slots=True)
class ClickActionEvent(BrowserRuntimeEvent):
    element: BrowserInteractiveElement


@dataclass(slots=True)
class TypeActionEvent(BrowserRuntimeEvent):
    element: BrowserInteractiveElement
    text: str


@dataclass(slots=True)
class PressEnterActionEvent(BrowserRuntimeEvent):
    pass


@dataclass(slots=True)
class ScrollActionEvent(BrowserRuntimeEvent):
    direction: str
    amount: int


@dataclass(slots=True)
class WaitActionEvent(BrowserRuntimeEvent):
    seconds: int


@dataclass(slots=True)
class GoBackActionEvent(BrowserRuntimeEvent):
    pass


@dataclass(slots=True)
class SwitchTabActionEvent(BrowserRuntimeEvent):
    tab_id: str | None


@dataclass(slots=True)
class PageCreatedEvent(BrowserRuntimeEvent):
    page: Page


@dataclass(slots=True)
class PageClosedEvent(BrowserRuntimeEvent):
    page_url: str
    page: Page | None = None
    is_active_page: bool = False


@dataclass(slots=True)
class BrowserClosedEvent(BrowserRuntimeEvent):
    reason: str = ""


@dataclass(slots=True)
class BrowserStateRequestEvent(BrowserRuntimeEvent):
    include_screenshot: bool = True
    include_recent_events: bool = True


@dataclass(slots=True)
class DialogHandledEvent(BrowserRuntimeEvent):
    dialog_type: str
    message: str


@dataclass(slots=True)
class NavigationCompletedEvent(BrowserRuntimeEvent):
    url: str
    page: Page | None = None


@dataclass(slots=True)
class DownloadStartedEvent(BrowserRuntimeEvent):
    download_id: str
    suggested_filename: str
    source_url: str
    download: Download
    page: Page | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DownloadProgressEvent(BrowserRuntimeEvent):
    download_id: str
    suggested_filename: str
    received_bytes: int
    total_bytes: int | None = None
    state: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DownloadCompletedEvent(BrowserRuntimeEvent):
    download_id: str
    suggested_filename: str
    destination: Path
    metadata: dict[str, Any] = field(default_factory=dict)
