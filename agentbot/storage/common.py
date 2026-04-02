"""Shared storage helpers."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

AGENTBOT_META_KEY = "_agentbot"


def new_prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
