"""Lightweight browser loop detection inspired by browser-use."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_page_fingerprint(*, url: str, dom_summary: str, element_count: int) -> str:
    payload = f"{url}|{element_count}|{_short_hash(dom_summary)}"
    return _short_hash(payload)


def compute_action_hash(action: dict[str, Any]) -> str:
    normalized = {
        "action_type": action.get("action_type"),
        "url": action.get("url"),
        "element_index": action.get("element_index"),
        "text": str(action.get("text") or "").strip().lower(),
        "direction": action.get("direction"),
        "amount": action.get("amount"),
        "tab_id": action.get("tab_id"),
    }
    return _short_hash(json.dumps(normalized, ensure_ascii=False, sort_keys=True))


def summarize_loop_signal(
    *,
    repeated_action_count: int,
    stagnant_count: int,
) -> str | None:
    if repeated_action_count >= 3 and stagnant_count >= 2:
        return (
            f"检测到可能循环：最近动作已重复 {repeated_action_count} 次，"
            f"且页面连续 {stagnant_count + 1} 次没有明显变化。"
        )
    if repeated_action_count >= 4:
        return f"检测到可能循环：最近动作已重复 {repeated_action_count} 次。"
    if stagnant_count >= 3:
        return f"检测到页面停滞：页面连续 {stagnant_count + 1} 次没有明显变化。"
    return None


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:12]
