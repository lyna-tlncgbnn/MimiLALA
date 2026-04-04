"""Session registry and lifecycle helpers for browser runtime sessions."""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from agentbot.browser.runtime import BrowserClosedEvent
from agentbot.storage.paths import workspace_root

if TYPE_CHECKING:
    from agentbot.browser.session import BrowserRuntimeSession


_SESSION_REGISTRY: dict[str, "BrowserRuntimeSession"] = {}


def register_runtime_session(session_id: str, runtime: "BrowserRuntimeSession") -> None:
    _SESSION_REGISTRY[session_id] = runtime


def get_runtime_session(session_id: str) -> "BrowserRuntimeSession":
    runtime = _SESSION_REGISTRY.get(session_id)
    if runtime is None:
        raise ValueError(f"Browser session not found: {session_id}")
    return runtime


def discard_runtime_session(session_id: str) -> "BrowserRuntimeSession | None":
    return _SESSION_REGISTRY.pop(session_id, None)


def browser_output_dir(base_dir: Path | None = None) -> Path:
    path = base_dir or (workspace_root() / "browser_artifacts")
    path.mkdir(parents=True, exist_ok=True)
    return path


def browser_profiles_dir(base_dir: Path | None = None) -> Path:
    path = base_dir or (workspace_root() / "browser_profiles")
    path.mkdir(parents=True, exist_ok=True)
    return path


def browser_session_artifacts_dir(session_id: str, *, base_dir: Path | None = None) -> Path:
    path = browser_output_dir(base_dir) / session_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def browser_download_dir(session_id: str, *, base_dir: Path | None = None) -> Path:
    path = browser_session_artifacts_dir(session_id, base_dir=base_dir) / "downloads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cleanup_orphan_browser_profiles(
    temp_profiles_dir: str | None,
    *,
    resolve_optional_dir: Callable[..., Path],
) -> None:
    profiles_root = resolve_optional_dir(temp_profiles_dir, default=workspace_root() / "browser_profiles")
    active_dirs = {
        runtime.temp_profile_dir.resolve()
        for runtime in _SESSION_REGISTRY.values()
        if runtime.temp_profile_dir is not None
    }
    for entry in profiles_root.iterdir():
        if not entry.is_dir() or not entry.name.startswith("browser_session_"):
            continue
        try:
            resolved = entry.resolve()
        except OSError:
            resolved = entry
        if resolved in active_dirs:
            continue
        shutil.rmtree(entry, ignore_errors=True)


def close_runtime_session(
    runtime: "BrowserRuntimeSession",
    *,
    terminate_process: Callable[[Any], None],
) -> None:
    if runtime.event_bus is not None:
        runtime.event_bus.emit(BrowserClosedEvent(created_at=time.time(), reason="close_browser_session"))

    try:
        runtime.context.close()
    except Exception:
        pass

    if runtime.browser is not None:
        try:
            runtime.browser.close()
        except Exception:
            pass

    if runtime.browser_process is not None:
        terminate_process(runtime.browser_process)

    try:
        runtime.playwright.stop()
    except Exception:
        pass

    if runtime.temp_profile_dir and runtime.temp_profile_dir.exists():
        shutil.rmtree(runtime.temp_profile_dir, ignore_errors=True)
