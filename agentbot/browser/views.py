"""Browser subgraph view models inspired by browser-use, adapted for AgentBot."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(slots=True)
class BrowserElementBounds:
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0


@dataclass(slots=True)
class BrowserTabInfo:
    tab_id: str
    url: str
    title: str
    parent_tab_id: str | None = None


@dataclass(slots=True)
class BrowserPageInfo:
    viewport_width: int = 1280
    viewport_height: int = 720
    scroll_x: int = 0
    scroll_y: int = 0
    pixels_above: int = 0
    pixels_below: int = 0


@dataclass(slots=True)
class BrowserInteractiveElement:
    index: int
    kind: Literal["link", "button", "input", "textarea", "select", "control"]
    tag: str
    selector: str
    text: str = ""
    href: str = ""
    role: str = ""
    input_type: str = ""
    name: str = ""
    placeholder: str = ""
    title: str = ""
    aria_label: str = ""
    enabled: bool = True
    visible: bool = True
    in_viewport: bool = True
    bounds: BrowserElementBounds = field(default_factory=BrowserElementBounds)


@dataclass(slots=True)
class BrowserStateSummary:
    url: str
    title: str
    tabs: list[BrowserTabInfo] = field(default_factory=list)
    page_info: BrowserPageInfo = field(default_factory=BrowserPageInfo)
    dom_summary: str = ""
    interactive_elements: list[BrowserInteractiveElement] = field(default_factory=list)
    screenshot_path: str | None = None
    browser_errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BrowserAction:
    action_type: Literal["navigate", "click", "type", "scroll", "wait", "go_back", "switch_tab", "done"]
    reason: str = ""
    url: str | None = None
    element_index: int | None = None
    text: str | None = None
    direction: Literal["up", "down"] | None = None
    amount: int | None = None
    tab_id: str | None = None
    approval_required: bool = False
    approval_reason: str | None = None


@dataclass(slots=True)
class BrowserActionResult:
    action_type: str
    success: bool
    summary_text: str
    output: dict | None = None
