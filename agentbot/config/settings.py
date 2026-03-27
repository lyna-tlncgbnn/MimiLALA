"""Minimal config-backed settings loaded from config.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TEMPERATURE = 0.1
CONFIG_FILE_NAME = "config.json"


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from the project config file."""

    openai_api_key: str
    openai_base_url: str | None = None
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE

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

        return cls(
            openai_api_key=api_key,
            openai_base_url=base_url,
            model=model,
            temperature=temperature,
        )

    @staticmethod
    def default_config_path() -> Path:
        return Path(__file__).resolve().parents[2] / CONFIG_FILE_NAME
