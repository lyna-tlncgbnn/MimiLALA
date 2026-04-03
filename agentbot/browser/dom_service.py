"""Browser observation layer with stable interactive-element mapping."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from agentbot.browser.session import BrowserRuntimeSession, browser_output_dir
from agentbot.browser.views import (
    BrowserElementBounds,
    BrowserInteractiveElement,
    BrowserPageInfo,
    BrowserStateSummary,
    BrowserTabInfo,
)
from agentbot.tools.common import truncate_content

MAX_INTERACTIVE_ELEMENTS = 30
AGENTBOT_ELEMENT_ATTR = "data-agentbot-id"


DOM_SNAPSHOT_SCRIPT = """
() => {
  const ATTR = 'data-agentbot-id';
  const MAX_ELEMENTS = 30;
  const SELECTOR = [
    'a[href]',
    'button',
    'input',
    'textarea',
    'select',
    'summary',
    '[role="button"]',
    '[role="link"]',
    '[role="textbox"]',
    '[contenteditable="true"]',
    '[tabindex]:not([tabindex="-1"])'
  ].join(',');

  const previous = document.querySelectorAll('[' + ATTR + ']');
  previous.forEach((node) => node.removeAttribute(ATTR));

  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 1280;
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 720;

  const normalizeText = (value) => (value || '').replace(/\\s+/g, ' ').trim();

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

  const getKind = (element) => {
    const tag = (element.tagName || '').toLowerCase();
    const role = (element.getAttribute('role') || '').toLowerCase();
    if (tag === 'a' || role === 'link') return 'link';
    if (tag === 'button' || role === 'button' || tag === 'summary') return 'button';
    if (tag === 'textarea') return 'textarea';
    if (tag === 'select') return 'select';
    if (tag === 'input') return 'input';
    return 'control';
  };

  const getAssociatedLabel = (element) => {
    if (!element) return '';
    if (typeof element.labels !== 'undefined' && element.labels && element.labels.length > 0) {
      const text = normalizeText(Array.from(element.labels).map((item) => item.innerText || item.textContent || '').join(' '));
      if (text) return text;
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

  const getElementText = (element) => {
    const candidates = [
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
      if (text) return text.slice(0, 160);
    }
    return '';
  };

  const shouldSkip = (element, style, rect) => {
    if (!isActuallyVisible(element, style, rect)) return true;
    const tag = (element.tagName || '').toLowerCase();
    const inputType = (element.getAttribute('type') || '').toLowerCase();
    if (tag === 'input' && ['hidden'].includes(inputType)) return true;
    if (style.pointerEvents === 'none') return true;
    return false;
  };

  const nodes = Array.from(document.querySelectorAll(SELECTOR));
  const interactive = [];

  for (const element of nodes) {
    if (interactive.length >= MAX_ELEMENTS) break;
    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    if (shouldSkip(element, style, rect)) continue;

    const agentbotId = 'ab-' + (interactive.length + 1);
    element.setAttribute(ATTR, agentbotId);

    interactive.push({
      index: interactive.length + 1,
      kind: getKind(element),
      tag: (element.tagName || '').toLowerCase(),
      selector: '[' + ATTR + '="' + agentbotId + '"]',
      text: getElementText(element),
      href: element.href || '',
      role: element.getAttribute('role') || '',
      input_type: element.getAttribute('type') || '',
      name: element.getAttribute('name') || '',
      placeholder: element.getAttribute('placeholder') || '',
      title: element.getAttribute('title') || '',
      aria_label: element.getAttribute('aria-label') || '',
      enabled: !(element.disabled || element.getAttribute('aria-disabled') === 'true'),
      visible: true,
      in_viewport: isViewportVisible(rect),
      bounds: {
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height)
      }
    });
  }

  const bodyText = normalizeText(document.body ? (document.body.innerText || document.body.textContent || '') : '');

  return {
    interactive_elements: interactive,
    main_text: bodyText.slice(0, 4000),
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


def capture_page_state(runtime: BrowserRuntimeSession) -> tuple[BrowserStateSummary, Path | None]:
    page = runtime.page
    title = page.title() or page.url or "Untitled page"
    snapshot = _safe_eval(page, DOM_SNAPSHOT_SCRIPT, default={}) or {}

    interactive_elements = _parse_interactive_elements(snapshot.get("interactive_elements"))
    page_info = _parse_page_info(snapshot.get("page_info"))
    text_content = str(snapshot.get("main_text") or "")

    tabs: list[BrowserTabInfo] = []
    for index, tab_page in enumerate(runtime.context.pages, start=1):
        try:
            tab_title = tab_page.title() or tab_page.url or f"Tab {index}"
        except Exception:
            tab_title = tab_page.url or f"Tab {index}"
        tabs.append(BrowserTabInfo(tab_id=f"tab_{index}", url=tab_page.url or "about:blank", title=tab_title))

    summary = BrowserStateSummary(
        url=page.url,
        title=title,
        tabs=tabs,
        page_info=page_info,
        dom_summary=_render_dom_summary(title, page.url, text_content, interactive_elements, page_info),
        interactive_elements=interactive_elements,
        browser_errors=[],
    )

    screenshot_path = browser_output_dir() / f"{runtime.session_id}-page.png"
    try:
        page.screenshot(path=str(screenshot_path), full_page=False, timeout=5000)
        screenshot_path_value: Path | None = screenshot_path
    except Exception:
        screenshot_path_value = None
    return summary, screenshot_path_value


def summarize_state_for_output(summary: BrowserStateSummary, screenshot_path: Path | None = None) -> dict[str, Any]:
    payload = {
        "url": summary.url,
        "title": summary.title,
        "tabs": [asdict(tab) for tab in summary.tabs],
        "page_info": asdict(summary.page_info),
        "dom_summary": summary.dom_summary,
        "interactive_elements": [asdict(element) for element in summary.interactive_elements],
        "browser_errors": list(summary.browser_errors),
    }
    if screenshot_path is not None:
        payload["screenshot_path"] = str(screenshot_path)
    return payload


def _parse_interactive_elements(raw_items: Any) -> list[BrowserInteractiveElement]:
    elements: list[BrowserInteractiveElement] = []
    if not isinstance(raw_items, list):
        return elements

    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            continue
        bounds_payload = item.get("bounds") if isinstance(item.get("bounds"), dict) else {}
        elements.append(
            BrowserInteractiveElement(
                index=int(item.get("index") or index),
                kind=str(item.get("kind") or "control"),
                tag=str(item.get("tag") or "div"),
                selector=str(item.get("selector") or ""),
                text=str(item.get("text") or ""),
                href=str(item.get("href") or ""),
                role=str(item.get("role") or ""),
                input_type=str(item.get("input_type") or ""),
                name=str(item.get("name") or ""),
                placeholder=str(item.get("placeholder") or ""),
                title=str(item.get("title") or ""),
                aria_label=str(item.get("aria_label") or ""),
                enabled=bool(item.get("enabled", True)),
                visible=bool(item.get("visible", True)),
                in_viewport=bool(item.get("in_viewport", True)),
                bounds=BrowserElementBounds(
                    x=float(bounds_payload.get("x") or 0.0),
                    y=float(bounds_payload.get("y") or 0.0),
                    width=float(bounds_payload.get("width") or 0.0),
                    height=float(bounds_payload.get("height") or 0.0),
                ),
            )
        )
    return elements


def _parse_page_info(raw_payload: Any) -> BrowserPageInfo:
    if not isinstance(raw_payload, dict):
        return BrowserPageInfo()
    return BrowserPageInfo(
        viewport_width=int(raw_payload.get("viewport_width") or 1280),
        viewport_height=int(raw_payload.get("viewport_height") or 720),
        scroll_x=int(raw_payload.get("scroll_x") or 0),
        scroll_y=int(raw_payload.get("scroll_y") or 0),
        pixels_above=int(raw_payload.get("pixels_above") or 0),
        pixels_below=max(int(raw_payload.get("pixels_below") or 0), 0),
    )


def _render_dom_summary(
    title: str,
    url: str,
    text_content: str,
    interactive_elements: list[BrowserInteractiveElement],
    page_info: BrowserPageInfo,
) -> str:
    lines = [
        f"Title: {title}",
        f"URL: {url}",
        f"Scroll: y={page_info.scroll_y}, below={page_info.pixels_below}px",
        "Main text:",
        truncate_content(text_content or "(no visible text)", max_chars=1800),
        f"Interactive elements ({len(interactive_elements)} shown, viewport-visible first):",
    ]

    if interactive_elements:
        for item in interactive_elements:
            label = " / ".join(
                part
                for part in [
                    item.kind,
                    item.tag,
                    item.input_type,
                    item.name,
                    item.placeholder,
                    item.aria_label,
                    item.text,
                ]
                if part
            )
            if item.href:
                label = f"{label} -> {item.href}" if label else item.href
            suffix_parts = []
            if not item.enabled:
                suffix_parts.append("disabled")
            if not item.in_viewport:
                suffix_parts.append("offscreen")
            bounds = item.bounds
            if bounds.width > 0 and bounds.height > 0:
                suffix_parts.append(
                    f"box=({int(bounds.x)},{int(bounds.y)},{int(bounds.width)}x{int(bounds.height)})"
                )
            suffix = f" [{' | '.join(suffix_parts)}]" if suffix_parts else ""
            lines.append(f"- [{item.index}] {label or '(unnamed element)'}{suffix}")
    else:
        lines.append("- none")

    return truncate_content("\n".join(lines), max_chars=3200)


def _safe_eval(page, expression: str, *, default):
    try:
        return page.evaluate(expression)
    except Exception:
        return default
