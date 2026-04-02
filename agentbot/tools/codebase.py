"""Codebase search and partial-read tools for project-scoped content discovery."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from langchain_core.tools import tool

from agentbot.tools.common import (
    format_project_path,
    resolve_project_path,
    truncate_content,
)

MAX_MATCHES = 50
MAX_GLOB_MATCHES = 200


def _iter_files(root_path: Path, pattern: str | None):
    for candidate in root_path.rglob("*"):
        if not candidate.is_file():
            continue
        relative = format_project_path(candidate).replace("\\", "/")
        if pattern and not fnmatch(candidate.name, pattern) and not fnmatch(relative, pattern):
            continue
        yield candidate


@tool
def glob_files(pattern: str, path: str = ".") -> str:
    """Find project files by glob pattern such as '*.md' or 'docs/**/*.md'."""
    normalized_pattern = pattern.strip()
    if not normalized_pattern:
        raise ValueError("pattern must not be empty.")

    root_path = resolve_project_path(path)
    if not root_path.exists():
        raise FileNotFoundError(f"Path not found: {format_project_path(root_path)}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {format_project_path(root_path)}")

    matches = [
        format_project_path(candidate)
        for candidate in _iter_files(root_path, normalized_pattern)
    ]
    matches.sort()

    lines = [f"Pattern: {normalized_pattern}", f"Base path: {format_project_path(root_path)}"]
    if not matches:
        lines.append("Matches: none")
        return "\n".join(lines)

    visible_matches = matches[:MAX_GLOB_MATCHES]
    lines.append(f"Matches ({len(visible_matches)}):")
    lines.extend(f"- {match}" for match in visible_matches)
    if len(matches) > MAX_GLOB_MATCHES:
        lines.append(
            f"Truncated: showing first {MAX_GLOB_MATCHES} of {len(matches)} matches"
        )
    return "\n".join(lines)


@tool
def search_in_files(query: str, path: str = ".", pattern: str = "*") -> str:
    """Search UTF-8 text files for a query string under a project directory."""
    normalized_query = query.strip()
    normalized_pattern = pattern.strip() or "*"
    if not normalized_query:
        raise ValueError("query must not be empty.")

    root_path = resolve_project_path(path)
    if not root_path.exists():
        raise FileNotFoundError(f"Path not found: {format_project_path(root_path)}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {format_project_path(root_path)}")

    matches: list[str] = []
    lowered_query = normalized_query.lower()
    for candidate in _iter_files(root_path, normalized_pattern):
        try:
            lines = candidate.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(lines, start=1):
            if lowered_query in line.lower():
                matches.append(
                    f"- {format_project_path(candidate)}:{line_number}: {line.strip()}"
                )
                if len(matches) >= MAX_MATCHES:
                    break
        if len(matches) >= MAX_MATCHES:
            break

    lines = [
        f"Query: {normalized_query}",
        f"Base path: {format_project_path(root_path)}",
        f"Pattern: {normalized_pattern}",
    ]
    if not matches:
        lines.append("Matches: none")
        return "\n".join(lines)

    lines.append(f"Matches ({len(matches)}):")
    lines.extend(matches)
    if len(matches) >= MAX_MATCHES:
        lines.append(f"Truncated: showing first {MAX_MATCHES} matches")
    return truncate_content("\n".join(lines))


@tool
def read_file_range(path: str, start_line: int, end_line: int) -> str:
    """Read a line range from a UTF-8 text file under the project root."""
    if start_line < 1:
        raise ValueError("start_line must be at least 1.")
    if end_line < start_line:
        raise ValueError("end_line must be greater than or equal to start_line.")

    file_path = resolve_project_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {format_project_path(file_path)}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {format_project_path(file_path)}")

    lines = file_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return f"File: {format_project_path(file_path)}\nStatus: empty file"
    if start_line > len(lines):
        raise ValueError(
            f"start_line {start_line} is beyond the end of the file ({len(lines)} lines)."
        )

    visible_end_line = min(end_line, len(lines))
    selected_lines = lines[start_line - 1 : visible_end_line]
    rendered = "\n".join(
        f"{line_number}: {line}"
        for line_number, line in enumerate(selected_lines, start=start_line)
    )
    return truncate_content(
        "\n".join(
            [
                f"File: {format_project_path(file_path)}",
                f"Line range: {start_line}-{visible_end_line} of {len(lines)}",
                rendered,
            ]
        )
    )


TOOLS = [glob_files, search_in_files, read_file_range]
