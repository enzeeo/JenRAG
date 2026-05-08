"""Commands for converting raw PDF and LaTeX study files into canonical Markdown."""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

from src.pipeline.config import DATA_DIR
from src.pipeline.conversion import (
    convert_latex_file_to_markdown,
    convert_pdf_file_to_markdown,
)

MARKDOWN_DIRECTORY_NAME = "md"
LATEX_SOURCE_DIRECTORIES = ["latex", "unmatched-tex"]
PDF_SOURCE_DIRECTORIES = ["pdf", "unmatched-pdf"]
SUPPORTED_SOURCE_TYPES = {"all", "tex", "pdf"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConversionCandidate:
    source_path: Path
    markdown_target_path: Path
    source_type: str


def main_convert_missing() -> None:
    """Convert every raw source file whose canonical Markdown target is still missing."""
    parser = argparse.ArgumentParser(description="Convert missing raw sources into Markdown.")
    parser.add_argument(
        "--source-type",
        choices=sorted(SUPPORTED_SOURCE_TYPES),
        default="all",
        help="Filter conversion to tex only, pdf only, or both.",
    )
    args = parser.parse_args()

    candidates = discover_missing_conversion_candidates(
        data_dir=DATA_DIR,
        source_type=args.source_type,
    )
    convert_candidates(candidates)


def main_convert_files() -> None:
    """Convert only requested raw source files whose Markdown targets are still missing."""
    parser = argparse.ArgumentParser(description="Convert specific raw files into Markdown.")
    parser.add_argument(
        "--source-type",
        choices=sorted(SUPPORTED_SOURCE_TYPES),
        default="all",
        help="Filter conversion to tex only, pdf only, or both.",
    )
    parser.add_argument(
        "--path",
        dest="paths",
        action="append",
        required=True,
        help="Raw source path under data/latex, data/pdf, data/unmatched-tex, or data/unmatched-pdf.",
    )
    args = parser.parse_args()

    candidates = build_requested_conversion_candidates(
        data_dir=DATA_DIR,
        requested_paths=args.paths,
        source_type=args.source_type,
    )
    convert_candidates(candidates)


def discover_missing_conversion_candidates(
    data_dir: str | Path,
    source_type: str,
) -> list[ConversionCandidate]:
    """Scan raw source trees and return candidates whose Markdown targets do not exist."""
    data_root = Path(data_dir)
    all_candidates: list[ConversionCandidate] = []
    for source_path in discover_raw_source_paths(data_root, source_type=source_type):
        all_candidates.append(build_conversion_candidate(data_root, source_path))
    return filter_missing_candidates(all_candidates)


def build_requested_conversion_candidates(
    data_dir: str | Path,
    requested_paths: list[str],
    source_type: str,
) -> list[ConversionCandidate]:
    """Validate and normalize requested raw source paths."""
    data_root = Path(data_dir)
    candidates = [
        build_conversion_candidate(data_root, resolve_requested_raw_source_path(data_root, raw_path, source_type))
        for raw_path in requested_paths
    ]
    return filter_missing_candidates(candidates)


def filter_missing_candidates(
    candidates: list[ConversionCandidate],
) -> list[ConversionCandidate]:
    """Skip targets that already exist and deduplicate by canonical Markdown output path."""
    chosen_candidates_by_target: dict[Path, ConversionCandidate] = {}
    for candidate in sorted(candidates, key=conversion_candidate_sort_key):
        if candidate.markdown_target_path.exists():
            log.info("Skipping %s because %s already exists.", candidate.source_path, candidate.markdown_target_path)
            continue
        existing_candidate = chosen_candidates_by_target.get(candidate.markdown_target_path)
        if existing_candidate is None:
            chosen_candidates_by_target[candidate.markdown_target_path] = candidate
            continue
        if conversion_candidate_sort_key(candidate) < conversion_candidate_sort_key(existing_candidate):
            chosen_candidates_by_target[candidate.markdown_target_path] = candidate
    return sorted(chosen_candidates_by_target.values(), key=lambda candidate: str(candidate.source_path))


def discover_raw_source_paths(data_root: Path, source_type: str) -> list[Path]:
    """Discover raw `.tex` and `.pdf` source files from matched and unmatched trees."""
    normalized_source_type = normalize_source_type(source_type)
    source_paths: list[Path] = []

    if normalized_source_type in {"all", "tex"}:
        for directory_name in LATEX_SOURCE_DIRECTORIES:
            directory_path = data_root / directory_name
            if directory_path.exists():
                source_paths.extend(sorted(directory_path.rglob("*.tex")))

    if normalized_source_type in {"all", "pdf"}:
        for directory_name in PDF_SOURCE_DIRECTORIES:
            directory_path = data_root / directory_name
            if directory_path.exists():
                source_paths.extend(sorted(directory_path.rglob("*.pdf")))

    return sorted(source_paths)


def resolve_requested_raw_source_path(
    data_root: Path,
    requested_path: str,
    source_type: str,
) -> Path:
    """Resolve one requested raw source path and validate source-type constraints."""
    candidate_path = Path(requested_path)
    if not candidate_path.is_absolute():
        candidate_path = data_root / candidate_path

    normalized_candidate_path = candidate_path.resolve(strict=False)
    try:
        relative_path = normalized_candidate_path.relative_to(data_root.resolve())
    except ValueError as error:
        raise ValueError(
            f"Requested raw path must stay inside {data_root}: {requested_path}"
        ) from error

    if not normalized_candidate_path.exists():
        raise ValueError(f"Requested raw path does not exist: {requested_path}")
    if not normalized_candidate_path.is_file():
        raise ValueError(f"Requested raw path is not a file: {requested_path}")

    detected_source_type = detect_source_type_from_path(relative_path)
    normalized_source_type = normalize_source_type(source_type)
    if normalized_source_type != "all" and detected_source_type != normalized_source_type:
        raise ValueError(
            f"Requested raw path {requested_path} does not match --source-type {normalized_source_type}."
        )

    return normalized_candidate_path


def build_conversion_candidate(data_root: Path, source_path: Path) -> ConversionCandidate:
    """Build source-path to Markdown-target mapping for one raw file."""
    relative_source_path = source_path.resolve(strict=False).relative_to(data_root.resolve())
    course_folder = relative_source_path.parts[1]
    markdown_target_path = (
        data_root
        / MARKDOWN_DIRECTORY_NAME
        / course_folder
        / f"{source_path.stem}.md"
    )
    return ConversionCandidate(
        source_path=source_path,
        markdown_target_path=markdown_target_path,
        source_type=detect_source_type_from_path(relative_source_path),
    )


def detect_source_type_from_path(relative_source_path: Path) -> str:
    """Map a raw source path to `tex` or `pdf`."""
    if len(relative_source_path.parts) < 3:
        raise ValueError(f"Raw source path must include source tree and course folder: {relative_source_path}")
    top_level_directory = relative_source_path.parts[0]
    if top_level_directory in LATEX_SOURCE_DIRECTORIES:
        return "tex"
    if top_level_directory in PDF_SOURCE_DIRECTORIES:
        return "pdf"
    raise ValueError(f"Unsupported raw source directory: {relative_source_path}")


def conversion_candidate_sort_key(candidate: ConversionCandidate) -> tuple[int, str]:
    """Prefer LaTeX over PDF when both map to the same Markdown target."""
    source_priority = 0 if candidate.source_type == "tex" else 1
    return (source_priority, str(candidate.source_path))


def normalize_source_type(source_type: str) -> str:
    """Normalize and validate source type filter."""
    normalized_source_type = source_type.strip().lower()
    if normalized_source_type not in SUPPORTED_SOURCE_TYPES:
        raise ValueError(f"Unsupported source type: {source_type}")
    return normalized_source_type


def convert_candidates(candidates: list[ConversionCandidate]) -> None:
    """Convert candidate raw source files and write Markdown outputs."""
    if not candidates:
        log.info("No raw files needed conversion.")
        return

    for candidate in candidates:
        log.info("Converting %s -> %s", candidate.source_path, candidate.markdown_target_path)
        if candidate.source_type == "tex":
            markdown_text = convert_latex_file_to_markdown(candidate.source_path)
        else:
            markdown_text = convert_pdf_file_to_markdown(candidate.source_path)
        candidate.markdown_target_path.parent.mkdir(parents=True, exist_ok=True)
        candidate.markdown_target_path.write_text(markdown_text, encoding="utf-8")

    log.info("Converted %s raw files into Markdown.", len(candidates))

