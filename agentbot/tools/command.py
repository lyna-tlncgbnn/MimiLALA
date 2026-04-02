"""Conservative local command execution tools."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from langchain_core.tools import tool

from agentbot.config.settings import Settings
from agentbot.tools.common import PROJECT_ROOT, format_project_path, resolve_project_path


def _load_command_settings():
    settings = Settings.from_file()
    if settings.command is None or not settings.command.enabled:
        raise ValueError(
            "Command execution is disabled. Add an enabled 'command' section to config.json before using run_command."
        )
    return settings.command


def _split_command(command: str) -> list[str]:
    normalized_command = command.strip()
    if not normalized_command:
        raise ValueError("command must not be empty.")

    try:
        parts = shlex.split(normalized_command, posix=False)
    except ValueError as exc:
        raise ValueError(f"command could not be parsed safely: {exc}") from exc

    if not parts:
        raise ValueError("command must not be empty.")
    return parts


def _normalize_program_name(value: str) -> str:
    normalized = value.strip().strip('"').replace("/", "\\")
    return normalized.lower()


def _program_matches_allowed(program: str, allowed_programs: list[str]) -> bool:
    program_path = Path(program.strip('"'))
    program_name = program_path.name.lower()
    normalized_program = _normalize_program_name(program)

    for allowed in allowed_programs:
        normalized_allowed = _normalize_program_name(allowed)
        allowed_name = Path(normalized_allowed).name.lower()
        if normalized_program == normalized_allowed or program_name == allowed_name:
            return True
    return False


def _contains_blocked_pattern(command: str, blocked_patterns: list[str]) -> str | None:
    lowered_command = command.lower()
    for pattern in blocked_patterns:
        normalized_pattern = pattern.strip().lower()
        if normalized_pattern and normalized_pattern in lowered_command:
            return pattern
    return None


def _build_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    return env


def _truncate_output(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text.strip() or "(empty)"

    visible = text[:max_chars].rstrip()
    return visible + f"\n... truncated to first {max_chars} characters"


@tool
def run_command(command: str, cwd: str = ".", timeout_seconds: float | None = None) -> str:
    """Run a locally configured allowlisted command inside the project root and return stdout and stderr."""
    command_settings = _load_command_settings()
    command_parts = _split_command(command)
    program = command_parts[0]

    if not _program_matches_allowed(program, command_settings.allowed_programs or []):
        raise ValueError(
            f"Program '{program}' is not allowed by command.allowed_programs in config.json."
        )

    blocked_pattern = _contains_blocked_pattern(command, command_settings.blocked_patterns or [])
    if blocked_pattern is not None:
        raise ValueError(
            f"Command contains blocked pattern {blocked_pattern!r} from command.blocked_patterns."
        )

    working_directory = resolve_project_path(cwd)
    if not working_directory.exists():
        raise FileNotFoundError(f"Working directory not found: {format_project_path(working_directory)}")
    if not working_directory.is_dir():
        raise NotADirectoryError(
            f"Working directory is not a directory: {format_project_path(working_directory)}"
        )

    effective_timeout = (
        command_settings.default_timeout_seconds
        if timeout_seconds is None
        else float(timeout_seconds)
    )
    if effective_timeout <= 0:
        raise ValueError("timeout_seconds must be greater than 0.")
    if effective_timeout > command_settings.max_timeout_seconds:
        raise ValueError(
            "timeout_seconds exceeds command.max_timeout_seconds from config.json."
        )

    try:
        completed = subprocess.run(
            command_parts,
            cwd=working_directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=effective_timeout,
            shell=False,
            env=_build_environment(),
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Program '{program}' was not found in the current environment."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        stdout = _truncate_output(exc.stdout or "", command_settings.max_output_chars)
        stderr = _truncate_output(exc.stderr or "", command_settings.max_output_chars)
        return "\n".join(
            [
                f"Command: {command}",
                f"Working directory: {format_project_path(working_directory)}",
                "Timed out: true",
                f"Timeout seconds: {effective_timeout:g}",
                f"Project root: {PROJECT_ROOT}",
                "Stdout:",
                stdout,
                "Stderr:",
                stderr,
            ]
        )

    stdout = _truncate_output(completed.stdout, command_settings.max_output_chars)
    stderr = _truncate_output(completed.stderr, command_settings.max_output_chars)
    return "\n".join(
        [
            f"Command: {command}",
            f"Working directory: {format_project_path(working_directory)}",
            "Timed out: false",
            f"Exit code: {completed.returncode}",
            "Stdout:",
            stdout,
            "Stderr:",
            stderr,
        ]
    )


TOOLS = [run_command]
