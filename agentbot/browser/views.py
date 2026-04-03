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
    frame_path: list[str] = field(default_factory=list)
    text: str = ""
    label_text: str = ""
    href: str = ""
    role: str = ""
    ax_role: str = ""
    ax_name: str = ""
    input_type: str = ""
    name: str = ""
    placeholder: str = ""
    title: str = ""
    aria_label: str = ""
    enabled: bool = True
    visible: bool = True
    in_viewport: bool = True
    disabled: bool = False
    checked: bool = False
    expanded: bool = False
    pressed: bool = False
    iframe_hint: str = ""
    section_hint: str = ""
    landmark_hint: str = ""
    semantic_group: str = ""
    semantic_score: float = 0.0
    bounds: BrowserElementBounds = field(default_factory=BrowserElementBounds)


@dataclass(slots=True)
class BrowserSemanticGroup:
    kind: str
    label: str
    element_indexes: list[int] = field(default_factory=list)


@dataclass(slots=True)
class BrowserStateSummary:
    url: str
    title: str
    tabs: list[BrowserTabInfo] = field(default_factory=list)
    page_info: BrowserPageInfo = field(default_factory=BrowserPageInfo)
    dom_summary: str = ""
    interactive_elements: list[BrowserInteractiveElement] = field(default_factory=list)
    semantic_groups: list[BrowserSemanticGroup] = field(default_factory=list)
    prioritized_hints: list[str] = field(default_factory=list)
    screenshot_path: str | None = None
    observation_fingerprint: str | None = None
    iframe_summaries: list[str] = field(default_factory=list)
    recent_events: list[str] = field(default_factory=list)
    browser_errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BrowserAction:
    action_type: Literal["navigate", "new_tab_navigate", "click", "type", "press_enter", "scroll", "wait", "go_back", "switch_tab", "done"]
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


@dataclass(slots=True)
class BrowserActionSequenceResult:
    results: list[BrowserActionResult] = field(default_factory=list)
    interrupted: bool = False
    interruption_reason: str | None = None
