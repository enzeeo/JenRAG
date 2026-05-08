from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


MARKDOWN_DIRECTORY_NAME = "md"
MARKDOWN_EXTENSION = ".md"
FILENAME_METADATA_PATTERN = re.compile(
    r"^(?P<course_category>[a-z]+)_(?P<course_number>\d{5})_"
    r"(?P<quarter>[a-z]+)_(?P<year>\d{4})_(?P<work_segment>.+)_(?P<author>[a-z-]+)$"
)
WORK_SEGMENT_PATTERN = re.compile(r"^(?P<work_type>[a-z]+?)(?P<work_number>\d+)?$")


@dataclass(frozen=True)
class CorpusDocument:
    title: str
    text: str
    metadata: dict[str, str]


def discover_corpus_paths(data_dir: str | Path) -> list[Path]:
    """Return structured Markdown corpus files from `data/md`."""
    root_path = Path(data_dir)
    if not root_path.exists():
        return []

    structured_root = root_path / MARKDOWN_DIRECTORY_NAME
    if not structured_root.exists():
        return []

    return sorted(
        path
        for path in structured_root.rglob("*")
        if path.is_file() and path.suffix.lower() == MARKDOWN_EXTENSION
    )


def load_corpus_documents(
    data_dir: str | Path,
) -> tuple[list[CorpusDocument], list[str]]:
    """Load structured Markdown corpus files."""
    root_path = Path(data_dir)
    warnings: list[str] = []
    discovered_paths = discover_corpus_paths(root_path)
    grouped_paths: dict[str, list[Path]] = {}

    for path in discovered_paths:
        grouped_paths.setdefault(build_document_group_key(root_path, path), []).append(path)

    documents: list[CorpusDocument] = []
    for group_key in sorted(grouped_paths):
        paths = sorted(grouped_paths[group_key], key=document_source_priority)
        chosen_path = paths[0]
        skipped_paths = paths[1:]
        if skipped_paths:
            skipped_labels = ", ".join(str(path.relative_to(root_path)) for path in skipped_paths)
            warnings.append(
                f"Skipped duplicate variants for {group_key}: {skipped_labels}"
            )

        document_text, extraction_warning = extract_document_text(chosen_path)
        if extraction_warning:
            warnings.append(extraction_warning)
        if not document_text.strip():
            warnings.append(
                f"Skipped {chosen_path.relative_to(root_path)} because no text could be extracted."
            )
            continue

        document_metadata = build_document_metadata(root_path, chosen_path)
        documents.append(
            CorpusDocument(
                title=str(document_metadata["title"]),
                text=document_text,
                metadata=document_metadata,
            )
        )

    return documents, warnings


def build_document_group_key(root_path: Path, path: Path) -> str:
    relative_path = path.relative_to(root_path)
    if len(relative_path.parts) >= 3 and relative_path.parts[0] == MARKDOWN_DIRECTORY_NAME:
        return f"{relative_path.parts[1]}/{path.stem}"
    return relative_path.stem


def document_source_priority(path: Path) -> tuple[int, str]:
    return (0, str(path))


def extract_document_text(path: Path) -> tuple[str, str | None]:
    suffix = path.suffix.lower()
    if suffix == MARKDOWN_EXTENSION:
        return path.read_text(encoding="utf-8"), None

    return "", f"Unsupported file type ignored: {path}"


def build_document_metadata(root_path: Path, path: Path) -> dict[str, str]:
    relative_path = path.relative_to(root_path)
    metadata: dict[str, str] = {
        "title": humanize_title_from_path(path),
        "source_path": str(relative_path),
        "source_extension": path.suffix.lower(),
        "document_stem": path.stem,
    }

    if len(relative_path.parts) >= 3 and relative_path.parts[0] == MARKDOWN_DIRECTORY_NAME:
        metadata["source_tree"] = relative_path.parts[0]
        metadata["course_folder"] = relative_path.parts[1]
        metadata.update(parse_structured_filename(path.stem))
    else:
        metadata["source_tree"] = "legacy"
        metadata["course_folder"] = ""

    if metadata.get("course_category") and metadata.get("course_number"):
        metadata["course_key"] = (
            f"{metadata['course_category']}_{metadata['course_number']}"
        )
    else:
        metadata["course_key"] = ""

    return metadata


def parse_structured_filename(file_stem: str) -> dict[str, str]:
    match = FILENAME_METADATA_PATTERN.fullmatch(file_stem)
    if not match:
        return {}

    work_segment = match.group("work_segment")
    work_match = WORK_SEGMENT_PATTERN.fullmatch(work_segment)

    metadata = {
        "course_category": match.group("course_category"),
        "course_number": match.group("course_number"),
        "quarter": match.group("quarter"),
        "year": match.group("year"),
        "work_segment": work_segment,
        "author": match.group("author"),
    }
    if work_match:
        metadata["work_type"] = work_match.group("work_type")
        metadata["work_number"] = work_match.group("work_number") or ""

    return metadata


def humanize_title_from_path(path: Path) -> str:
    parsed_metadata = parse_structured_filename(path.stem)
    if not parsed_metadata:
        return path.stem.replace("_", " ")

    course_label = (
        f"{parsed_metadata['course_category'].upper()} {parsed_metadata['course_number']}"
    )
    work_segment = parsed_metadata.get("work_segment", path.stem).replace("_", " ")
    author = parsed_metadata.get("author", "")
    return (
        f"{course_label} {parsed_metadata['quarter']} {parsed_metadata['year']} "
        f"{work_segment} {author}"
    ).strip()
