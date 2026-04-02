"""Minimal filesystem tools for the richer-tools phase."""

from __future__ import annotations

from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from langchain_core.tools import tool
from pypdf import PdfReader

from agentbot.tools.common import (
    MAX_LIST_ENTRIES,
    format_project_path,
    resolve_project_path,
    truncate_content,
)


@tool
def list_directory(path: str) -> str:
    """List files and subdirectories under a project-relative or absolute directory path."""
    directory = resolve_project_path(path)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {format_project_path(directory)}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {format_project_path(directory)}")

    entries = sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    if not entries:
        return f"Directory: {_format_path(directory)}\nStatus: empty"

    visible_entries = entries[:MAX_LIST_ENTRIES]
    directories = [entry for entry in visible_entries if entry.is_dir()]
    files = [entry for entry in visible_entries if entry.is_file()]

    lines: list[str] = [f"Directory: {format_project_path(directory)}"]
    lines.append(f"Subdirectories ({len(directories)}):")
    if directories:
        lines.extend(f"- {format_project_path(entry)}" for entry in directories)
    else:
        lines.append("- none")

    lines.append(f"Files ({len(files)}):")
    if files:
        lines.extend(f"- {format_project_path(entry)}" for entry in files)
    else:
        lines.append("- none")

    if len(entries) > MAX_LIST_ENTRIES:
        lines.append(
            f"Truncated: showing first {MAX_LIST_ENTRIES} of {len(entries)} entries"
        )

    return "\n".join(lines)


@tool
def read_file(path: str) -> str:
    """Read a UTF-8 text file from a project-relative or absolute path."""
    file_path = resolve_project_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {format_project_path(file_path)}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {format_project_path(file_path)}")

    content = file_path.read_text(encoding="utf-8")
    return truncate_content(content)


@tool
def read_pdf(path: str) -> str:
    """Read text from a PDF file within the project root."""
    file_path = resolve_project_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {format_project_path(file_path)}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {format_project_path(file_path)}")
    if file_path.suffix.lower() != ".pdf":
        raise ValueError(f"Path is not a PDF file: {format_project_path(file_path)}")

    reader = PdfReader(str(file_path))
    page_texts: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            page_texts.append(f"[Page {index}]\n{text}")

    if not page_texts:
        return f"No extractable text found in {format_project_path(file_path)}"

    return truncate_content("\n\n".join(page_texts))


@tool
def read_docx(path: str) -> str:
    """Read paragraph text from a DOCX file within the project root."""
    file_path = resolve_project_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {format_project_path(file_path)}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {format_project_path(file_path)}")
    if file_path.suffix.lower() != ".docx":
        raise ValueError(f"Path is not a DOCX file: {format_project_path(file_path)}")

    try:
        with ZipFile(file_path) as archive:
            document_xml = archive.read("word/document.xml")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Invalid DOCX structure: {format_project_path(file_path)}") from exc
    except BadZipFile as exc:
        raise ValueError(f"Invalid DOCX file: {format_project_path(file_path)}") from exc

    root = ElementTree.fromstring(document_xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []

    for paragraph in root.findall(".//w:p", namespace):
        texts = [
            node.text or ""
            for node in paragraph.findall(".//w:t", namespace)
        ]
        line = "".join(texts).strip()
        if line:
            paragraphs.append(line)

    if not paragraphs:
        return f"No extractable text found in {format_project_path(file_path)}"

    return truncate_content("\n\n".join(paragraphs))


@tool
def write_file(path: str, content: str) -> str:
    """Write UTF-8 text to a project-relative or absolute file path, creating parent directories if needed."""
    file_path = resolve_project_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {format_project_path(file_path)}"


TOOLS = [list_directory, read_file, read_pdf, read_docx, write_file]
