"""Minimal config-backed settings loaded from config.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_SEARCH_PROVIDER = "tavily"
DEFAULT_SEARCH_MAX_RESULTS = 5
DEFAULT_SEARCH_TIMEOUT_SECONDS = 12.0
DEFAULT_COMMAND_ENABLED = False
DEFAULT_COMMAND_DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_COMMAND_MAX_TIMEOUT_SECONDS = 60.0
DEFAULT_COMMAND_MAX_OUTPUT_CHARS = 12000
DEFAULT_BROWSER_HEADLESS = True
DEFAULT_ALLOWED_COMMAND_PROGRAMS = (
    ".venv\\Scripts\\python.exe",
    "python",
    "uv",
    "npm",
)
DEFAULT_BLOCKED_COMMAND_PATTERNS = (
    "del ",
    "erase ",
    "remove-item",
    "rmdir",
    "format ",
    "shutdown ",
    "reg delete",
    "git reset --hard",
    "git clean -fd",
    ">",
    ">>",
    "|",
    "&&",
    "||",
)
CONFIG_FILE_NAME = "config.json"


@dataclass(slots=True)
class SearchSettings:
    """Application-level search configuration loaded from config.json."""

    provider: str = DEFAULT_SEARCH_PROVIDER
    api_key: str = ""
    max_results: int = DEFAULT_SEARCH_MAX_RESULTS
    timeout_seconds: float = DEFAULT_SEARCH_TIMEOUT_SECONDS


@dataclass(slots=True)
class CommandSettings:
    """Application-level command execution policy loaded from config.json."""

    enabled: bool = DEFAULT_COMMAND_ENABLED
    default_timeout_seconds: float = DEFAULT_COMMAND_DEFAULT_TIMEOUT_SECONDS
    max_timeout_seconds: float = DEFAULT_COMMAND_MAX_TIMEOUT_SECONDS
    max_output_chars: int = DEFAULT_COMMAND_MAX_OUTPUT_CHARS
    allowed_programs: list[str] | None = None
    blocked_patterns: list[str] | None = None


@dataclass(slots=True)
class BrowserSettings:
    """Application-level browser execution settings loaded from config.json."""

    headless: bool = DEFAULT_BROWSER_HEADLESS


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from the project config file."""

    openai_api_key: str
    openai_base_url: str | None = None
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    search: SearchSettings | None = None
    command: CommandSettings | None = None
    browser: BrowserSettings | None = None
    debug: bool = False

    @classmethod
    def from_file(cls, path: Path | None = None) -> "Settings":
        config_path = path or cls.default_config_path()
        if not config_path.exists():
            raise ValueError(
                f"{CONFIG_FILE_NAME} was not found at {config_path}. Create it before running the CLI."
            )

        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{CONFIG_FILE_NAME} contains invalid JSON: {exc}") from exc

        llm_payload = payload.get("llm")
        if not isinstance(llm_payload, dict):
            raise ValueError(f"{CONFIG_FILE_NAME} must contain an object field named 'llm'.")

        api_key = str(llm_payload.get("api_key", "")).strip()
        if not api_key:
            raise ValueError(f"{CONFIG_FILE_NAME} requires llm.api_key.")

        base_url_raw = llm_payload.get("base_url", "")
        base_url = str(base_url_raw).strip() or None
        model = str(llm_payload.get("model", DEFAULT_MODEL)).strip() or DEFAULT_MODEL
        temperature_raw = str(llm_payload.get("temperature", DEFAULT_TEMPERATURE)).strip()
        try:
            temperature = float(temperature_raw)
        except ValueError as exc:
            raise ValueError(f"{CONFIG_FILE_NAME} llm.temperature must be a number, got: {temperature_raw!r}") from exc

        search = _parse_search_settings(payload.get("search"))
        command = _parse_command_settings(payload.get("command"))
        browser = _parse_browser_settings(payload.get("browser"))

        debug_raw = payload.get("debug", False)
        if not isinstance(debug_raw, bool):
            raise ValueError(f"{CONFIG_FILE_NAME} debug must be true or false.")

        return cls(
            openai_api_key=api_key,
            openai_base_url=base_url,
            model=model,
            temperature=temperature,
            search=search,
            command=command,
            browser=browser,
            debug=debug_raw,
        )

    @staticmethod
    def default_config_path() -> Path:
        return Path(__file__).resolve().parents[2] / CONFIG_FILE_NAME


