"""Subprocess worker that runs browser-use in its own Python environment."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _configure_import_path() -> None:
    browser_use_dir = Path(os.environ.get("AGENTBOT_BROWSER_USE_DIR", r"F:\browser-use")).resolve()
    if str(browser_use_dir) not in sys.path:
        sys.path.insert(0, str(browser_use_dir))


os.environ.setdefault("BROWSER_USE_SETUP_LOGGING", "false")
_default_workspace = Path(
    os.environ.get("AGENTBOT_BROWSER_WORKSPACE_DIR", str(Path(__file__).resolve().parents[1] / "workspace"))
).resolve()
_default_workspace.mkdir(parents=True, exist_ok=True)
os.environ["TMP"] = str(_default_workspace)
os.environ["TEMP"] = str(_default_workspace)
os.environ["TMPDIR"] = str(_default_workspace)
_configure_import_path()

_ORIGINAL_PATH_EXISTS = Path.exists
_ORIGINAL_PATH_MKDIR = Path.mkdir


def _redirect_import_tmp_path(path: Path) -> Path:
    raw_path = str(path).replace("\\", "/")
    if raw_path.startswith("/tmp/browser-use-downloads-") or raw_path.startswith("\\tmp\\browser-use-downloads-"):
        return _default_workspace / "browser-use-import-downloads" / path.name
    return path


def _patched_exists(self: Path) -> bool:
    return _ORIGINAL_PATH_EXISTS(_redirect_import_tmp_path(self))


def _patched_mkdir(self: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
    redirected = _redirect_import_tmp_path(self)
    return _ORIGINAL_PATH_MKDIR(redirected, mode=mode, parents=parents, exist_ok=exist_ok)


Path.exists = _patched_exists  # type: ignore[assignment]
Path.mkdir = _patched_mkdir  # type: ignore[assignment]

from browser_use.browser import BrowserSession  # noqa: E402
from browser_use.filesystem.file_system import FileSystem  # noqa: E402
from browser_use.llm.openai.chat import ChatOpenAI  # noqa: E402
from browser_use.tools.service import Tools  # noqa: E402
from browser_use.tools.views import (  # noqa: E402
    ClickElementActionIndexOnly,
    CloseTabAction,
    FindElementsAction,
    GetDropdownOptionsAction,
    InputTextAction,
    NavigateAction,
    ExtractAction,
    ReadContentAction,
    SaveAsPdfAction,
    ScreenshotAction,
    SelectDropdownOptionAction,
    SendKeysAction,
    ScrollAction,
    SearchPageAction,
    SwitchTabAction,
    UploadFileAction,
)

Path.exists = _ORIGINAL_PATH_EXISTS  # type: ignore[assignment]
Path.mkdir = _ORIGINAL_PATH_MKDIR  # type: ignore[assignment]


def _write_response(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def _resolve_browser_executable() -> str | None:
    configured = os.environ.get("AGENTBOT_BROWSER_EXECUTABLE_PATH", "").strip()
    if configured:
        configured_path = Path(configured)
        if configured_path.exists():
            return str(configured_path)
        raise RuntimeError(f"Configured browser executable was not found: {configured}")

    local_app_data = os.environ.get("LOCALAPPDATA", r"C:\Users\%USERNAME%\AppData\Local")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    candidates = [
        Path(program_files) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(program_files_x86) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(local_app_data) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(program_files) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(program_files_x86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(local_app_data) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _serialize_action_result(action_type: str, result: Any) -> dict[str, Any]:
    return {
        "success": not bool(getattr(result, "error", None)),
        "action_type": action_type,
        "extracted_content": str(getattr(result, "extracted_content", "") or ""),
        "error": getattr(result, "error", None),
        "metadata": getattr(result, "metadata", None),
        "attachments": getattr(result, "attachments", None),
        "images": getattr(result, "images", None),
    }


def _build_selector_preview(selector_map: dict[int, Any], limit: int = 25) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for index in sorted(selector_map)[:limit]:
        node = selector_map[index]
        label = (
            (node.get_all_children_text().strip() if hasattr(node, "get_all_children_text") else "")
            or (node.attributes or {}).get("aria-label", "")
            or (node.attributes or {}).get("placeholder", "")
            or (node.attributes or {}).get("title", "")
            or (node.attributes or {}).get("name", "")
        )
        preview.append(
            {
                "index": index,
                "tag": getattr(node, "tag_name", "") or getattr(node, "node_name", ""),
                "label": label[:120],
            }
        )
    return preview


async def _read_command() -> dict[str, Any] | None:
    loop = asyncio.get_running_loop()
    line = await loop.run_in_executor(None, sys.stdin.readline)
    if not line:
        return None
    line = line.strip()
    if not line:
        return {}
    return json.loads(line)


async def main() -> None:
    session: BrowserSession | None = None
    tools: Tools | None = None
    file_system: FileSystem | None = None
    page_extraction_llm: ChatOpenAI | None = None
    workspace_dir = Path(
        os.environ.get("AGENTBOT_BROWSER_WORKSPACE_DIR", str(Path(__file__).resolve().parents[1] / "workspace"))
    ).resolve()
    downloads_dir = workspace_dir / "browser-downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    browser_executable = _resolve_browser_executable()
    session_profile_dir: Path | None = None
    session_filesystem_dir: Path | None = None
    keep_profile = os.environ.get("AGENTBOT_KEEP_BROWSER_PROFILE", "").strip() == "1"

    while True:
        command = await _read_command()
        if command is None:
            break
        if not command:
            continue

        name = command.get("command")

        try:
            if name == "start":
                if session is None:
                    session_profile_dir = Path(
                        tempfile.mkdtemp(prefix="browser-use-user-data-dir-", dir=str(workspace_dir))
                    )
                    session_filesystem_dir = Path(
                        tempfile.mkdtemp(prefix="browser-use-filesystem-", dir=str(workspace_dir))
                    )
                    session_kwargs: dict[str, Any] = {
                        "headless": False,
                        "downloads_path": downloads_dir,
                        "user_data_dir": session_profile_dir,
                    }
                    if browser_executable:
                        session_kwargs["executable_path"] = browser_executable
                    session = BrowserSession(
                        **session_kwargs,
                    )
                    await session.start()
                    tools = Tools()
                    file_system = FileSystem(base_dir=session_filesystem_dir, create_default_files=False)
                    api_key = os.environ.get("AGENTBOT_BROWSER_LLM_API_KEY", "").strip()
                    if api_key:
                        page_extraction_llm = ChatOpenAI(
                            model=os.environ.get("AGENTBOT_BROWSER_LLM_MODEL", "gpt-4.1-mini").strip(),
                            api_key=api_key,
                            base_url=os.environ.get("AGENTBOT_BROWSER_LLM_BASE_URL", "").strip() or None,
                            temperature=0.1,
                        )

                start_url = command.get("start_url")
                navigation = None
                if start_url:
                    assert tools is not None
                    result = await tools.navigate(
                        browser_session=session,
                        url=start_url,
                        new_tab=False,
                    )
                    navigation = _serialize_action_result("navigate", result)

                _write_response(
                    {
                        "ok": True,
                        "result": {
                            "started": True,
                            "session_id": getattr(session, "id", None),
                            "browser_executable": browser_executable,
                            "navigation": navigation,
                        },
                    }
                )
            elif name == "observe":
                if session is None:
                    raise RuntimeError("Browser session has not been started.")
                state = await session.get_browser_state_summary(
                    include_screenshot=False,
                    include_recent_events=True,
                )
                selector_map = await session.get_selector_map()
                _write_response(
                    {
                        "ok": True,
                        "result": {
                            "url": state.url,
                            "title": state.title,
                            "tabs": [
                                {
                                    "target_id": tab.target_id[-4:],
                                    "title": tab.title,
                                    "url": tab.url,
                                }
                                for tab in state.tabs
                            ],
                            "interactive_count": len(selector_map),
                            "llm_representation": state.dom_state.llm_representation(),
                            "selector_preview": _build_selector_preview(selector_map),
                            "recent_events": state.recent_events,
                        },
                    }
                )
            elif name == "act":
                if session is None or tools is None:
                    raise RuntimeError("Browser session has not been started.")
                action_type = str(command["action_type"])
                if action_type == "navigate":
                    params = NavigateAction(
                        url=str(command["url"]),
                        new_tab=bool(command.get("new_tab", False)),
                    )
                    result = await tools.navigate(
                        browser_session=session,
                        url=params.url,
                        new_tab=params.new_tab,
                    )
                elif action_type == "click":
                    params = ClickElementActionIndexOnly(index=int(command["index"]))
                    result = await tools.click(browser_session=session, index=params.index)
                elif action_type == "input":
                    params = InputTextAction(
                        index=int(command["index"]),
                        text=str(command["text"]),
                        clear=bool(command.get("clear", True)),
                    )
                    result = await tools.input(
                        browser_session=session,
                        index=params.index,
                        text=params.text,
                        clear=params.clear,
                    )
                elif action_type == "upload_file":
                    if file_system is None:
                        raise RuntimeError("upload_file is unavailable because browser filesystem is not configured.")
                    params = UploadFileAction(
                        index=int(command["index"]),
                        path=str(command["path"]),
                    )
                    result = await tools.upload_file(
                        params=params,
                        browser_session=session,
                        available_file_paths=[params.path],
                        file_system=file_system,
                    )
                elif action_type == "scroll":
                    params = ScrollAction(
                        down=bool(command.get("down", True)),
                        pages=float(command["pages"]),
                        index=command.get("index"),
                    )
                    result = await tools.scroll(
                        browser_session=session,
                        down=params.down,
                        pages=params.pages,
                        index=params.index,
                    )
                elif action_type == "scroll_to_text":
                    result = await tools.find_text(text=str(command["text"]), browser_session=session)
                elif action_type == "wait":
                    result = await tools.wait(seconds=int(command["seconds"]))
                elif action_type == "go_back":
                    result = await tools.go_back(browser_session=session)
                elif action_type == "extract":
                    if page_extraction_llm is None or file_system is None:
                        raise RuntimeError("Extract action is unavailable because browser extraction LLM is not configured.")
                    params = ExtractAction(
                        query=str(command["query"]),
                        extract_links=bool(command.get("extract_links", False)),
                        start_from_char=int(command.get("start_from_char", 0)),
                    )
                    result = await tools.extract(
                        browser_session=session,
                        query=params.query,
                        extract_links=params.extract_links,
                        start_from_char=params.start_from_char,
                        page_extraction_llm=page_extraction_llm,
                        file_system=file_system,
                    )
                elif action_type == "search_page":
                    params = SearchPageAction(pattern=str(command["pattern"]))
                    result = await tools.search_page(params=params, browser_session=session)
                elif action_type == "find_elements":
                    params = FindElementsAction(
                        selector=str(command["selector"]),
                        attributes=command.get("attributes"),
                        include_text=bool(command.get("include_text", True)),
                    )
                    result = await tools.find_elements(params=params, browser_session=session)
                elif action_type == "switch_tab":
                    params = SwitchTabAction(tab_id=str(command["tab_id"]))
                    result = await tools.switch(params=params, browser_session=session)
                elif action_type == "close_tab":
                    params = CloseTabAction(tab_id=str(command["tab_id"]))
                    result = await tools.close(params=params, browser_session=session)
                elif action_type == "send_keys":
                    params = SendKeysAction(keys=str(command["keys"]))
                    result = await tools.send_keys(params=params, browser_session=session)
                elif action_type == "read_content":
                    if page_extraction_llm is None:
                        raise RuntimeError("read_content is unavailable because browser extraction LLM is not configured.")
                    params = ReadContentAction(
                        goal=str(command["goal"]),
                        source=str(command.get("source") or "page"),
                        context=str(command.get("context") or ""),
                    )
                    result = await tools.read_long_content(
                        params=params,
                        browser_session=session,
                        page_extraction_llm=page_extraction_llm,
                        available_file_paths=[],
                    )
                elif action_type == "get_dropdown_options":
                    params = GetDropdownOptionsAction(index=int(command["index"]))
                    result = await tools.dropdown_options(params=params, browser_session=session)
                elif action_type == "select_dropdown_option":
                    params = SelectDropdownOptionAction(
                        index=int(command["index"]),
                        text=str(command["text"]),
                    )
                    result = await tools.select_dropdown(params=params, browser_session=session)
                elif action_type == "screenshot":
                    if file_system is None:
                        raise RuntimeError("screenshot is unavailable because browser filesystem is not configured.")
                    params = ScreenshotAction(file_name=command.get("file_name"))
                    result = await tools.screenshot(
                        params=params,
                        browser_session=session,
                        file_system=file_system,
                    )
                elif action_type == "save_as_pdf":
                    if file_system is None:
                        raise RuntimeError("save_as_pdf is unavailable because browser filesystem is not configured.")
                    params = SaveAsPdfAction(
                        file_name=command.get("file_name"),
                        print_background=bool(command.get("print_background", True)),
                        landscape=bool(command.get("landscape", False)),
                        scale=float(command.get("scale", 1.0)),
                        paper_format=str(command.get("paper_format") or "Letter"),
                    )
                    result = await tools.save_as_pdf(
                        params=params,
                        browser_session=session,
                        file_system=file_system,
                    )
                else:
                    raise RuntimeError(f"Unsupported action_type: {action_type}")

                _write_response({"ok": True, "result": _serialize_action_result(action_type, result)})
            elif name == "close":
                if session is not None:
                    await session.kill()
                    session = None
                    tools = None
                    file_system = None
                    page_extraction_llm = None
                    if session_profile_dir is not None and not keep_profile:
                        shutil.rmtree(session_profile_dir, ignore_errors=True)
                    if session_filesystem_dir is not None:
                        shutil.rmtree(session_filesystem_dir, ignore_errors=True)
                    session_profile_dir = None
                    session_filesystem_dir = None
                _write_response({"ok": True, "result": {"closed": True}})
                break
            else:
                raise RuntimeError(f"Unknown command: {name}")
        except Exception as exc:  # pragma: no cover - subprocess bridge
            if session is not None:
                try:
                    await session.kill()
                except Exception:
                    pass
            if session_profile_dir is not None and not keep_profile:
                shutil.rmtree(session_profile_dir, ignore_errors=True)
            if session_filesystem_dir is not None:
                shutil.rmtree(session_filesystem_dir, ignore_errors=True)
            session = None
            tools = None
            file_system = None
            page_extraction_llm = None
            session_profile_dir = None
            session_filesystem_dir = None
            _write_response({"ok": False, "error": str(exc)})


if __name__ == "__main__":
    asyncio.run(main())
