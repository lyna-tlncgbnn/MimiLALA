"""Raw browser observation capture helpers inspired by browser-use."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Frame, Page

if TYPE_CHECKING:
    from agentbot.browser.session import BrowserRuntimeSession

MAX_RAW_CANDIDATES_PER_DOCUMENT = 120
AGENTBOT_ELEMENT_ATTR = "data-agentbot-id"


@dataclass(slots=True)
class BrowserRawElementCandidate:
    selector: str
    tag: str
    kind: str
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
    section_hint: str = ""
    landmark_hint: str = ""
    frame_path: list[str] = field(default_factory=list)
    enabled: bool = True
    visible: bool = True
    in_viewport: bool = True
    disabled: bool = False
    checked: bool = False
    expanded: bool = False
    pressed: bool = False
    is_form_control: bool = False
    is_text_input: bool = False
    is_search_like: bool = False
    is_primary_action: bool = False
    top_offset: float = 0.0
    left_offset: float = 0.0
    width: float = 0.0
    height: float = 0.0


@dataclass(slots=True)
class BrowserRawDocumentSnapshot:
    frame_name: str
    frame_url: str
    frame_path: list[str] = field(default_factory=list)
    main_text: str = ""
    interactive_candidates: list[BrowserRawElementCandidate] = field(default_factory=list)
    page_info: dict[str, int] = field(default_factory=dict)
    headings: list[str] = field(default_factory=list)
    landmarks: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BrowserRawObservation:
    url: str
    title: str
    tabs: list[dict[str, str]] = field(default_factory=list)
    main_document: BrowserRawDocumentSnapshot | None = None
    frame_documents: list[BrowserRawDocumentSnapshot] = field(default_factory=list)
    recent_events: list[str] = field(default_factory=list)
    browser_errors: list[str] = field(default_factory=list)


DOCUMENT_RAW_CAPTURE_SCRIPT = """
() => {
  const ATTR = 'data-agentbot-id';
  const MAX_ELEMENTS = 120;
  const SELECTOR = [
    'a[href]',
    'button',
    'input',
    'textarea',
    'select',
    'summary',
    'iframe',
    'frame',
    '[role="button"]',
    '[role="link"]',
    '[role="textbox"]',
    '[role="searchbox"]',
    '[role="combobox"]',
    '[role="checkbox"]',
    '[role="radio"]',
    '[role="tab"]',
    '[role="menuitem"]',
    '[contenteditable="true"]',
    '[tabindex]:not([tabindex="-1"])',
    '[onclick]',
    '[onmousedown]',
    '[onmouseup]',
    '[onkeydown]',
    '[onkeyup]'
  ].join(',');

  const normalizeText = (value) => (value || '').replace(/\\s+/g, ' ').trim();
  const interactiveTagNames = new Set([
    'button', 'input', 'select', 'textarea', 'a', 'details', 'summary', 'option', 'optgroup'
  ]);
  const interactiveRoles = new Set([
    'button', 'link', 'menuitem', 'option', 'radio', 'checkbox', 'tab',
    'textbox', 'combobox', 'slider', 'spinbutton', 'search', 'searchbox',
    'row', 'cell', 'gridcell', 'switch'
  ]);
  const landmarkTags = new Set(['main', 'nav', 'header', 'footer', 'aside', 'section', 'form', 'dialog']);

  document.querySelectorAll('[' + ATTR + ']').forEach((node) => node.removeAttribute(ATTR));

  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 1280;
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 720;

  const getComputedAX = (element) => {
    const fallback = { role: '', name: '', checked: false, expanded: false, pressed: false, disabled: false };
    try {
      if (typeof window.getComputedAccessibleNode !== 'function') return fallback;
      const ax = window.getComputedAccessibleNode(element);
      if (!ax) return fallback;
      return {
        role: normalizeText(ax.role || ''),
        name: normalizeText(ax.name || ''),
        checked: Boolean(ax.checked),
        expanded: Boolean(ax.expanded),
        pressed: Boolean(ax.pressed),
        disabled: Boolean(ax.disabled),
      };
    } catch (error) {
      return fallback;
    }
  };

  const getAssociatedLabel = (element) => {
    if (!element) return '';
    try {
      if (typeof element.labels !== 'undefined' && element.labels && element.labels.length > 0) {
        const text = normalizeText(Array.from(element.labels).map((item) => item.innerText || item.textContent || '').join(' '));
        if (text) return text;
      }
    } catch (error) {
    }
    const labelledBy = element.getAttribute('aria-labelledby');
    if (labelledBy) {
      const text = normalizeText(
        labelledBy
          .split(/\\s+/)
          .map((id) => {
            const node = document.getElementById(id);
            return node ? (node.innerText || node.textContent || '') : '';
          })
          .join(' ')
      );
      if (text) return text;
    }
    return '';
  };

  const getElementText = (element, axInfo) => {
    const candidates = [
      axInfo.name,
      element.getAttribute('aria-label'),
      getAssociatedLabel(element),
      element.getAttribute('placeholder'),
      element.getAttribute('title'),
      element.getAttribute('name'),
      element.innerText,
      element.textContent,
      element.getAttribute('value')
    ];
    for (const candidate of candidates) {
      const text = normalizeText(candidate);
      if (text) return text.slice(0, 200);
    }
    return '';
  };

  const isActuallyVisible = (element, style, rect) => {
    if (!element || !style || !rect) return false;
    if (element.hidden) return false;
    if (element.getAttribute('aria-hidden') === 'true') return false;
    if (style.display === 'none') return false;
    if (style.visibility === 'hidden' || style.visibility === 'collapse') return false;
    if (Number.parseFloat(style.opacity || '1') <= 0.05) return false;
    if (rect.width < 4 || rect.height < 4) return false;
    if (typeof element.checkVisibility === 'function') {
      try {
        if (!element.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) return false;
      } catch (error) {
      }
    }
    return true;
  };

  const isViewportVisible = (rect) => (
    rect.bottom > 0 &&
    rect.right > 0 &&
    rect.top < viewportHeight &&
    rect.left < viewportWidth
  );

  const hasSearchIndicators = (element) => {
    const indicators = ['search', 'magnify', 'glass', 'lookup', 'find', 'query', 'search-icon', 'search-button', '搜索', '查询'];
    const className = normalizeText(element.getAttribute('class') || '').toLowerCase();
    const elementId = normalizeText(element.getAttribute('id') || '').toLowerCase();
    const text = normalizeText(element.innerText || element.textContent || '').toLowerCase();
    return indicators.some((item) => className.includes(item) || elementId.includes(item) || text.includes(item));
  };

  const getNearestLandmark = (element) => {
    const landmark = element.closest('main, nav, header, footer, aside, section, form, dialog, [role="main"], [role="navigation"], [role="search"], [role="dialog"], [role="form"]');
    if (!landmark) return { section: '', landmark: '' };
    const tag = (landmark.tagName || '').toLowerCase();
    const role = normalizeText(landmark.getAttribute('role') || '').toLowerCase();
    const heading = landmark.querySelector('h1, h2, h3, [role="heading"]');
    const headingText = normalizeText(heading ? (heading.innerText || heading.textContent || '') : '');
    const aria = normalizeText(landmark.getAttribute('aria-label') || landmark.getAttribute('title') || '');
    return {
      section: headingText || aria || tag || role,
      landmark: role || tag
    };
  };

  const isInteractiveElement = (element, style, rect, axInfo) => {
    const tag = (element.tagName || '').toLowerCase();
    const role = normalizeText(element.getAttribute('role') || '').toLowerCase();
    if (['html', 'body'].includes(tag)) return false;
    if (!isActuallyVisible(element, style, rect)) return false;
    if (element.disabled || element.getAttribute('aria-disabled') === 'true' || axInfo.disabled) return false;
    if (style.pointerEvents === 'none') return false;
    if (tag === 'input' && (element.getAttribute('type') || '').toLowerCase() === 'hidden') return false;
    if ((tag === 'iframe' || tag === 'frame') && rect.width > 100 && rect.height > 100) return true;
    if (interactiveTagNames.has(tag)) return true;
    if (interactiveRoles.has(role)) return true;
    if (interactiveRoles.has((axInfo.role || '').toLowerCase())) return true;

    const tabindex = element.getAttribute('tabindex');
    if (tabindex !== null) {
      const value = Number.parseInt(tabindex, 10);
      if (!Number.isNaN(value) && value >= 0) return true;
    }

    if ((element.getAttribute('contenteditable') || '').toLowerCase() === 'true') return true;
    if ((style.cursor || '').toLowerCase() === 'pointer') return true;
    if (axInfo.checked || axInfo.expanded || axInfo.pressed) return true;
    if (hasSearchIndicators(element)) return true;
    return false;
  };

  const getKind = (element, axInfo) => {
    const tag = (element.tagName || '').toLowerCase();
    const role = normalizeText(element.getAttribute('role') || '').toLowerCase();
    const axRole = (axInfo.role || '').toLowerCase();
    if (tag === 'a' || role === 'link' || axRole === 'link') return 'link';
    if (tag === 'button' || role === 'button' || axRole === 'button' || tag === 'summary') return 'button';
    if (tag === 'textarea') return 'textarea';
    if (tag === 'select') return 'select';
    if (tag === 'input') return 'input';
    return 'control';
  };

  const headings = Array.from(document.querySelectorAll('h1, h2, h3, [role="heading"]'))
    .map((node) => normalizeText(node.innerText || node.textContent || ''))
    .filter(Boolean)
    .slice(0, 12);

  const landmarks = Array.from(document.querySelectorAll('main, nav, header, footer, aside, section, form, dialog, [role="main"], [role="navigation"], [role="search"], [role="dialog"], [role="form"]'))
    .map((node) => {
      const tag = (node.tagName || '').toLowerCase();
      const role = normalizeText(node.getAttribute('role') || '').toLowerCase();
      const label = normalizeText(node.getAttribute('aria-label') || node.getAttribute('title') || '');
      return normalizeText(label || role || tag);
    })
    .filter(Boolean)
    .slice(0, 20);

  const nodes = Array.from(document.querySelectorAll(SELECTOR));
  const interactive = [];

  for (const element of nodes) {
    if (interactive.length >= MAX_ELEMENTS) break;
    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    const axInfo = getComputedAX(element);
    if (!isInteractiveElement(element, style, rect, axInfo)) continue;

    const agentbotId = 'ab-' + (interactive.length + 1);
    element.setAttribute(ATTR, agentbotId);

    const context = getNearestLandmark(element);
    const tag = (element.tagName || '').toLowerCase();
    const inputType = normalizeText(element.getAttribute('type') || '').toLowerCase();
    const role = normalizeText(element.getAttribute('role') || '').toLowerCase();
    const labelText = getAssociatedLabel(element);
    const text = getElementText(element, axInfo);

    interactive.push({
      selector: '[' + ATTR + '="' + agentbotId + '"]',
      kind: getKind(element, axInfo),
      tag,
      text,
      label_text: labelText,
      href: element.href || '',
      role: element.getAttribute('role') || '',
      ax_role: axInfo.role || '',
      ax_name: axInfo.name || '',
      input_type: element.getAttribute('type') || '',
      name: element.getAttribute('name') || '',
      placeholder: element.getAttribute('placeholder') || '',
      title: element.getAttribute('title') || '',
      aria_label: element.getAttribute('aria-label') || '',
      section_hint: context.section || '',
      landmark_hint: context.landmark || '',
      enabled: !(element.disabled || element.getAttribute('aria-disabled') === 'true' || axInfo.disabled),
      visible: true,
      in_viewport: isViewportVisible(rect),
      disabled: Boolean(element.disabled || element.getAttribute('aria-disabled') === 'true' || axInfo.disabled),
      checked: Boolean(element.checked || element.getAttribute('aria-checked') === 'true' || axInfo.checked),
      expanded: Boolean(element.getAttribute('aria-expanded') === 'true' || axInfo.expanded),
      pressed: Boolean(element.getAttribute('aria-pressed') === 'true' || axInfo.pressed),
      is_form_control: ['input', 'textarea', 'select'].includes(tag) || role === 'combobox',
      is_text_input: tag === 'textarea' || (tag === 'input' && !['checkbox', 'radio', 'submit', 'button', 'hidden', 'file'].includes(inputType)),
      is_search_like: hasSearchIndicators(element) || inputType === 'search' || context.landmark === 'search',
      is_primary_action: role === 'button' || tag === 'button' || /(search|查询|搜索|submit|提交)/i.test(text),
      top_offset: Math.round(rect.top),
      left_offset: Math.round(rect.left),
      width: Math.round(rect.width),
      height: Math.round(rect.height)
    });
  }

  const bodyText = normalizeText(document.body ? (document.body.innerText || document.body.textContent || '') : '');

  return {
    interactive_candidates: interactive,
    main_text: bodyText.slice(0, 7000),
    headings,
    landmarks,
    page_info: {
      viewport_width: viewportWidth,
      viewport_height: viewportHeight,
      scroll_x: Math.round(window.scrollX || 0),
      scroll_y: Math.round(window.scrollY || 0),
      pixels_above: Math.max(Math.round(window.scrollY || 0), 0),
      pixels_below: Math.max(
        Math.round(
          (document.documentElement ? document.documentElement.scrollHeight : 0) -
          ((window.scrollY || 0) + viewportHeight)
        ),
        0
      )
    }
  };
}
"""


def capture_raw_observation(runtime: "BrowserRuntimeSession") -> BrowserRawObservation:
    page = runtime.page
    try:
        page.wait_for_load_state("load", timeout=2000)
    except Exception:
        pass

    title = page.title() or page.url or "Untitled page"
    main_document = _capture_document(page, frame_name="main document", frame_path=[])
    frame_documents = _capture_frame_documents(page)
    tabs = _capture_tabs(runtime)
    recent_events = [str(event.get("message") or "") for event in runtime.recent_events[-8:] if str(event.get("message") or "").strip()]
    return BrowserRawObservation(
        url=page.url,
        title=title,
        tabs=tabs,
        main_document=main_document,
        frame_documents=frame_documents,
        recent_events=recent_events,
        browser_errors=[],
    )


def _capture_document(target: Page | Frame, *, frame_name: str, frame_path: list[str]) -> BrowserRawDocumentSnapshot:
    snapshot = _snapshot_target(target)
    candidates = [
        _parse_candidate(item, frame_path=frame_path)
        for item in snapshot.get("interactive_candidates") or []
        if isinstance(item, dict)
    ]
    return BrowserRawDocumentSnapshot(
        frame_name=frame_name,
        frame_url=getattr(target, "url", "") or "about:blank",
        frame_path=list(frame_path),
        main_text=str(snapshot.get("main_text") or ""),
        interactive_candidates=candidates[:MAX_RAW_CANDIDATES_PER_DOCUMENT],
        page_info=_normalize_page_info(snapshot.get("page_info")),
        headings=[str(item) for item in (snapshot.get("headings") or []) if str(item).strip()],
        landmarks=[str(item) for item in (snapshot.get("landmarks") or []) if str(item).strip()],
    )


def _capture_frame_documents(page: Page) -> list[BrowserRawDocumentSnapshot]:
    documents: list[BrowserRawDocumentSnapshot] = []
    for frame in page.frames[1:]:
        try:
            selector_path = _frame_selector_path(frame)
            if not selector_path:
                continue
            documents.append(
                _capture_document(
                    frame,
                    frame_name=_frame_name(frame),
                    frame_path=selector_path,
                )
            )
        except Exception:
            continue
    return documents


def _capture_tabs(runtime: BrowserRuntimeSession) -> list[dict[str, str]]:
    tabs: list[dict[str, str]] = []
    for index, tab_page in enumerate(runtime.context.pages, start=1):
        try:
            tab_title = tab_page.title() or tab_page.url or f"Tab {index}"
        except Exception:
            tab_title = tab_page.url or f"Tab {index}"
        tabs.append({"tab_id": f"tab_{index}", "url": tab_page.url or "about:blank", "title": tab_title})
    return tabs


def _snapshot_target(target: Page | Frame) -> dict[str, Any]:
    try:
        return target.evaluate(DOCUMENT_RAW_CAPTURE_SCRIPT) or {}
    except PlaywrightError:
        return {}


def _parse_candidate(item: dict[str, Any], *, frame_path: list[str]) -> BrowserRawElementCandidate:
    return BrowserRawElementCandidate(
        selector=str(item.get("selector") or ""),
        tag=str(item.get("tag") or "div"),
        kind=str(item.get("kind") or "control"),
        text=str(item.get("text") or ""),
        label_text=str(item.get("label_text") or ""),
        href=str(item.get("href") or ""),
        role=str(item.get("role") or ""),
        ax_role=str(item.get("ax_role") or ""),
        ax_name=str(item.get("ax_name") or ""),
        input_type=str(item.get("input_type") or ""),
        name=str(item.get("name") or ""),
        placeholder=str(item.get("placeholder") or ""),
        title=str(item.get("title") or ""),
        aria_label=str(item.get("aria_label") or ""),
        section_hint=str(item.get("section_hint") or ""),
        landmark_hint=str(item.get("landmark_hint") or ""),
        frame_path=list(frame_path),
        enabled=bool(item.get("enabled", True)),
        visible=bool(item.get("visible", True)),
        in_viewport=bool(item.get("in_viewport", True)),
        disabled=bool(item.get("disabled", False)),
        checked=bool(item.get("checked", False)),
        expanded=bool(item.get("expanded", False)),
        pressed=bool(item.get("pressed", False)),
        is_form_control=bool(item.get("is_form_control", False)),
        is_text_input=bool(item.get("is_text_input", False)),
        is_search_like=bool(item.get("is_search_like", False)),
        is_primary_action=bool(item.get("is_primary_action", False)),
        top_offset=float(item.get("top_offset") or 0.0),
        left_offset=float(item.get("left_offset") or 0.0),
        width=float(item.get("width") or 0.0),
        height=float(item.get("height") or 0.0),
    )


def _normalize_page_info(raw_payload: Any) -> dict[str, int]:
    if not isinstance(raw_payload, dict):
        return {
            "viewport_width": 1280,
            "viewport_height": 720,
            "scroll_x": 0,
            "scroll_y": 0,
            "pixels_above": 0,
            "pixels_below": 0,
        }
    return {
        "viewport_width": int(raw_payload.get("viewport_width") or 1280),
        "viewport_height": int(raw_payload.get("viewport_height") or 720),
        "scroll_x": int(raw_payload.get("scroll_x") or 0),
        "scroll_y": int(raw_payload.get("scroll_y") or 0),
        "pixels_above": int(raw_payload.get("pixels_above") or 0),
        "pixels_below": max(int(raw_payload.get("pixels_below") or 0), 0),
    }


def _frame_selector_path(frame: Frame) -> list[str]:
    path: list[str] = []
    current = frame
    while current.parent_frame is not None:
        frame_element = current.frame_element()
        attr_value = frame_element.get_attribute(AGENTBOT_ELEMENT_ATTR)
        if not attr_value:
            attr_value = frame_element.evaluate(
                """(element, attr) => {
                    let currentValue = element.getAttribute(attr);
                    if (!currentValue) {
                        currentValue = 'ab-frame-' + Math.random().toString(36).slice(2, 10);
                        element.setAttribute(attr, currentValue);
                    }
                    return currentValue;
                }""",
                AGENTBOT_ELEMENT_ATTR,
            )
        path.insert(0, f'[{AGENTBOT_ELEMENT_ATTR}="{attr_value}"]')
        current = current.parent_frame
    return path


def _frame_name(frame: Frame) -> str:
    try:
        frame_element = frame.frame_element()
        for attr in ("title", "name", "id"):
            value = frame_element.get_attribute(attr)
            if value:
                return value
    except Exception:
        pass
    return "embedded frame"
