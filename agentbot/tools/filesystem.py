"""Minimal filesystem tools for the richer-tools phase."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from langchain_core.tools import tool
from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_READ_CHARS = 12000
MAX_LIST_ENTRIES = 200


def _resolve_path(path: str) -> Path:
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


def _format_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _truncate_content(content: str) -> str:
    if len(content) <= MAX_READ_CHARS:
        return content

    return (
        content[:MAX_READ_CHARS]
        + f"\n\n... truncated: showing first {MAX_READ_CHARS} characters of "
        + f"{len(content)} total characters"
    )


@tool
def list_directory(path: str) -> str:
    """List files and subdirectories under a project-relative or absolute directory path."""
    directory = _resolve_path(path)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {_format_path(directory)}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {_format_path(directory)}")

    entries = sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    if not entries:
        return f"Directory is empty: {_format_path(directory)}"

    lines: list[str] = []
    for entry in entries[:MAX_LIST_ENTRIES]:
        kind = "dir" if entry.is_dir() else "file"
        lines.append(f"{kind}: {_format_path(entry)}")

    if len(entries) > MAX_LIST_ENTRIES:
        lines.append(
            f"... truncated: showing first {MAX_LIST_ENTRIES} of {len(entries)} entries"
        )

    return "\n".join(lines)


@tool
def read_file(path: str) -> str:
    """Read a UTF-8 text file from a project-relative or absolute path."""
    file_path = _resolve_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {_format_path(file_path)}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {_format_path(file_path)}")

    content = file_path.read_text(encoding="utf-8")
    return _truncate_content(content)


@tool
def read_pdf(path: str) -> str:
    """Read text from a PDF file within the project root."""
    file_path = _resolve_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {_format_path(file_path)}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {_format_path(file_path)}")
    if file_path.suffix.lower() != ".pdf":
        raise ValueError(f"Path is not a PDF file: {_format_path(file_path)}")

    reader = PdfReader(str(file_path))
    page_texts: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            page_texts.append(f"[Page {index}]\n{text}")

    if not page_texts:
        return f"No extractable text found in {_format_path(file_path)}"

    return _truncate_content("\n\n".join(page_texts))


@tool
def read_docx(path: str) -> str:
    """Read paragraph text from a DOCX file within the project root."""
    file_path = _resolve_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {_format_path(file_path)}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {_format_path(file_path)}")
    if file_path.suffix.lower() != ".docx":
        raise ValueError(f"Path is not a DOCX file: {_format_path(file_path)}")

    try:
        with ZipFile(file_path) as archive:
            document_xml = archive.read("word/document.xml")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Invalid DOCX structure: {_format_path(file_path)}") from exc
    except BadZipFile as exc:
        raise ValueError(f"Invalid DOCX file: {_format_path(file_path)}") from exc

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
        return f"No extractable text found in {_format_path(file_path)}"

    return _truncate_content("\n\n".join(paragraphs))


@tool
def write_file(path: str, content: str) -> str:
    """Write UTF-8 text to a project-relative or absolute file path, creating parent directories if needed."""
    file_path = _resolve_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {_format_path(file_path)}"


TOOLS = [list_directory, read_file, read_pdf, read_docx, write_file]
