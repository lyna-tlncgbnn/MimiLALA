"""Runtime bridge for browser-use powered browser sessions."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from threading import Thread
from uuid import uuid4

from agentbot.models.browser import BrowserActionPlan, BrowserActionResultModel, BrowserObservation


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BROWSER_USE_DIR = Path(os.environ.get("AGENTBOT_BROWSER_USE_DIR", r"F:\browser-use"))
DEFAULT_BROWSER_USE_PYTHON = Path(
    os.environ.get(
        "AGENTBOT_BROWSER_USE_PYTHON",
        str(DEFAULT_BROWSER_USE_DIR / ".venv" / "Scripts" / "python.exe"),
    )
)
WORKER_SCRIPT = PROJECT_ROOT / "agentbot" / "browser_worker.py"
DEFAULT_WORKER_TIMEOUT_SECONDS = int(os.environ.get("AGENTBOT_BROWSER_WORKER_TIMEOUT_SECONDS", "45"))


@dataclass
class BrowserWorkerSession:
    session_id: str
    process: subprocess.Popen[str]


class BrowserRuntimeManager:
    """Manage long-lived browser worker subprocesses."""

    def __init__(self) -> None:
        self._sessions: dict[str, BrowserWorkerSession] = {}
        self._lock = Lock()

    def create_session(self, start_url: str | None = None, llm_config: dict | None = None) -> str:
        python_executable = DEFAULT_BROWSER_USE_PYTHON
        if not python_executable.exists():
            raise RuntimeError(f"browser-use Python was not found at {python_executable}")

        env = os.environ.copy()
        env["AGENTBOT_BROWSER_USE_DIR"] = str(DEFAULT_BROWSER_USE_DIR)
        env["AGENTBOT_BROWSER_WORKSPACE_DIR"] = str(PROJECT_ROOT / "workspace")
        env["PYTHONIOENCODING"] = "utf-8"
        if llm_config:
            for source_key, env_key in (
                ("api_key", "AGENTBOT_BROWSER_LLM_API_KEY"),
                ("base_url", "AGENTBOT_BROWSER_LLM_BASE_URL"),
                ("model", "AGENTBOT_BROWSER_LLM_MODEL"),
            ):
                value = llm_config.get(source_key)
                if value:
                    env[env_key] = str(value)
        process = subprocess.Popen(
            [str(python_executable), str(WORKER_SCRIPT)],
            cwd=str(PROJECT_ROOT),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        session_id = uuid4().hex
        worker_session = BrowserWorkerSession(session_id=session_id, process=process)
        try:
            self._send_command(worker_session, {"command": "start", "start_url": start_url})
        except Exception:
            process.kill()
            process.wait(timeout=5)
            raise
        with self._lock:
            self._sessions[session_id] = worker_session
        return session_id

    def observe(self, session_id: str) -> BrowserObservation:
        payload = self._send_command(self._require_session(session_id), {"command": "observe"})
        return BrowserObservation.model_validate(payload)

    def execute_action(self, session_id: str, action: BrowserActionPlan) -> BrowserActionResultModel:
        payload = self._send_command(
            self._require_session(session_id),
            {
                "command": "act",
                "action_type": action.action_type,
                "url": action.url,
                "new_tab": action.new_tab,
                "index": action.index,
                "text": action.text,
                "path": action.path,
                "clear": action.clear,
                "seconds": action.seconds,
                "pages": action.pages,
                "down": action.down,
                "query": action.query,
                "pattern": action.pattern,
                "selector": action.selector,
                "attributes": action.attributes,
                "include_text": action.include_text,
                "extract_links": action.extract_links,
                "start_from_char": action.start_from_char,
                "tab_id": action.tab_id,
                "keys": action.keys,
                "goal": action.goal,
                "source": action.source,
                "context": action.context,
                "file_name": action.file_name,
                "print_background": action.print_background,
                "landscape": action.landscape,
                "scale": action.scale,
                "paper_format": action.paper_format,
            },
        )
        return BrowserActionResultModel.model_validate(payload)

    def close_session(self, session_id: str) -> None:
        with self._lock:
            worker_session = self._sessions.pop(session_id, None)
        if worker_session is None:
            return
        try:
            self._send_command(worker_session, {"command": "close"})
        except Exception:
            worker_session.process.kill()
        finally:
            worker_session.process.wait(timeout=5)

    def _require_session(self, session_id: str) -> BrowserWorkerSession:
        with self._lock:
            worker_session = self._sessions.get(session_id)
        if worker_session is None:
            raise RuntimeError(f"Unknown browser session: {session_id}")
        return worker_session

    def _send_command(self, worker_session: BrowserWorkerSession, payload: dict) -> dict:
        process = worker_session.process
        if process.stdin is None or process.stdout is None:
            raise RuntimeError("Browser worker pipes are not available.")
        if process.poll() is not None:
            stderr_output = ""
            if process.stderr is not None:
                stderr_output = process.stderr.read().strip()
            raise RuntimeError(f"Browser worker exited unexpectedly. {stderr_output}".strip())

        process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        process.stdin.flush()

        line = self._readline_with_timeout(process, DEFAULT_WORKER_TIMEOUT_SECONDS)
        if not line:
            stderr_output = ""
            if process.stderr is not None:
                stderr_output = process.stderr.read().strip()
            raise RuntimeError(f"Browser worker returned no data. {stderr_output}".strip())

        response = json.loads(line)
        if not response.get("ok"):
            raise RuntimeError(str(response.get("error") or "Unknown browser worker error"))
        return dict(response.get("result") or {})

    @staticmethod
    def _readline_with_timeout(process: subprocess.Popen[str], timeout_seconds: int) -> str:
        if process.stdout is None:
            raise RuntimeError("Browser worker stdout pipe is not available.")

        result: list[str] = []
        error: list[BaseException] = []

        def _reader() -> None:
            try:
                result.append(process.stdout.readline())
            except BaseException as exc:  # pragma: no cover - defensive bridge code
                error.append(exc)

        thread = Thread(target=_reader, daemon=True)
        thread.start()
        thread.join(timeout_seconds)
        if thread.is_alive():
            process.kill()
            stderr_output = ""
            if process.stderr is not None:
                stderr_output = process.stderr.read().strip()
            raise RuntimeError(
                f"Browser worker timed out after {timeout_seconds}s. {stderr_output}".strip()
            )
        if error:
            raise RuntimeError(str(error[0]))
        return result[0] if result else ""


runtime_manager = BrowserRuntimeManager()
