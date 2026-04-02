"""Project-scoped filesystem and office document tools."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from posixpath import normpath
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

WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
SPREADSHEET_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
SPREADSHEET_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DRAWINGML_NAMESPACE = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
MAX_SPREADSHEET_PREVIEW_ROWS = 20
MAX_BATCH_FILES = 12
SUPPORTED_BATCH_SUFFIXES = {".txt", ".md", ".pdf", ".docx", ".xlsx", ".pptx"}


def _read_archive_xml(archive: ZipFile, member: str, *, missing_message: str) -> ElementTree.Element:
    try:
        payload = archive.read(member)
    except KeyError as exc:
        raise FileNotFoundError(missing_message) from exc
    return ElementTree.fromstring(payload)


def _normalize_archive_member(base_dir: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return normpath(f"{base_dir}/{target}")


def _read_text_file(file_path: Path) -> str:
    return truncate_content(file_path.read_text(encoding="utf-8"))


def _read_pdf_text(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    page_texts: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            page_texts.append(f"[Page {index}]\n{text}")

    if not page_texts:
        return f"No extractable text found in {format_project_path(file_path)}"

    return truncate_content("\n\n".join(page_texts))


def _read_docx_text(file_path: Path) -> str:
    try:
        with ZipFile(file_path) as archive:
            root = _read_archive_xml(
                archive,
                "word/document.xml",
                missing_message=f"Invalid DOCX structure: {format_project_path(file_path)}",
            )
    except BadZipFile as exc:
        raise ValueError(f"Invalid DOCX file: {format_project_path(file_path)}") from exc

    body = root.find("./w:body", WORD_NAMESPACE)
    if body is None:
        return f"No extractable text found in {format_project_path(file_path)}"

    blocks: list[str] = []
    table_index = 0
    for child in list(body):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            texts = [node.text or "" for node in child.findall(".//w:t", WORD_NAMESPACE)]
            line = "".join(texts).strip()
            if not line:
                continue

            style_node = child.find("./w:pPr/w:pStyle", WORD_NAMESPACE)
            style_value = ""
            if style_node is not None:
                style_value = style_node.attrib.get(f"{{{WORD_NAMESPACE['w']}}}val", "").strip()

            if style_value.lower().startswith("heading"):
                blocks.append(f"[{style_value}] {line}")
            else:
                blocks.append(line)
        elif tag == "tbl":
            table_index += 1
            row_texts: list[str] = []
            for row in child.findall("./w:tr", WORD_NAMESPACE):
                cells: list[str] = []
                for cell in row.findall("./w:tc", WORD_NAMESPACE):
                    fragments = [node.text or "" for node in cell.findall(".//w:t", WORD_NAMESPACE)]
                    cells.append("".join(fragments).strip())
                if any(cell.strip() for cell in cells):
                    row_texts.append(" | ".join(cells))
            if row_texts:
                blocks.append(f"[Table {table_index}]\n" + "\n".join(row_texts))

    if not blocks:
        return f"No extractable text found in {format_project_path(file_path)}"

    return truncate_content("\n\n".join(blocks))


def _column_letters_to_index(column_letters: str) -> int:
    value = 0
    for char in column_letters.upper():
        if "A" <= char <= "Z":
            value = value * 26 + (ord(char) - ord("A") + 1)
    return max(value - 1, 0)


def _parse_cell_reference(reference: str) -> tuple[int, int]:
    letters = "".join(char for char in reference if char.isalpha())
    digits = "".join(char for char in reference if char.isdigit())
    column_index = _column_letters_to_index(letters)
    row_index = max(int(digits) - 1, 0) if digits else 0
    return row_index, column_index


def _load_shared_strings(archive: ZipFile) -> list[str]:
    try:
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []

    namespace = {"s": SPREADSHEET_MAIN_NS}
    values: list[str] = []
    for string_item in root.findall(".//s:si", namespace):
        fragments = [node.text or "" for node in string_item.findall(".//s:t", namespace)]
        values.append("".join(fragments))
    return values


def _extract_cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    value_node = cell.find(f"{{{SPREADSHEET_MAIN_NS}}}v")
    if value_node is None:
        inline_texts = [node.text or "" for node in cell.findall(f".//{{{SPREADSHEET_MAIN_NS}}}t")]
        return "".join(inline_texts).strip()

    raw_value = value_node.text or ""
    data_type = cell.attrib.get("t", "")
    if data_type == "s":
        try:
            return shared_strings[int(raw_value)]
        except (ValueError, IndexError):
            return raw_value
    if data_type == "b":
        return "TRUE" if raw_value == "1" else "FALSE"
    return raw_value


def _read_xlsx_text(file_path: Path, *, max_preview_rows: int = MAX_SPREADSHEET_PREVIEW_ROWS) -> str:
    try:
        with ZipFile(file_path) as archive:
            workbook_root = _read_archive_xml(
                archive,
                "xl/workbook.xml",
                missing_message=f"Invalid XLSX structure: {format_project_path(file_path)}",
            )
            workbook_rels_root = _read_archive_xml(
                archive,
                "xl/_rels/workbook.xml.rels",
                missing_message=f"Invalid XLSX relationships: {format_project_path(file_path)}",
            )
            shared_strings = _load_shared_strings(archive)

            rel_map: dict[str, str] = {}
            for relation in workbook_rels_root.findall(f"{{{PACKAGE_REL_NS}}}Relationship"):
                rel_id = relation.attrib.get("Id", "")
                target = relation.attrib.get("Target", "")
                if rel_id and target:
                    rel_map[rel_id] = target.lstrip("/")

            namespace = {"s": SPREADSHEET_MAIN_NS, "r": SPREADSHEET_REL_NS}
            sheet_nodes = workbook_root.findall(".//s:sheets/s:sheet", namespace)
            if not sheet_nodes:
                return f"No worksheets found in {format_project_path(file_path)}"

            rendered_sheets: list[str] = []
            for sheet_index, sheet in enumerate(sheet_nodes, start=1):
                sheet_name = sheet.attrib.get("name", f"Sheet {sheet_index}")
                rel_id = sheet.attrib.get(f"{{{SPREADSHEET_REL_NS}}}id", "")
                target = rel_map.get(rel_id)
                if not target:
                    rendered_sheets.append(f"[Sheet {sheet_index}] {sheet_name}\nStatus: missing worksheet data")
                    continue

                sheet_path = _normalize_archive_member("xl", target)
                sheet_root = _read_archive_xml(
                    archive,
                    sheet_path,
                    missing_message=f"Worksheet data missing for {sheet_name} in {format_project_path(file_path)}",
                )

                rows_by_index: dict[int, dict[int, str]] = defaultdict(dict)
                max_column_index = 0
                for row in sheet_root.findall(f".//{{{SPREADSHEET_MAIN_NS}}}sheetData/{{{SPREADSHEET_MAIN_NS}}}row"):
                    for cell in row.findall(f"{{{SPREADSHEET_MAIN_NS}}}c"):
                        reference = cell.attrib.get("r", "")
                        row_index, column_index = _parse_cell_reference(reference)
                        rows_by_index[row_index][column_index] = _extract_cell_value(cell, shared_strings)
                        max_column_index = max(max_column_index, column_index)

                ordered_rows = sorted(rows_by_index.items())
                lines = [f"[Sheet {sheet_index}] {sheet_name}", f"Rows with data: {len(ordered_rows)}"]
                if not ordered_rows:
                    lines.append("Status: empty sheet")
                    rendered_sheets.append("\n".join(lines))
                    continue

                visible_rows = ordered_rows[:max_preview_rows]
                lines.append(f"Preview rows ({len(visible_rows)}):")
                for row_number, row_values in visible_rows:
                    cells = [row_values.get(column_index, "") for column_index in range(max_column_index + 1)]
                    while cells and not cells[-1]:
                        cells.pop()
                    lines.append(f"- Row {row_number + 1}: " + " | ".join(cells or [""]))

                if len(ordered_rows) > max_preview_rows:
                    lines.append(
                        f"Truncated: showing first {max_preview_rows} of {len(ordered_rows)} rows with data"
                    )
                rendered_sheets.append("\n".join(lines))
    except BadZipFile as exc:
        raise ValueError(f"Invalid XLSX file: {format_project_path(file_path)}") from exc

    return truncate_content("\n\n".join(rendered_sheets))


def _slide_sort_key(name: str) -> int:
    stem = name.rsplit("/", 1)[-1]
    digits = "".join(char for char in stem if char.isdigit())
    return int(digits or "0")


def _read_pptx_text(file_path: Path) -> str:
    try:
        with ZipFile(file_path) as archive:
            slide_names = sorted(
                (
                    name
                    for name in archive.namelist()
                    if name.startswith("ppt/slides/slide") and name.endswith(".xml")
                ),
                key=_slide_sort_key,
            )
            if not slide_names:
                return f"No slides found in {format_project_path(file_path)}"

            rendered_slides: list[str] = []
            for slide_index, slide_name in enumerate(slide_names, start=1):
                root = ElementTree.fromstring(archive.read(slide_name))
                texts = [node.text or "" for node in root.findall(".//a:t", DRAWINGML_NAMESPACE)]
                visible_lines = [text.strip() for text in texts if text and text.strip()]
                if visible_lines:
                    rendered_slides.append(f"[Slide {slide_index}]\n" + "\n".join(visible_lines))
                else:
                    rendered_slides.append(f"[Slide {slide_index}]\nNo extractable text found")
    except BadZipFile as exc:
        raise ValueError(f"Invalid PPTX file: {format_project_path(file_path)}") from exc

    return truncate_content("\n\n".join(rendered_slides))


def _read_supported_document(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return _read_text_file(file_path)
    if suffix == ".pdf":
        return _read_pdf_text(file_path)
    if suffix == ".docx":
        return _read_docx_text(file_path)
    if suffix == ".xlsx":
        return _read_xlsx_text(file_path)
    if suffix == ".pptx":
        return _read_pptx_text(file_path)
    raise ValueError(f"Unsupported document type: {format_project_path(file_path)}")


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
        return f"Directory: {format_project_path(directory)}\nStatus: empty"

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
        lines.append(f"Truncated: showing first {MAX_LIST_ENTRIES} of {len(entries)} entries")

    return "\n".join(lines)


@tool
def read_file(path: str) -> str:
    """Read a UTF-8 text file from a project-relative or absolute path."""
    file_path = resolve_project_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {format_project_path(file_path)}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {format_project_path(file_path)}")

    return _read_text_file(file_path)


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

    return _read_pdf_text(file_path)


@tool
def read_docx(path: str) -> str:
    """Read paragraph and table text from a DOCX file within the project root."""
    file_path = resolve_project_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {format_project_path(file_path)}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {format_project_path(file_path)}")
    if file_path.suffix.lower() != ".docx":
        raise ValueError(f"Path is not a DOCX file: {format_project_path(file_path)}")

    return _read_docx_text(file_path)


@tool
def read_xlsx(path: str, max_preview_rows: int = MAX_SPREADSHEET_PREVIEW_ROWS) -> str:
    """Read worksheet names and preview rows from an XLSX file within the project root."""
    if max_preview_rows < 1 or max_preview_rows > 100:
        raise ValueError("max_preview_rows must be between 1 and 100.")

    file_path = resolve_project_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {format_project_path(file_path)}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {format_project_path(file_path)}")
    if file_path.suffix.lower() != ".xlsx":
        raise ValueError(f"Path is not an XLSX file: {format_project_path(file_path)}")

    return _read_xlsx_text(file_path, max_preview_rows=max_preview_rows)


@tool
def read_pptx(path: str) -> str:
    """Read slide text from a PPTX file within the project root."""
    file_path = resolve_project_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {format_project_path(file_path)}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {format_project_path(file_path)}")
    if file_path.suffix.lower() != ".pptx":
        raise ValueError(f"Path is not a PPTX file: {format_project_path(file_path)}")

    return _read_pptx_text(file_path)


@tool
def batch_read_documents(path: str, max_files: int = 5) -> str:
    """Read a small batch of supported documents from a directory and return per-file previews."""
    if max_files < 1 or max_files > MAX_BATCH_FILES:
        raise ValueError(f"max_files must be between 1 and {MAX_BATCH_FILES}.")

    directory = resolve_project_path(path)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {format_project_path(directory)}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {format_project_path(directory)}")

    files = sorted(
        (
            file_path
            for file_path in directory.iterdir()
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_BATCH_SUFFIXES
        ),
        key=lambda file_path: file_path.name.lower(),
    )
    if not files:
        return (
            f"Directory: {format_project_path(directory)}\n"
            f"Supported files: none ({', '.join(sorted(SUPPORTED_BATCH_SUFFIXES))})"
        )

    selected_files = files[:max_files]
    blocks = [
        f"Directory: {format_project_path(directory)}",
        f"Supported files found: {len(files)}",
        f"Files included: {len(selected_files)}",
    ]

    for index, file_path in enumerate(selected_files, start=1):
        blocks.append(f"[Document {index}] {format_project_path(file_path)}")
        blocks.append(_read_supported_document(file_path))

    if len(files) > max_files:
        blocks.append(f"Truncated: showing first {max_files} of {len(files)} supported files")

    return truncate_content("\n\n".join(blocks))


@tool
def write_file(path: str, content: str) -> str:
    """Write UTF-8 text to a project-relative or absolute file path, creating parent directories if needed."""
    file_path = resolve_project_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {format_project_path(file_path)}"


TOOLS = [
    list_directory,
    read_file,
    read_pdf,
    read_docx,
    read_xlsx,
    read_pptx,
    batch_read_documents,
    write_file,
]
