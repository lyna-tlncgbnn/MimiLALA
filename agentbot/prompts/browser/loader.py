"""Utilities for loading browser prompt templates from disk."""

from __future__ import annotations

from pathlib import Path


PROMPT_DIR = Path(__file__).resolve().parent


def load_browser_prompt(name: str, **replacements: object) -> str:
    """Load one browser prompt template and format it with simple replacements."""
    template_path = PROMPT_DIR / name
    template = template_path.read_text(encoding="utf-8")
    if replacements:
        return template.format(**replacements)
    return template
