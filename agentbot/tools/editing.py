"""Safer partial-edit tools for project-scoped text files."""

from __future__ import annotations

from langchain_core.tools import tool

from agentbot.tools.common import format_project_path, resolve_project_path


@tool
def replace_in_file(path: str, old_text: str, new_text: str, replace_all: bool = False) -> str:
    """Replace text within a UTF-8 project file without overwriting the whole file manually."""
    if not old_text:
        raise ValueError("old_text must not be empty.")

    file_path = resolve_project_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {format_project_path(file_path)}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {format_project_path(file_path)}")

    content = file_path.read_text(encoding="utf-8")
    occurrences = content.count(old_text)
    if occurrences == 0:
        raise ValueError("old_text was not found in the target file.")
    if occurrences > 1 and not replace_all:
        raise ValueError(
            "old_text matched multiple locations. Set replace_all=true or provide a more specific old_text."
        )

    if replace_all:
        updated = content.replace(old_text, new_text)
        replaced_count = occurrences
    else:
        updated = content.replace(old_text, new_text, 1)
        replaced_count = 1

    file_path.write_text(updated, encoding="utf-8")
    return (
        f"Updated {format_project_path(file_path)} by replacing "
        f"{replaced_count} occurrence(s)."
    )


@tool
def append_file(path: str, content: str, ensure_newline: bool = True) -> str:
    """Append UTF-8 text to a project file, creating the file and parent directories if needed."""
    file_path = resolve_project_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    existing = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
    prefix = ""
    if existing and ensure_newline and not existing.endswith("\n"):
        prefix = "\n"

    file_path.write_text(existing + prefix + content, encoding="utf-8")
    return f"Appended {len(content)} characters to {format_project_path(file_path)}"


TOOLS = [replace_in_file, append_file]