def _parse_search_settings(raw_payload) -> SearchSettings | None:
    if raw_payload is None:
        return None
    if not isinstance(raw_payload, dict):
        raise ValueError(f"{CONFIG_FILE_NAME} search must be an object when provided.")

    provider = str(raw_payload.get("provider", DEFAULT_SEARCH_PROVIDER)).strip() or DEFAULT_SEARCH_PROVIDER
    api_key = str(raw_payload.get("api_key", "")).strip()

    max_results_raw = raw_payload.get("max_results", DEFAULT_SEARCH_MAX_RESULTS)
    try:
        max_results = int(max_results_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{CONFIG_FILE_NAME} search.max_results must be an integer, got: {max_results_raw!r}"
        ) from exc
    if max_results < 1 or max_results > 10:
        raise ValueError(f"{CONFIG_FILE_NAME} search.max_results must be between 1 and 10.")

    timeout_raw = raw_payload.get("timeout_seconds", DEFAULT_SEARCH_TIMEOUT_SECONDS)
    try:
        timeout_seconds = float(timeout_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{CONFIG_FILE_NAME} search.timeout_seconds must be a number, got: {timeout_raw!r}"
        ) from exc
    if timeout_seconds <= 0:
        raise ValueError(f"{CONFIG_FILE_NAME} search.timeout_seconds must be greater than 0.")

    return SearchSettings(
        provider=provider,
        api_key=api_key,
        max_results=max_results,
        timeout_seconds=timeout_seconds,
    )


def _parse_command_settings(raw_payload) -> CommandSettings | None:
    if raw_payload is None:
        return None
    if not isinstance(raw_payload, dict):
        raise ValueError(f"{CONFIG_FILE_NAME} command must be an object when provided.")

    enabled_raw = raw_payload.get("enabled", DEFAULT_COMMAND_ENABLED)
    if not isinstance(enabled_raw, bool):
        raise ValueError(f"{CONFIG_FILE_NAME} command.enabled must be true or false.")

    default_timeout_raw = raw_payload.get(
        "default_timeout_seconds", DEFAULT_COMMAND_DEFAULT_TIMEOUT_SECONDS
    )
    try:
        default_timeout_seconds = float(default_timeout_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{CONFIG_FILE_NAME} command.default_timeout_seconds must be a number, got: {default_timeout_raw!r}"
        ) from exc
    if default_timeout_seconds <= 0:
        raise ValueError(f"{CONFIG_FILE_NAME} command.default_timeout_seconds must be greater than 0.")

    max_timeout_raw = raw_payload.get(
        "max_timeout_seconds", DEFAULT_COMMAND_MAX_TIMEOUT_SECONDS
    )
    try:
        max_timeout_seconds = float(max_timeout_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{CONFIG_FILE_NAME} command.max_timeout_seconds must be a number, got: {max_timeout_raw!r}"
        ) from exc
    if max_timeout_seconds <= 0:
        raise ValueError(f"{CONFIG_FILE_NAME} command.max_timeout_seconds must be greater than 0.")
    if max_timeout_seconds < default_timeout_seconds:
        raise ValueError(
            f"{CONFIG_FILE_NAME} command.max_timeout_seconds must be greater than or equal to command.default_timeout_seconds."
        )

    max_output_chars_raw = raw_payload.get(
        "max_output_chars", DEFAULT_COMMAND_MAX_OUTPUT_CHARS
    )
    try:
        max_output_chars = int(max_output_chars_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{CONFIG_FILE_NAME} command.max_output_chars must be an integer, got: {max_output_chars_raw!r}"
        ) from exc
    if max_output_chars < 1000:
        raise ValueError(f"{CONFIG_FILE_NAME} command.max_output_chars must be at least 1000.")

    allowed_programs = _parse_string_list(
        raw_payload.get("allowed_programs", list(DEFAULT_ALLOWED_COMMAND_PROGRAMS)),
        field_name="command.allowed_programs",
        min_length=1,
    )
    blocked_patterns = _parse_string_list(
        raw_payload.get("blocked_patterns", list(DEFAULT_BLOCKED_COMMAND_PATTERNS)),
        field_name="command.blocked_patterns",
        min_length=0,
    )

    return CommandSettings(
        enabled=enabled_raw,
        default_timeout_seconds=default_timeout_seconds,
        max_timeout_seconds=max_timeout_seconds,
        max_output_chars=max_output_chars,
        allowed_programs=allowed_programs,
        blocked_patterns=blocked_patterns,
    )


def _parse_browser_settings(raw_payload) -> BrowserSettings | None:
    if raw_payload is None:
        return BrowserSettings()
    if not isinstance(raw_payload, dict):
        raise ValueError(f"{CONFIG_FILE_NAME} browser must be an object when provided.")

    headless_raw = raw_payload.get("headless", DEFAULT_BROWSER_HEADLESS)
    if not isinstance(headless_raw, bool):
        raise ValueError(f"{CONFIG_FILE_NAME} browser.headless must be true or false.")

    return BrowserSettings(headless=headless_raw)


def _parse_string_list(raw_value, *, field_name: str, min_length: int) -> list[str]:
    if not isinstance(raw_value, list):
        raise ValueError(f"{CONFIG_FILE_NAME} {field_name} must be an array of strings.")

    values: list[str] = []
    for item in raw_value:
        normalized = str(item).strip()
        if not normalized:
            continue
        values.append(normalized)

    if len(values) < min_length:
        raise ValueError(f"{CONFIG_FILE_NAME} {field_name} must include at least {min_length} item(s).")

    return values
