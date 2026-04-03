"""Serialize raw browser observations into planner-friendly state."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from agentbot.browser.observation_capture import BrowserRawDocumentSnapshot, BrowserRawElementCandidate, BrowserRawObservation
from agentbot.browser.views import (
    BrowserElementBounds,
    BrowserInteractiveElement,
    BrowserPageInfo,
    BrowserSemanticGroup,
    BrowserStateSummary,
    BrowserTabInfo,
)
from agentbot.tools.common import truncate_content

MAX_INTERACTIVE_ELEMENTS = 40


def serialize_raw_observation(raw: BrowserRawObservation) -> BrowserStateSummary:
    main_document = raw.main_document or BrowserRawDocumentSnapshot(frame_name="main document", frame_url=raw.url)
    page_info = _page_info_from_raw(main_document.page_info)

    ranked_candidates = _rank_candidates(main_document, raw.frame_documents)
    interactive_elements = [_candidate_to_interactive(item, index) for index, item in enumerate(ranked_candidates[:MAX_INTERACTIVE_ELEMENTS], start=1)]
    semantic_groups = _build_semantic_groups(interactive_elements)
    prioritized_hints = _build_prioritized_hints(main_document, interactive_elements, semantic_groups)
    iframe_summaries = _build_frame_summaries(raw.frame_documents)

    observation_fingerprint = _compute_observation_fingerprint(
        raw.url,
        raw.title,
        main_document.main_text,
        interactive_elements,
        iframe_summaries,
        prioritized_hints,
    )

    summary = BrowserStateSummary(
        url=raw.url,
        title=raw.title,
        tabs=[BrowserTabInfo(**tab) for tab in raw.tabs],
        page_info=page_info,
        dom_summary=_render_dom_summary(
            title=raw.title,
            url=raw.url,
            text_content=main_document.main_text,
            interactive_elements=interactive_elements,
            semantic_groups=semantic_groups,
            prioritized_hints=prioritized_hints,
            page_info=page_info,
            iframe_summaries=iframe_summaries,
            recent_events=list(raw.recent_events),
        ),
        interactive_elements=interactive_elements,
        semantic_groups=semantic_groups,
        prioritized_hints=prioritized_hints,
        observation_fingerprint=observation_fingerprint,
        iframe_summaries=iframe_summaries,
        recent_events=list(raw.recent_events),
        browser_errors=list(raw.browser_errors),
    )
    return summary


def summarize_state_for_output(summary: BrowserStateSummary, screenshot_path: str | None = None) -> dict:
    payload = {
        "url": summary.url,
        "title": summary.title,
        "tabs": [asdict(tab) for tab in summary.tabs],
        "page_info": asdict(summary.page_info),
        "dom_summary": summary.dom_summary,
        "interactive_elements": [asdict(element) for element in summary.interactive_elements],
        "semantic_groups": [asdict(group) for group in summary.semantic_groups],
        "prioritized_hints": list(summary.prioritized_hints),
        "observation_fingerprint": summary.observation_fingerprint,
        "iframe_summaries": list(summary.iframe_summaries),
        "recent_events": list(summary.recent_events),
        "browser_errors": list(summary.browser_errors),
    }
    if screenshot_path is not None:
        payload["screenshot_path"] = str(screenshot_path)
    return payload


def _rank_candidates(
    main_document: BrowserRawDocumentSnapshot,
    frame_documents: list[BrowserRawDocumentSnapshot],
) -> list[BrowserRawElementCandidate]:
    candidates: list[BrowserRawElementCandidate] = []
    candidates.extend(main_document.interactive_candidates)
    for document in frame_documents:
        candidates.extend(document.interactive_candidates)

    def _score(item: BrowserRawElementCandidate) -> tuple[float, float, float]:
        score = 0.0
        if item.visible:
            score += 2.5
        if item.in_viewport:
            score += 1.5
        if item.enabled and not item.disabled:
            score += 1.0
        if item.is_form_control:
            score += 4.0
        if item.is_text_input:
            score += 3.5
        if item.is_search_like:
            score += 2.5
        if item.is_primary_action:
            score += 2.0
        if item.kind in {"input", "textarea", "select"}:
            score += 2.5
        if item.label_text:
            score += 1.5
        if item.placeholder:
            score += 1.0
        if item.ax_name or item.aria_label:
            score += 0.8
        if item.section_hint:
            score += 0.5
        if item.landmark_hint in {"form", "main", "search"}:
            score += 2.0
        if item.landmark_hint == "nav":
            score -= 3.0
        if item.top_offset <= 130 and item.landmark_hint in {"header", "nav"}:
            score -= 4.0
        if item.top_offset <= 130 and item.kind in {"link", "button"} and not item.is_form_control:
            score -= 1.2

        lowered_blob = " ".join(
            [
                item.text,
                item.label_text,
                item.placeholder,
                item.aria_label,
                item.ax_name,
                item.section_hint,
            ]
        ).lower()
        task_agnostic_form_terms = [
            "search",
            "查询",
            "搜索",
            "出发",
            "到达",
            "目的",
            "日期",
            "city",
            "airport",
            "destination",
            "departure",
            "origin",
        ]
        if any(term in lowered_blob for term in task_agnostic_form_terms):
            score += 3.0

        center_bias = -abs((item.left_offset + (item.width / 2.0)) - 640.0) / 1000.0
        vertical_bias = -abs(item.top_offset - 260.0) / 1200.0
        return (score, center_bias, vertical_bias)

    ranked = sorted(candidates, key=_score, reverse=True)
    deduped: list[BrowserRawElementCandidate] = []
    seen_signatures: set[tuple[str, tuple[str, ...], str, str, int, int]] = set()
    for item in ranked:
        signature = (
            item.selector,
            tuple(item.frame_path),
            (item.text or item.label_text or item.aria_label or item.ax_name).strip().lower(),
            item.tag,
            int(item.top_offset),
            int(item.left_offset),
        )
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        deduped.append(item)
    return deduped


def _candidate_to_interactive(item: BrowserRawElementCandidate, index: int) -> BrowserInteractiveElement:
    semantic_score = _semantic_score(item)
    return BrowserInteractiveElement(
        index=index,
        kind=item.kind if item.kind in {"link", "button", "input", "textarea", "select", "control"} else "control",
        tag=item.tag,
        selector=item.selector,
        frame_path=list(item.frame_path),
        text=item.text,
        label_text=item.label_text,
        href=item.href,
        role=item.role,
        ax_role=item.ax_role,
        ax_name=item.ax_name,
        input_type=item.input_type,
        name=item.name,
        placeholder=item.placeholder,
        title=item.title,
        aria_label=item.aria_label,
        enabled=item.enabled,
        visible=item.visible,
        in_viewport=item.in_viewport,
        disabled=item.disabled,
        checked=item.checked,
        expanded=item.expanded,
        pressed=item.pressed,
        iframe_hint=f"iframe-depth={len(item.frame_path)}" if item.frame_path else "",
        section_hint=item.section_hint,
        landmark_hint=item.landmark_hint,
        semantic_group=_semantic_group_for(item),
        semantic_score=semantic_score,
        bounds=BrowserElementBounds(
            x=item.left_offset,
            y=item.top_offset,
            width=item.width,
            height=item.height,
        ),
    )


def _semantic_group_for(item: BrowserRawElementCandidate) -> str:
    lowered_blob = " ".join([item.text, item.label_text, item.placeholder, item.aria_label, item.ax_name, item.section_hint]).lower()
    if any(term in lowered_blob for term in ["search", "查询", "搜索"]):
        return "search"
    if any(term in lowered_blob for term in ["出发", "departure", "origin"]):
        return "origin"
    if any(term in lowered_blob for term in ["到达", "目的", "destination", "arrival"]):
        return "destination"
    if any(term in lowered_blob for term in ["日期", "date", "时间", "calendar"]):
        return "date"
    if item.landmark_hint == "nav":
        return "navigation"
    if item.landmark_hint == "dialog":
        return "dialog"
    if item.is_form_control:
        return "form"
    return "generic"


def _semantic_score(item: BrowserRawElementCandidate) -> float:
    score = 0.0
    if item.is_form_control:
        score += 4.0
    if item.is_text_input:
        score += 2.0
    if item.is_search_like:
        score += 1.5
    if item.in_viewport:
        score += 1.0
    if item.landmark_hint in {"main", "form", "search"}:
        score += 1.0
    if item.landmark_hint == "nav":
        score -= 2.0
    return round(score, 2)


def _build_semantic_groups(interactive_elements: list[BrowserInteractiveElement]) -> list[BrowserSemanticGroup]:
    grouped: dict[str, list[int]] = {}
    labels = {
        "search": "Search controls",
        "origin": "Origin/departure controls",
        "destination": "Destination controls",
        "date": "Date controls",
        "form": "Form controls",
        "dialog": "Dialog controls",
        "navigation": "Navigation controls",
        "generic": "Other interactive controls",
    }
    for item in interactive_elements:
        grouped.setdefault(item.semantic_group or "generic", []).append(item.index)

    ordered_kinds = ["origin", "destination", "date", "search", "form", "dialog", "navigation", "generic"]
    groups: list[BrowserSemanticGroup] = []
    for kind in ordered_kinds:
        indexes = grouped.get(kind)
        if indexes:
            groups.append(BrowserSemanticGroup(kind=kind, label=labels.get(kind, kind), element_indexes=indexes[:8]))
    return groups


def _build_prioritized_hints(
    main_document: BrowserRawDocumentSnapshot,
    interactive_elements: list[BrowserInteractiveElement],
    semantic_groups: list[BrowserSemanticGroup],
) -> list[str]:
    hints: list[str] = []
    if main_document.headings:
        hints.append(f"Visible headings: {', '.join(main_document.headings[:3])}")
    if semantic_groups:
        top_group = semantic_groups[0]
        hints.append(f"Top semantic group: {top_group.label} -> indexes {top_group.element_indexes[:4]}")
    top_form_controls = [item for item in interactive_elements if item.semantic_group in {"origin", "destination", "date", "search", "form"}]
    if top_form_controls:
        labels = []
        for item in top_form_controls[:5]:
            label = item.text or item.label_text or item.placeholder or item.aria_label or item.ax_name or item.tag
            labels.append(f"[{item.index}] {label}")
        hints.append(f"Likely task-relevant controls: {', '.join(labels)}")
    if main_document.landmarks:
        hints.append(f"Landmarks: {', '.join(main_document.landmarks[:5])}")
    return hints[:6]


def _build_frame_summaries(frame_documents: list[BrowserRawDocumentSnapshot]) -> list[str]:
    summaries: list[str] = []
    for document in frame_documents:
        parts = [f"iframe: {document.frame_name} ({document.frame_url or 'about:blank'})"]
        if document.headings:
            parts.append(f"headings={', '.join(document.headings[:2])}")
        if document.landmarks:
            parts.append(f"landmarks={', '.join(document.landmarks[:3])}")
        summaries.append(" | ".join(parts))
    return summaries[:12]


def _page_info_from_raw(raw_payload: dict[str, int]) -> BrowserPageInfo:
    return BrowserPageInfo(
        viewport_width=int(raw_payload.get("viewport_width") or 1280),
        viewport_height=int(raw_payload.get("viewport_height") or 720),
        scroll_x=int(raw_payload.get("scroll_x") or 0),
        scroll_y=int(raw_payload.get("scroll_y") or 0),
        pixels_above=int(raw_payload.get("pixels_above") or 0),
        pixels_below=max(int(raw_payload.get("pixels_below") or 0), 0),
    )


def _render_dom_summary(
    *,
    title: str,
    url: str,
    text_content: str,
    interactive_elements: list[BrowserInteractiveElement],
    semantic_groups: list[BrowserSemanticGroup],
    prioritized_hints: list[str],
    page_info: BrowserPageInfo,
    iframe_summaries: list[str],
    recent_events: list[str],
) -> str:
    lines = [
        f"Title: {title}",
        f"URL: {url}",
        f"Scroll: y={page_info.scroll_y}, below={page_info.pixels_below}px",
    ]
    if prioritized_hints:
        lines.append("Planner hints:")
        for item in prioritized_hints[:5]:
            lines.append(f"- {item}")
    if semantic_groups:
        lines.append("Semantic groups:")
        for group in semantic_groups[:6]:
            lines.append(f"- {group.label}: {group.element_indexes}")
    if iframe_summaries:
        lines.append("Frames:")
        for item in iframe_summaries[:8]:
            lines.append(f"- {item}")
    if recent_events:
        lines.append("Recent browser events:")
        for item in recent_events[-6:]:
            lines.append(f"- {item}")

    lines.extend(
        [
            "Main text:",
            truncate_content(text_content or "(no visible text)", max_chars=2200),
            f"Priority interactive elements ({len(interactive_elements)} shown):",
        ]
    )
    if interactive_elements:
        for item in interactive_elements:
            label = " / ".join(
                part
                for part in [
                    item.semantic_group,
                    item.kind,
                    item.tag,
                    item.role or item.ax_role,
                    item.input_type,
                    item.label_text,
                    item.placeholder,
                    item.aria_label or item.ax_name,
                    item.text,
                ]
                if part
            )
            if item.href:
                label = f"{label} -> {item.href}" if label else item.href

            suffix_parts: list[str] = []
            if item.frame_path:
                suffix_parts.append(f"frame-depth={len(item.frame_path)}")
            if item.section_hint:
                suffix_parts.append(f"section={item.section_hint}")
            if item.landmark_hint:
                suffix_parts.append(f"landmark={item.landmark_hint}")
            if item.disabled:
                suffix_parts.append("disabled")
            if item.checked:
                suffix_parts.append("checked")
            if item.expanded:
                suffix_parts.append("expanded")
            if item.pressed:
                suffix_parts.append("pressed")
            if not item.in_viewport:
                suffix_parts.append("offscreen")
            suffix_parts.append(f"score={item.semantic_score}")
            bounds = item.bounds
            if bounds.width > 0 and bounds.height > 0:
                suffix_parts.append(f"box=({int(bounds.x)},{int(bounds.y)},{int(bounds.width)}x{int(bounds.height)})")

            suffix = f" [{' | '.join(suffix_parts)}]" if suffix_parts else ""
            lines.append(f"- [{item.index}] {label or '(unnamed element)'}{suffix}")
    else:
        lines.append("- none")

    return truncate_content("\n".join(lines), max_chars=4200)


def _compute_observation_fingerprint(
    url: str,
    title: str,
    text_content: str,
    interactive_elements: list[BrowserInteractiveElement],
    iframe_summaries: list[str],
    prioritized_hints: list[str],
) -> str:
    compact_elements = [
        {
            "i": item.index,
            "s": item.selector,
            "f": item.frame_path,
            "t": item.tag,
            "r": item.role or item.ax_role,
            "g": item.semantic_group,
            "n": item.text or item.label_text or item.ax_name or item.aria_label,
            "p": item.placeholder,
            "y": int(item.bounds.y),
            "x": int(item.bounds.x),
        }
        for item in interactive_elements
    ]
    payload = json.dumps(
        {
            "url": url,
            "title": title,
            "text": text_content[:1200],
            "elements": compact_elements,
            "frames": iframe_summaries,
            "hints": prioritized_hints,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()[:16]
