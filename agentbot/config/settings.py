"""Minimal config-backed settings loaded from config.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_TOP_P = 1.0
DEFAULT_FREQUENCY_PENALTY = 0.0
DEFAULT_PRESENCE_PENALTY = 0.0
DEFAULT_LLM_MAX_RETRIES = 2
DEFAULT_SEARCH_PROVIDER = "tavily"
DEFAULT_SEARCH_MAX_RESULTS = 5
DEFAULT_SEARCH_TIMEOUT_SECONDS = 12.0
DEFAULT_COMMAND_ENABLED = False
DEFAULT_COMMAND_DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_COMMAND_MAX_TIMEOUT_SECONDS = 60.0
DEFAULT_COMMAND_MAX_OUTPUT_CHARS = 12000
DEFAULT_BROWSER_HEADLESS = True
DEFAULT_BROWSER_CLOSE_ON_FINISH = True
DEFAULT_BROWSER_MAX_ACTIONS = 12
DEFAULT_BROWSER_MAX_ACTIONS_PER_STEP = 3
DEFAULT_BROWSER_MODE = "system"
DEFAULT_BROWSER_VIEWPORT_WIDTH = 1280
DEFAULT_BROWSER_VIEWPORT_HEIGHT = 720
DEFAULT_BROWSER_WINDOW_WIDTH = 1440
DEFAULT_BROWSER_WINDOW_HEIGHT = 900
DEFAULT_BROWSER_NO_VIEWPORT = False
DEFAULT_BROWSER_START_MAXIMIZED = False
DEFAULT_BROWSER_COPY_LOCAL_PROFILE = True
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
    close_on_finish: bool = DEFAULT_BROWSER_CLOSE_ON_FINISH
    max_actions: int = DEFAULT_BROWSER_MAX_ACTIONS
    max_actions_per_step: int = DEFAULT_BROWSER_MAX_ACTIONS_PER_STEP
    mode: str = DEFAULT_BROWSER_MODE
    viewport_width: int = DEFAULT_BROWSER_VIEWPORT_WIDTH
    viewport_height: int = DEFAULT_BROWSER_VIEWPORT_HEIGHT
    window_width: int = DEFAULT_BROWSER_WINDOW_WIDTH
    window_height: int = DEFAULT_BROWSER_WINDOW_HEIGHT
    no_viewport: bool = DEFAULT_BROWSER_NO_VIEWPORT
    start_maximized: bool = DEFAULT_BROWSER_START_MAXIMIZED
    executable_path: str | None = None
    user_data_dir: str | None = None
    profile_directory: str | None = None
    temp_profiles_dir: str | None = None
    copy_local_profile: bool = DEFAULT_BROWSER_COPY_LOCAL_PROFILE
    artifacts_dir: str | None = None
    downloads_dir: str | None = None
    channel: str | None = None


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from the project config file."""

    openai_api_key: str
    openai_base_url: str | None = None
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int | None = None
    top_p: float = DEFAULT_TOP_P
    frequency_penalty: float = DEFAULT_FREQUENCY_PENALTY
    presence_penalty: float = DEFAULT_PRESENCE_PENALTY
    request_timeout_seconds: float | None = None
    max_retries: int = DEFAULT_LLM_MAX_RETRIES
    reasoning_effort: str | None = None
    reasoning: dict | None = None
    extra_body: dict | None = None
    default_headers: dict[str, str] | None = None
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
        max_tokens = _parse_optional_positive_int(llm_payload.get("max_tokens"), field_name="llm.max_tokens")
        top_p = _parse_float_in_range(
            llm_payload.get("top_p", DEFAULT_TOP_P),
            field_name="llm.top_p",
            min_value=0.0,
            max_value=1.0,
        )
        frequency_penalty = _parse_float_in_range(
            llm_payload.get("frequency_penalty", DEFAULT_FREQUENCY_PENALTY),
            field_name="llm.frequency_penalty",
            min_value=-2.0,
            max_value=2.0,
        )
        presence_penalty = _parse_float_in_range(
            llm_payload.get("presence_penalty", DEFAULT_PRESENCE_PENALTY),
            field_name="llm.presence_penalty",
            min_value=-2.0,
            max_value=2.0,
        )
        request_timeout_seconds = _parse_optional_positive_float(
            llm_payload.get("request_timeout_seconds"),
            field_name="llm.request_timeout_seconds",
        )
        max_retries = _parse_non_negative_int(
            llm_payload.get("max_retries", DEFAULT_LLM_MAX_RETRIES),
            field_name="llm.max_retries",
        )
        reasoning_effort = _parse_optional_string(llm_payload.get("reasoning_effort"))
        reasoning = _parse_optional_dict(llm_payload.get("reasoning"), field_name="llm.reasoning")
        extra_body = _parse_optional_dict(llm_payload.get("extra_body"), field_name="llm.extra_body")
        default_headers = _parse_optional_string_dict(
            llm_payload.get("default_headers"),
            field_name="llm.default_headers",
        )

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
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            request_timeout_seconds=request_timeout_seconds,
            max_retries=max_retries,
            reasoning_effort=reasoning_effort,
            reasoning=reasoning,
            extra_body=extra_body,
            default_headers=default_headers,
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

    close_on_finish_raw = raw_payload.get("close_on_finish", DEFAULT_BROWSER_CLOSE_ON_FINISH)
    if not isinstance(close_on_finish_raw, bool):
        raise ValueError(f"{CONFIG_FILE_NAME} browser.close_on_finish must be true or false.")

    max_actions_raw = raw_payload.get("max_actions", DEFAULT_BROWSER_MAX_ACTIONS)
    try:
        max_actions = int(max_actions_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{CONFIG_FILE_NAME} browser.max_actions must be an integer, got: {max_actions_raw!r}") from exc
    if max_actions < 1:
        raise ValueError(f"{CONFIG_FILE_NAME} browser.max_actions must be greater than 0.")

    max_actions_per_step_raw = raw_payload.get("max_actions_per_step", DEFAULT_BROWSER_MAX_ACTIONS_PER_STEP)
    try:
        max_actions_per_step = int(max_actions_per_step_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{CONFIG_FILE_NAME} browser.max_actions_per_step must be an integer, got: {max_actions_per_step_raw!r}"
        ) from exc
    if max_actions_per_step < 1:
        raise ValueError(f"{CONFIG_FILE_NAME} browser.max_actions_per_step must be greater than 0.")

    mode = _parse_optional_string(raw_payload.get("mode")) or DEFAULT_BROWSER_MODE
    if mode not in {"system", "playwright"}:
        raise ValueError(f'{CONFIG_FILE_NAME} browser.mode must be either "system" or "playwright".')

    viewport_width = _parse_positive_int(
        raw_payload.get("viewport_width", DEFAULT_BROWSER_VIEWPORT_WIDTH),
        field_name="browser.viewport_width",
    )
    viewport_height = _parse_positive_int(
        raw_payload.get("viewport_height", DEFAULT_BROWSER_VIEWPORT_HEIGHT),
        field_name="browser.viewport_height",
    )
    window_width = _parse_positive_int(
        raw_payload.get("window_width", DEFAULT_BROWSER_WINDOW_WIDTH),
        field_name="browser.window_width",
    )
    window_height = _parse_positive_int(
        raw_payload.get("window_height", DEFAULT_BROWSER_WINDOW_HEIGHT),
        field_name="browser.window_height",
    )

    no_viewport_raw = raw_payload.get("no_viewport", DEFAULT_BROWSER_NO_VIEWPORT)
    if not isinstance(no_viewport_raw, bool):
        raise ValueError(f"{CONFIG_FILE_NAME} browser.no_viewport must be true or false.")

    start_maximized_raw = raw_payload.get("start_maximized", DEFAULT_BROWSER_START_MAXIMIZED)
    if not isinstance(start_maximized_raw, bool):
        raise ValueError(f"{CONFIG_FILE_NAME} browser.start_maximized must be true or false.")

    executable_path = _parse_optional_string(raw_payload.get("executable_path"))
    user_data_dir = _parse_optional_string(raw_payload.get("user_data_dir"))
    profile_directory = _parse_optional_string(raw_payload.get("profile_directory"))
    temp_profiles_dir = _parse_optional_string(raw_payload.get("temp_profiles_dir"))
    copy_local_profile_raw = raw_payload.get("copy_local_profile", DEFAULT_BROWSER_COPY_LOCAL_PROFILE)
    if not isinstance(copy_local_profile_raw, bool):
        raise ValueError(f"{CONFIG_FILE_NAME} browser.copy_local_profile must be true or false.")
    artifacts_dir = _parse_optional_string(raw_payload.get("artifacts_dir"))
    downloads_dir = _parse_optional_string(raw_payload.get("downloads_dir"))
    channel = _parse_optional_string(raw_payload.get("channel"))

    return BrowserSettings(
        headless=headless_raw,
        close_on_finish=close_on_finish_raw,
        max_actions=max_actions,
        max_actions_per_step=max_actions_per_step,
        mode=mode,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        window_width=window_width,
        window_height=window_height,
        no_viewport=no_viewport_raw,
        start_maximized=start_maximized_raw,
        executable_path=executable_path,
        user_data_dir=user_data_dir,
        profile_directory=profile_directory,
        temp_profiles_dir=temp_profiles_dir,
        copy_local_profile=copy_local_profile_raw,
        artifacts_dir=artifacts_dir,
        downloads_dir=downloads_dir,
        channel=channel,
    )


def _parse_positive_int(raw_value, *, field_name: str) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{CONFIG_FILE_NAME} {field_name} must be an integer, got: {raw_value!r}") from exc
    if value < 1:
        raise ValueError(f"{CONFIG_FILE_NAME} {field_name} must be greater than 0.")
    return value


def _parse_optional_string(raw_value) -> str | None:
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    return text or None


def _parse_optional_positive_int(raw_value, *, field_name: str) -> int | None:
    if raw_value is None:
        return None
    return _parse_positive_int(raw_value, field_name=field_name)


def _parse_non_negative_int(raw_value, *, field_name: str) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{CONFIG_FILE_NAME} {field_name} must be an integer, got: {raw_value!r}") from exc
    if value < 0:
        raise ValueError(f"{CONFIG_FILE_NAME} {field_name} must be greater than or equal to 0.")
    return value


def _parse_optional_positive_float(raw_value, *, field_name: str) -> float | None:
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{CONFIG_FILE_NAME} {field_name} must be a number, got: {raw_value!r}") from exc
    if value <= 0:
        raise ValueError(f"{CONFIG_FILE_NAME} {field_name} must be greater than 0.")
    return value


def _parse_float_in_range(raw_value, *, field_name: str, min_value: float, max_value: float) -> float:
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{CONFIG_FILE_NAME} {field_name} must be a number, got: {raw_value!r}") from exc
    if value < min_value or value > max_value:
        raise ValueError(f"{CONFIG_FILE_NAME} {field_name} must be between {min_value} and {max_value}.")
    return value


def _parse_optional_dict(raw_value, *, field_name: str) -> dict | None:
    if raw_value is None:
        return None
    if not isinstance(raw_value, dict):
        raise ValueError(f"{CONFIG_FILE_NAME} {field_name} must be an object when provided.")
    return raw_value


def _parse_optional_string_dict(raw_value, *, field_name: str) -> dict[str, str] | None:
    if raw_value is None:
        return None
    if not isinstance(raw_value, dict):
        raise ValueError(f"{CONFIG_FILE_NAME} {field_name} must be an object when provided.")
    parsed: dict[str, str] = {}
    for key, value in raw_value.items():
        parsed[str(key)] = str(value)
    return parsed


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
