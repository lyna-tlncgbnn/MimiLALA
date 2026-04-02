"""Shared helpers for project-scoped tools."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_READ_CHARS = 12000
MAX_LIST_ENTRIES = 200


def resolve_project_path(path: str) -> Path:
    """Resolve a project-relative or absolute path within the project root."""
    raw_path = Path(path).expanduser()
    candidate = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
    resolved = candidate.resolve()

    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError(
            f"Path '{path}' is outside the project root and cannot be accessed."
        ) from exc

    return resolved


def format_project_path(path: Path) -> str:
    """Return a stable project-relative display path when possible."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def truncate_content(content: str, *, max_chars: int = MAX_READ_CHARS) -> str:
    """Truncate long text outputs for tool-friendly responses."""
    if len(content) <= max_chars:
        return content

    return (
        content[:max_chars]
        + f"\n\n... truncated: showing first {max_chars} characters of "
        + f"{len(content)} total characters"
    )
