"""Browser session helpers with system-browser and Playwright modes."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from uuid import uuid4

from playwright.sync_api import Browser, BrowserContext, Download, Dialog, Page, Playwright, sync_playwright

from agentbot.browser.session_manager import (
    browser_download_dir,
    browser_session_artifacts_dir,
    cleanup_orphan_browser_profiles,
    close_runtime_session,
    discard_runtime_session,
    get_runtime_session,
    register_runtime_session,
)
from agentbot.browser.runtime import (
    BrowserClosedEvent,
    BrowserStateRequestEvent,
    BrowserRuntimeEventBus,
    DialogHandledEvent,
    NavigationCompletedEvent,
    PageClosedEvent,
    PageCreatedEvent,
)
from agentbot.browser.runtime.watchdogs import (
    DOMWatchdog,
    DefaultActionWatchdog,
    DialogsWatchdog,
    DownloadsWatchdog,
    LifecycleWatchdog,
    NavigationWatchdog,
    PopupsWatchdog,
)
from agentbot.storage.paths import repo_root, workspace_root


@dataclass(slots=True)
class BrowserSessionState:
    session_id: str
    current_url: str
    title: str
    mode: str
    headless: bool
    viewport_width: int | None = None
    viewport_height: int | None = None
    window_width: int | None = None
    window_height: int | None = None
    no_viewport: bool = False
    start_maximized: bool = False
    channel: str | None = None
    executable_path: str | None = None
    user_data_dir: str | None = None
    profile_directory: str | None = None
    temp_profile_dir: str | None = None
    cdp_url: str | None = None
    artifacts_dir: str = ""
    downloads_dir: str = ""


@dataclass(slots=True)
class BrowserRuntimeSession:
    session_id: str
    mode: str
    playwright: Playwright
    browser: Browser | None
    context: BrowserContext
    page: Page
    artifacts_dir: Path
    downloads_dir: Path
    executable_path: str | None = None
    user_data_dir: Path | None = None
    profile_directory: str | None = None
    temp_profile_dir: Path | None = None
    cdp_url: str | None = None
    browser_process: subprocess.Popen[bytes] | None = None
    downloaded_files: list[str] = field(default_factory=list)
    recent_events: list[dict[str, str]] = field(default_factory=list)
    closed_popup_messages: list[str] = field(default_factory=list)
    observed_page_ids: set[int] = field(default_factory=set)
    active_downloads: dict[str, dict[str, Any]] = field(default_factory=dict)
    latest_download_id: str | None = None
    cached_raw_observation: Any | None = None
    cached_browser_state: Any | None = None
    cached_selector_map: dict[int, Any] = field(default_factory=dict)
    cached_screenshot_path: Path | None = None
    cached_observation_at: float | None = None
    event_bus: BrowserRuntimeEventBus | None = None
    dom_watchdog: DOMWatchdog | None = None
    downloads_watchdog: DownloadsWatchdog | None = None
    popups_watchdog: PopupsWatchdog | None = None
    dialogs_watchdog: DialogsWatchdog | None = None
    navigation_watchdog: NavigationWatchdog | None = None
    lifecycle_watchdog: LifecycleWatchdog | None = None
    default_action_watchdog: DefaultActionWatchdog | None = None
    download_start_timeout_seconds: float = 4.0
    download_complete_timeout_seconds: float = 30.0


def start_browser_session(
    *,
    initial_url: str,
    title: str,
    mode: str = "system",
    headless: bool = True,
    viewport_width: int = 1280,
    viewport_height: int = 720,
    window_width: int = 1440,
    window_height: int = 900,
    no_viewport: bool = False,
    start_maximized: bool = False,
    executable_path: str | None = None,
    user_data_dir: str | None = None,
    profile_directory: str | None = None,
    temp_profiles_dir: str | None = None,
    copy_local_profile: bool = True,
    artifacts_dir: str | None = None,
    downloads_dir: str | None = None,
    channel: str | None = None,
    download_start_timeout_seconds: float = 4.0,
    download_complete_timeout_seconds: float = 30.0,
) -> BrowserSessionState:
    if mode == "system":
        cleanup_orphan_browser_profiles(
            temp_profiles_dir,
            resolve_optional_dir=_resolve_optional_dir,
        )
    session_id = f"browser_session_{uuid4().hex}"
    runtime = _create_runtime_session(
        session_id=session_id,
        initial_url=initial_url,
        mode=mode,
        headless=headless,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        window_width=window_width,
        window_height=window_height,
        no_viewport=no_viewport,
        start_maximized=start_maximized,
        executable_path=executable_path,
        user_data_dir=user_data_dir,
        profile_directory=profile_directory,
        temp_profiles_dir=temp_profiles_dir,
        copy_local_profile=copy_local_profile,
        artifacts_dir=artifacts_dir,
        downloads_dir=downloads_dir,
        channel=channel,
        download_start_timeout_seconds=download_start_timeout_seconds,
        download_complete_timeout_seconds=download_complete_timeout_seconds,
    )
    register_runtime_session(session_id, runtime)
    page_title = runtime.page.title() or title
    return BrowserSessionState(
        session_id=session_id,
        current_url=runtime.page.url or initial_url,
        title=page_title,
        mode=runtime.mode,
        headless=headless,
        viewport_width=None if no_viewport else viewport_width,
        viewport_height=None if no_viewport else viewport_height,
        window_width=window_width,
        window_height=window_height,
        no_viewport=no_viewport,
        start_maximized=start_maximized,
        channel=channel,
        executable_path=runtime.executable_path,
        user_data_dir=str(runtime.user_data_dir) if runtime.user_data_dir else None,
        profile_directory=runtime.profile_directory,
        temp_profile_dir=str(runtime.temp_profile_dir) if runtime.temp_profile_dir else None,
        cdp_url=runtime.cdp_url,
        artifacts_dir=str(runtime.artifacts_dir),
        downloads_dir=str(runtime.downloads_dir),
    )

def dispatch_runtime_action(runtime: BrowserRuntimeSession, event) -> Any:
    if runtime.event_bus is None:
        raise ValueError("Browser runtime event bus is not initialized.")
    return runtime.event_bus.request(event)


def request_browser_state(
    runtime: BrowserRuntimeSession,
    *,
    include_screenshot: bool = True,
    include_recent_events: bool = True,
):
    if runtime.event_bus is None:
        raise ValueError("Browser runtime event bus is not initialized.")
    response = runtime.event_bus.request(
        BrowserStateRequestEvent(
            created_at=time.time(),
            include_screenshot=include_screenshot,
            include_recent_events=include_recent_events,
        )
    )
    if response is None:
        raise ValueError("Browser state request did not return a browser state summary.")
    return response


def close_browser_session(session_id: str) -> None:
    runtime = discard_runtime_session(session_id)
    if runtime is None:
        return
    close_runtime_session(runtime, terminate_process=_terminate_process)


def _create_runtime_session(
    *,
    session_id: str,
    initial_url: str,
    mode: str,
    headless: bool,
    viewport_width: int,
    viewport_height: int,
    window_width: int,
    window_height: int,
    no_viewport: bool,
    start_maximized: bool,
    executable_path: str | None,
    user_data_dir: str | None,
    profile_directory: str | None,
    temp_profiles_dir: str | None,
    copy_local_profile: bool,
    artifacts_dir: str | None,
    downloads_dir: str | None,
    channel: str | None,
    download_start_timeout_seconds: float,
    download_complete_timeout_seconds: float,
) -> BrowserRuntimeSession:
    if mode == "system":
        return _create_system_runtime_session(
            session_id=session_id,
            initial_url=initial_url,
            headless=headless,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            window_width=window_width,
            window_height=window_height,
            no_viewport=no_viewport,
            start_maximized=start_maximized,
            executable_path=executable_path,
            user_data_dir=user_data_dir,
            profile_directory=profile_directory,
            temp_profiles_dir=temp_profiles_dir,
            copy_local_profile=copy_local_profile,
            artifacts_dir=artifacts_dir,
            downloads_dir=downloads_dir,
            channel=channel,
            download_start_timeout_seconds=download_start_timeout_seconds,
            download_complete_timeout_seconds=download_complete_timeout_seconds,
        )

    return _create_playwright_runtime_session(
        session_id=session_id,
        initial_url=initial_url,
        headless=headless,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        window_width=window_width,
        window_height=window_height,
        no_viewport=no_viewport,
        start_maximized=start_maximized,
        artifacts_dir=artifacts_dir,
        downloads_dir=downloads_dir,
        channel=channel,
        download_start_timeout_seconds=download_start_timeout_seconds,
        download_complete_timeout_seconds=download_complete_timeout_seconds,
    )


def _create_playwright_runtime_session(
    *,
    session_id: str,
    initial_url: str,
    headless: bool,
    viewport_width: int,
    viewport_height: int,
    window_width: int,
    window_height: int,
    no_viewport: bool,
    start_maximized: bool,
    artifacts_dir: str | None,
    downloads_dir: str | None,
    channel: str | None,
    download_start_timeout_seconds: float,
    download_complete_timeout_seconds: float,
) -> BrowserRuntimeSession:
    playwright = sync_playwright().start()
    launch_args = [f"--window-size={window_width},{window_height}"]
    if start_maximized:
        launch_args.append("--start-maximized")

    launch_kwargs: dict[str, object] = {
        "headless": headless,
        "args": launch_args,
    }
    if channel:
        launch_kwargs["channel"] = channel

    browser = playwright.chromium.launch(**launch_kwargs)
    artifacts_root = _resolve_optional_dir(artifacts_dir, default=workspace_root() / "browser_artifacts")
    session_artifacts_dir = browser_session_artifacts_dir(session_id, base_dir=artifacts_root)
    session_downloads_dir = _resolve_downloads_dir(
        session_id=session_id,
        artifacts_root=artifacts_root,
        downloads_dir=downloads_dir,
    )

    context_kwargs: dict[str, object] = {"accept_downloads": True}
    if no_viewport:
        context_kwargs["no_viewport"] = True
    else:
        context_kwargs["viewport"] = {"width": viewport_width, "height": viewport_height}

    context = browser.new_context(**context_kwargs)
    page = context.new_page()
    runtime = BrowserRuntimeSession(
        session_id=session_id,
        mode="playwright",
        playwright=playwright,
        browser=browser,
        context=context,
        page=page,
        artifacts_dir=session_artifacts_dir,
        downloads_dir=session_downloads_dir,
        executable_path=None,
        user_data_dir=None,
        profile_directory=None,
        temp_profile_dir=None,
        cdp_url=None,
        download_start_timeout_seconds=download_start_timeout_seconds,
        download_complete_timeout_seconds=download_complete_timeout_seconds,
    )
    _initialize_runtime_watchdogs(runtime)
    _attach_context_handlers(runtime)
    _attach_existing_pages(runtime)
    _navigate_initial_page(runtime.page, initial_url)
    return runtime


def _create_system_runtime_session(
    *,
    session_id: str,
    initial_url: str,
    headless: bool,
    viewport_width: int,
    viewport_height: int,
    window_width: int,
    window_height: int,
    no_viewport: bool,
    start_maximized: bool,
    executable_path: str | None,
    user_data_dir: str | None,
    profile_directory: str | None,
    temp_profiles_dir: str | None,
    copy_local_profile: bool,
    artifacts_dir: str | None,
    downloads_dir: str | None,
    channel: str | None,
    download_start_timeout_seconds: float,
    download_complete_timeout_seconds: float,
) -> BrowserRuntimeSession:
    resolved_executable = _resolve_system_browser_executable(executable_path, channel)
    resolved_user_data_dir = _resolve_system_user_data_dir(user_data_dir, channel, resolved_executable)
    resolved_profile_directory = _resolve_profile_directory(resolved_user_data_dir, profile_directory)
    artifacts_root = _resolve_optional_dir(artifacts_dir, default=workspace_root() / "browser_artifacts")
    session_artifacts_dir = browser_session_artifacts_dir(session_id, base_dir=artifacts_root)
    session_downloads_dir = _resolve_downloads_dir(
        session_id=session_id,
        artifacts_root=artifacts_root,
        downloads_dir=downloads_dir,
    )
    profiles_root = _resolve_optional_dir(temp_profiles_dir, default=workspace_root() / "browser_profiles")
    temp_profile_dir = profiles_root / session_id
    _prepare_temp_profile_dir(
        source_user_data_dir=resolved_user_data_dir,
        profile_directory=resolved_profile_directory,
        destination=temp_profile_dir,
        copy_local_profile=copy_local_profile,
        downloads_dir=session_downloads_dir,
    )

    debug_port = _find_free_port()
    browser_process = _launch_system_browser_process(
        executable_path=resolved_executable,
        user_data_dir=temp_profile_dir,
        profile_directory=resolved_profile_directory,
        headless=headless,
        window_width=window_width,
        window_height=window_height,
        start_maximized=start_maximized,
        debug_port=debug_port,
    )
    cdp_url = _wait_for_cdp_url(debug_port)

    playwright = sync_playwright().start()
    browser = playwright.chromium.connect_over_cdp(cdp_url)
    _configure_browser_download_behavior(browser=browser, downloads_dir=session_downloads_dir)
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.pages[0] if context.pages else context.new_page()
    if no_viewport:
        try:
            page.set_viewport_size({"width": window_width, "height": window_height})
        except Exception:
            pass
    else:
        try:
            page.set_viewport_size({"width": viewport_width, "height": viewport_height})
        except Exception:
            pass
    runtime = BrowserRuntimeSession(
        session_id=session_id,
        mode="system",
        playwright=playwright,
        browser=browser,
        context=context,
        page=page,
        artifacts_dir=session_artifacts_dir,
        downloads_dir=session_downloads_dir,
        executable_path=resolved_executable,
        user_data_dir=resolved_user_data_dir,
        profile_directory=resolved_profile_directory,
        temp_profile_dir=temp_profile_dir,
        cdp_url=cdp_url,
        browser_process=browser_process,
        download_start_timeout_seconds=download_start_timeout_seconds,
        download_complete_timeout_seconds=download_complete_timeout_seconds,
    )
    _initialize_runtime_watchdogs(runtime)
    _attach_context_handlers(runtime)
    _attach_existing_pages(runtime)
    _navigate_initial_page(runtime.page, initial_url)
    return runtime


def record_runtime_event(
    runtime: BrowserRuntimeSession,
    event_type: str,
    message: str,
    *,
    dedupe_recent: bool = False,
) -> None:
    if dedupe_recent:
        for event in runtime.recent_events[-8:]:
            if event.get("type") == event_type and event.get("message") == message:
                return
    runtime.recent_events.append(
        {
            "type": event_type,
            "message": message,
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
    )
    if len(runtime.recent_events) > 40:
        del runtime.recent_events[:-40]


def wait_for_runtime_event(
    runtime: BrowserRuntimeSession,
    *,
    since_index: int,
    event_types: set[str],
    timeout_seconds: float,
    poll_interval_seconds: float = 0.1,
) -> list[dict[str, str]]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        matches = [event for event in runtime.recent_events[since_index:] if event.get("type") in event_types]
        if matches:
            return matches
        time.sleep(poll_interval_seconds)
    return [event for event in runtime.recent_events[since_index:] if event.get("type") in event_types]


def _initialize_runtime_watchdogs(runtime: BrowserRuntimeSession) -> None:
    runtime.event_bus = BrowserRuntimeEventBus()
    runtime.dom_watchdog = DOMWatchdog(runtime)
    runtime.downloads_watchdog = DownloadsWatchdog(runtime)
    runtime.popups_watchdog = PopupsWatchdog(runtime)
    runtime.dialogs_watchdog = DialogsWatchdog(runtime)
    runtime.navigation_watchdog = NavigationWatchdog(runtime)
    runtime.lifecycle_watchdog = LifecycleWatchdog(runtime)
    runtime.default_action_watchdog = DefaultActionWatchdog(runtime)
    runtime.dom_watchdog.register()
    runtime.downloads_watchdog.register()
    runtime.popups_watchdog.register()
    runtime.dialogs_watchdog.register()
    runtime.navigation_watchdog.register()
    runtime.lifecycle_watchdog.register()
    runtime.default_action_watchdog.register()


def _attach_existing_pages(runtime: BrowserRuntimeSession) -> None:
    for page in runtime.context.pages:
        _attach_page_handlers(runtime, page)


def _attach_context_handlers(runtime: BrowserRuntimeSession) -> None:
    def _on_page(page: Page) -> None:
        _attach_page_handlers(runtime, page)
        if runtime.event_bus is not None:
            runtime.event_bus.emit(PageCreatedEvent(created_at=time.time(), page=page))

    runtime.context.on("page", _on_page)
    if runtime.browser is not None:
        def _on_disconnected() -> None:
            if runtime.event_bus is not None:
                runtime.event_bus.emit(BrowserClosedEvent(created_at=time.time(), reason="browser_disconnected"))

        runtime.browser.on("disconnected", _on_disconnected)


def _attach_page_handlers(runtime: BrowserRuntimeSession, page: Page) -> None:
    page_id = id(page)
    if page_id in runtime.observed_page_ids:
        return
    runtime.observed_page_ids.add(page_id)

    def _on_dialog(dialog: Dialog) -> None:
        if runtime.event_bus is not None:
            runtime.event_bus.emit(
                DialogHandledEvent(
                    created_at=time.time(),
                    dialog_type=dialog.type,
                    message=dialog.message,
                )
            )
        else:
            message = f"{dialog.type}: {dialog.message}"
            runtime.closed_popup_messages.append(message)
            record_runtime_event(runtime, "dialog", f"Handled dialog {message}")
        try:
            dialog.dismiss()
        except Exception:
            pass

    def _on_download(download: Download) -> None:
        if runtime.event_bus is not None and runtime.downloads_watchdog is not None:
            event = runtime.downloads_watchdog.prepare_download_event(download=download, page=page)
            runtime.event_bus.emit(event)
            return
        try:
            suggested = download.suggested_filename or "download"
            destination = _unique_download_path(runtime.downloads_dir, suggested)
            download.save_as(str(destination))
            runtime.downloaded_files.append(str(destination))
            record_runtime_event(runtime, "download", f"Downloaded file: {destination.name} -> {destination}")
        except Exception as exc:
            record_runtime_event(runtime, "download_error", f"Download handling failed: {exc}")

    def _on_frame_navigated(frame) -> None:
        if frame == page.main_frame:
            if runtime.event_bus is not None:
                runtime.event_bus.emit(
                    NavigationCompletedEvent(
                        created_at=time.time(),
                        url=page.url or "about:blank",
                        page=page,
                    )
                )
            else:
                record_runtime_event(runtime, "navigation", f"Navigated to {page.url or 'about:blank'}")

    def _on_close() -> None:
        if runtime.event_bus is not None:
            runtime.event_bus.emit(
                PageClosedEvent(
                    created_at=time.time(),
                    page_url=page.url or "about:blank",
                    page=page,
                    is_active_page=(runtime.page == page),
                )
            )
        else:
            record_runtime_event(runtime, "page_closed", f"Closed page: {page.url or 'about:blank'}")

    page.on("dialog", _on_dialog)
    page.on("download", _on_download)
    page.on("framenavigated", _on_frame_navigated)
    page.on("close", _on_close)


def _unique_download_path(directory: Path, filename: str) -> Path:
    target = directory / filename
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    counter = 1
    while True:
        candidate = directory / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _resolve_optional_dir(raw_value: str | None, *, default: Path) -> Path:
    if not raw_value:
        path = default
    else:
        path = Path(raw_value)
        if not path.is_absolute():
            path = repo_root() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_downloads_dir(*, session_id: str, artifacts_root: Path, downloads_dir: str | None) -> Path:
    if downloads_dir:
        return _resolve_optional_dir(downloads_dir, default=workspace_root() / "browser_downloads")
    return browser_download_dir(session_id, base_dir=artifacts_root)


def _navigate_initial_page(page: Page, initial_url: str) -> None:
    if initial_url and initial_url != "about:blank":
        page.goto(initial_url, wait_until="domcontentloaded", timeout=30000)
    else:
        page.goto("about:blank")


def _resolve_system_browser_executable(executable_path: str | None, channel: str | None) -> str:
    if executable_path:
        path = Path(executable_path).expanduser()
        if not path.is_absolute():
            path = repo_root() / path
        if not path.exists():
            raise ValueError(f"Configured browser.executable_path does not exist: {path}")
        return str(path)

    candidates = _browser_executable_candidates(channel)
    for candidate in candidates:
        path = Path(os.path.expandvars(candidate)).expanduser()
        if path.exists():
            return str(path)

    raise ValueError(
        "Could not find a local Chrome/Edge executable. Configure browser.executable_path or browser.channel."
    )


def _browser_executable_candidates(channel: str | None) -> list[str]:
    if os.name != "nt":
        return []

    chrome_candidates = [
        r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe",
        r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe",
        r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
    ]
    edge_candidates = [
        r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe",
        r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe",
        r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe",
    ]
    if channel and "edge" in channel.lower():
        return [*edge_candidates, *chrome_candidates]
    return [*chrome_candidates, *edge_candidates]


def _resolve_system_user_data_dir(user_data_dir: str | None, channel: str | None, executable_path: str) -> Path:
    if user_data_dir:
        path = Path(user_data_dir).expanduser()
        if not path.is_absolute():
            path = repo_root() / path
        if not path.exists():
            raise ValueError(f"Configured browser.user_data_dir does not exist: {path}")
        return path

    lower_executable = executable_path.lower()
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    if channel and "edge" in channel.lower() or "msedge" in lower_executable or "edge" in lower_executable:
        path = local_app_data / "Microsoft" / "Edge" / "User Data"
    else:
        path = local_app_data / "Google" / "Chrome" / "User Data"

    if not path.exists():
        raise ValueError(f"Could not find local browser user data directory: {path}")
    return path


def _resolve_profile_directory(user_data_dir: Path, requested: str | None) -> str:
    if requested:
        return requested

    profiles = _list_local_profiles(user_data_dir)
    if any(profile["directory"] == "Default" for profile in profiles):
        return "Default"
    if profiles:
        return profiles[0]["directory"]
    return "Default"


def _list_local_profiles(user_data_dir: Path) -> list[dict[str, str]]:
    local_state_path = user_data_dir / "Local State"
    if not local_state_path.exists():
        return []
    try:
        payload = json.loads(local_state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    info_cache = payload.get("profile", {}).get("info_cache", {})
    profiles: list[dict[str, str]] = []
    if not isinstance(info_cache, dict):
        return profiles

    for directory, info in info_cache.items():
        if not isinstance(info, dict):
            continue
        profiles.append(
            {
                "directory": directory,
                "name": str(info.get("name", directory)),
            }
        )
    return profiles


def _prepare_temp_profile_dir(
    *,
    source_user_data_dir: Path,
    profile_directory: str,
    destination: Path,
    copy_local_profile: bool,
    downloads_dir: Path,
) -> None:
    if destination.exists():
        shutil.rmtree(destination, ignore_errors=True)
    destination.mkdir(parents=True, exist_ok=True)

    profile_source = source_user_data_dir / profile_directory
    profile_destination = destination / profile_directory

    if copy_local_profile and profile_source.exists():
        shutil.copytree(profile_source, profile_destination, dirs_exist_ok=True)
        local_state_source = source_user_data_dir / "Local State"
        if local_state_source.exists():
            shutil.copy2(local_state_source, destination / "Local State")
    else:
        profile_destination.mkdir(parents=True, exist_ok=True)

    _apply_download_preferences(profile_destination, downloads_dir)


def _apply_download_preferences(profile_directory: Path, downloads_dir: Path) -> None:
    preferences_path = profile_directory / "Preferences"
    payload: dict[str, Any]
    if preferences_path.exists():
        try:
            payload = json.loads(preferences_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
    else:
        payload = {}

    download_settings = payload.get("download")
    if not isinstance(download_settings, dict):
        download_settings = {}
        payload["download"] = download_settings
    download_settings.update(
        {
            "default_directory": str(downloads_dir),
            "directory_upgrade": True,
            "prompt_for_download": False,
        }
    )

    savefile_settings = payload.get("savefile")
    if not isinstance(savefile_settings, dict):
        savefile_settings = {}
        payload["savefile"] = savefile_settings
    savefile_settings["default_directory"] = str(downloads_dir)

    plugins_settings = payload.get("plugins")
    if not isinstance(plugins_settings, dict):
        plugins_settings = {}
        payload["plugins"] = plugins_settings
    plugins_settings.setdefault("always_open_pdf_externally", True)

    preferences_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _launch_system_browser_process(
    *,
    executable_path: str,
    user_data_dir: Path,
    profile_directory: str,
    headless: bool,
    window_width: int,
    window_height: int,
    start_maximized: bool,
    debug_port: int,
) -> subprocess.Popen[bytes]:
    launch_args = [
        executable_path,
        f"--user-data-dir={user_data_dir}",
        f"--profile-directory={profile_directory}",
        f"--remote-debugging-port={debug_port}",
        "--disable-popup-blocking",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-renderer-backgrounding",
        "--disable-backgrounding-occluded-windows",
        "--disable-features=CalculateNativeWinOcclusion",
        "--ash-no-nudges",
        "--silent-debugger-extension-api",
    ]
    if headless:
        launch_args.append("--headless=new")
    if start_maximized:
        launch_args.append("--start-maximized")
    else:
        launch_args.append(f"--window-size={window_width},{window_height}")
    return subprocess.Popen(launch_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _configure_browser_download_behavior(*, browser: Browser, downloads_dir: Path) -> None:
    downloads_dir.mkdir(parents=True, exist_ok=True)
    try:
        cdp_session = browser.new_browser_cdp_session()
        cdp_session.send(
            "Browser.setDownloadBehavior",
            {
                "behavior": "allow",
                "downloadPath": str(downloads_dir),
                "eventsEnabled": True,
            },
        )
    except Exception:
        pass


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _wait_for_cdp_url(port: int, *, timeout_seconds: float = 20.0) -> str:
    deadline = time.time() + timeout_seconds
    last_error = ""
    while time.time() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
                websocket_url = payload.get("webSocketDebuggerUrl")
                if websocket_url:
                    return f"http://127.0.0.1:{port}"
                last_error = "missing webSocketDebuggerUrl"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.1)
    raise TimeoutError(f"Timed out waiting for CDP endpoint on port {port}: {last_error}")
