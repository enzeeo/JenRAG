from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging
import re
import sqlite3
import sys

from src.pipeline.chunker import Chunk, chunk_document
from src.pipeline.config import DATA_DIR, WIKI_DB_PATH, WIKI_REPORT_PATH
from src.pipeline.corpus import CorpusDocument, load_corpus_documents

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

MIN_SUMMARY_SENTENCES = 2
MAX_SUMMARY_CHARACTERS = 480
MAX_BODY_CHARACTERS = 2200
MAX_RELATED_LINKS = 6
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "use",
    "with",
}
GENERIC_SECTION_PATTERN = re.compile(
    r"^(solutions?|problem\s*#?\s*\d+|exercise[\w\s.,-]*problem\s*\d+)$",
    re.IGNORECASE,
)
LATEX_COMMAND_PATTERN = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class WikiPage:
    slug: str
    title: str
    page_type: str
    summary: str
    body: str
    course_key: str
    source_path: str
    source_title: str
    aliases: list[str]
    section: str


def slugify(value: str) -> str:
    normalized_value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized_value or "page"


def strip_latex_markup(text: str) -> str:
    cleaned_text = LATEX_COMMAND_PATTERN.sub(" ", text)
    cleaned_text = cleaned_text.replace("{", " ").replace("}", " ")
    cleaned_text = cleaned_text.replace("$", " ")
    cleaned_text = re.sub(r"\s+", " ", cleaned_text)
    return cleaned_text.strip()


def split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def build_summary(text: str) -> str:
    sentences = split_sentences(strip_latex_markup(text))
    if not sentences:
        return ""

    selected_sentences: list[str] = []
    total_length = 0
    for sentence in sentences:
        selected_sentences.append(sentence)
        total_length += len(sentence)
        if len(selected_sentences) >= MIN_SUMMARY_SENTENCES or total_length >= MAX_SUMMARY_CHARACTERS:
            break
    return " ".join(selected_sentences)[:MAX_SUMMARY_CHARACTERS].strip()


def build_body(text: str) -> str:
    cleaned_text = strip_latex_markup(text)
    return cleaned_text[:MAX_BODY_CHARACTERS].strip()


def tokenize(value: str) -> set[str]:
    return {
        token
        for token in TOKEN_PATTERN.findall(value.lower())
        if len(token) > 2 and token not in STOP_WORDS
    }


def title_aliases(document: CorpusDocument, section: str) -> list[str]:
    aliases = {document.title}
    if section:
        aliases.add(section)
        aliases.add(f"{document.title} {section}")
    work_segment = document.metadata.get("work_segment", "")
    if work_segment:
        aliases.add(work_segment.replace("_", " "))
    course_key = document.metadata.get("course_key", "")
    if course_key:
        aliases.add(course_key.replace("_", " ").upper())
    return sorted(alias for alias in aliases if alias)


def build_course_page(documents: list[CorpusDocument], course_key: str) -> WikiPage:
    course_documents = [document for document in documents if document.metadata.get("course_key") == course_key]
    source_document = course_documents[0]
    document_titles = [document.title for document in course_documents]
    summary = (
        f"{course_key.replace('_', ' ').upper()} study graph built from "
        f"{len(course_documents)} source documents."
    )
    body_lines = [summary, "", "Included documents:"]
    body_lines.extend(f"- {title}" for title in document_titles)
    return WikiPage(
        slug=f"course/{slugify(course_key)}",
        title=course_key.replace("_", " ").upper(),
        page_type="course",
        summary=summary,
        body="\n".join(body_lines),
        course_key=course_key,
        source_path=source_document.metadata.get("source_path", ""),
        source_title=source_document.title,
        aliases=[course_key, course_key.replace("_", " ").upper()],
        section="",
    )


def build_document_page(document: CorpusDocument) -> WikiPage:
    summary = build_summary(document.text)
    if not summary:
        summary = f"Study material from {document.title}."
    return WikiPage(
        slug=f"document/{slugify(document.metadata.get('document_stem', document.title))}",
        title=document.title,
        page_type="document",
        summary=summary,
        body=build_body(document.text),
        course_key=document.metadata.get("course_key", ""),
        source_path=document.metadata.get("source_path", ""),
        source_title=document.title,
        aliases=title_aliases(document, ""),
        section="",
    )


def build_section_pages(document: CorpusDocument) -> list[WikiPage]:
    section_chunks = chunk_document(
        document.title,
        document.text,
        base_metadata=document.metadata,
    )
    pages: list[WikiPage] = []

    for chunk_index, chunk in enumerate(section_chunks, start=1):
        section_title = chunk.metadata.get("section", "").strip()
        if not section_title:
            continue

        display_title = section_title
        if GENERIC_SECTION_PATTERN.fullmatch(section_title):
            display_title = f"{document.title} — {section_title}"

        pages.append(
            WikiPage(
                slug=(
                    f"section/{slugify(document.metadata.get('document_stem', document.title))}"
                    f"-{chunk_index}-{slugify(section_title)}"
                ),
                title=display_title,
                page_type="section",
                summary=build_summary(chunk.text) or f"Section from {document.title}.",
                body=build_body(chunk.text),
                course_key=document.metadata.get("course_key", ""),
                source_path=document.metadata.get("source_path", ""),
                source_title=document.title,
                aliases=title_aliases(document, section_title),
                section=section_title,
            )
        )

    return pages


def build_wiki_pages(documents: list[CorpusDocument]) -> list[WikiPage]:
    pages: list[WikiPage] = []
    course_keys = sorted(
        {
            document.metadata.get("course_key", "")
            for document in documents
            if document.metadata.get("course_key", "")
        }
    )

    for course_key in course_keys:
        pages.append(build_course_page(documents, course_key))

    for document in documents:
        pages.append(build_document_page(document))
        pages.extend(build_section_pages(document))

    return pages


def build_page_links(pages: list[WikiPage]) -> list[tuple[str, str, str]]:
    links: set[tuple[str, str, str]] = set()
    pages_by_course: dict[str, list[WikiPage]] = {}
    pages_by_source: dict[str, list[WikiPage]] = {}

    for page in pages:
        pages_by_course.setdefault(page.course_key, []).append(page)
        pages_by_source.setdefault(page.source_path, []).append(page)

    course_pages = {
        page.course_key: page
        for page in pages
        if page.page_type == "course" and page.course_key
    }
    document_pages = {
        page.source_path: page
        for page in pages
        if page.page_type == "document"
    }

    for source_path, source_pages in pages_by_source.items():
        document_page = document_pages.get(source_path)
        if document_page is None:
            continue

        course_page = course_pages.get(document_page.course_key)
        if course_page is not None:
            links.add((document_page.slug, course_page.slug, "belongs_to_course"))
            links.add((course_page.slug, document_page.slug, "has_document"))

        section_pages = [page for page in source_pages if page.page_type == "section"]
        for section_page in section_pages:
            links.add((document_page.slug, section_page.slug, "has_section"))
            links.add((section_page.slug, document_page.slug, "section_of"))
            if course_page is not None:
                links.add((section_page.slug, course_page.slug, "in_course"))

        for current_page, next_page in zip(section_pages, section_pages[1:]):
            links.add((current_page.slug, next_page.slug, "next_section"))
            links.add((next_page.slug, current_page.slug, "previous_section"))

    for course_key, course_pages_in_group in pages_by_course.items():
        if not course_key:
            continue
        section_pages = [page for page in course_pages_in_group if page.page_type == "section"]
        for page in section_pages:
            scored_related_pages: list[tuple[int, str]] = []
            page_tokens = tokenize(page.title + " " + page.summary)
            if not page_tokens:
                continue

            for candidate in section_pages:
                if candidate.slug == page.slug:
                    continue
                overlap_size = len(page_tokens & tokenize(candidate.title + " " + candidate.summary))
                if overlap_size >= 2:
                    scored_related_pages.append((overlap_size, candidate.slug))

            scored_related_pages.sort(reverse=True)
            for _, related_slug in scored_related_pages[:MAX_RELATED_LINKS]:
                links.add((page.slug, related_slug, "related_topic"))

    return sorted(links)


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DROP TABLE IF EXISTS page_links;
        DROP TABLE IF EXISTS page_aliases;
        DROP TABLE IF EXISTS page_sources;
        DROP TABLE IF EXISTS pages;

        CREATE TABLE pages (
            slug TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            page_type TEXT NOT NULL,
            summary TEXT NOT NULL,
            body TEXT NOT NULL,
            course_key TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_title TEXT NOT NULL,
            section TEXT NOT NULL
        );

        CREATE TABLE page_aliases (
            page_slug TEXT NOT NULL,
            alias TEXT NOT NULL
        );

        CREATE TABLE page_sources (
            page_slug TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_title TEXT NOT NULL
        );

        CREATE TABLE page_links (
            from_slug TEXT NOT NULL,
            to_slug TEXT NOT NULL,
            relation TEXT NOT NULL
        );
        """
    )


def write_database(database_path: str | Path, pages: list[WikiPage], links: list[tuple[str, str, str]]) -> None:
    output_path = Path(database_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(output_path) as connection:
        initialize_database(connection)
        connection.executemany(
            """
            INSERT INTO pages (
                slug, title, page_type, summary, body, course_key, source_path, source_title, section
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    page.slug,
                    page.title,
                    page.page_type,
                    page.summary,
                    page.body,
                    page.course_key,
                    page.source_path,
                    page.source_title,
                    page.section,
                )
                for page in pages
            ],
        )
        connection.executemany(
            "INSERT INTO page_aliases (page_slug, alias) VALUES (?, ?)",
            [
                (page.slug, alias)
                for page in pages
                for alias in page.aliases
            ],
        )
        connection.executemany(
            "INSERT INTO page_sources (page_slug, source_path, source_title) VALUES (?, ?, ?)",
            [
                (page.slug, page.source_path, page.source_title)
                for page in pages
            ],
        )
        connection.executemany(
            "INSERT INTO page_links (from_slug, to_slug, relation) VALUES (?, ?, ?)",
            links,
        )
        connection.commit()


def build_report(
    documents: list[CorpusDocument],
    pages: list[WikiPage],
    links: list[tuple[str, str, str]],
    warnings: list[str],
) -> str:
    page_type_counts: dict[str, int] = {}
    for page in pages:
        page_type_counts[page.page_type] = page_type_counts.get(page.page_type, 0) + 1

    lines = [
        "# StudyGraph Wiki Report",
        "",
        "## Summary",
        "",
        f"- Source documents scanned: {len(documents)}",
        f"- Wiki pages created: {len(pages)}",
        f"- Wiki links created: {len(links)}",
        "",
        "## Page Types",
        "",
    ]

    for page_type, count in sorted(page_type_counts.items()):
        lines.append(f"- {page_type}: {count}")

    lines.extend(
        [
            "",
            "## Source Documents",
            "",
        ]
    )
    for document in documents:
        lines.append(
            f"- `{document.metadata.get('source_path', '')}` -> {document.title}"
        )

    lines.extend(
        [
            "",
            "## Sample Pages",
            "",
        ]
    )
    for page in pages[:12]:
        lines.append(f"- `{page.slug}`: {page.title}")
        lines.append(f"  Summary: {page.summary}")

    lines.extend(
        [
            "",
            "## Warnings",
            "",
        ]
    )
    if warnings:
        lines.extend(f"- {warning_message}" for warning_message in warnings)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Review Checklist",
            "",
            "- Check for duplicated or weak section pages.",
            "- Check whether related-topic links look reasonable for each course.",
            "- Check whether upload metadata produced the right course grouping and source mappings.",
            "- If a generated page is suspicious, cite the source path before editing or replacing it.",
        ]
    )

    return "\n".join(lines) + "\n"


def write_report(report_path: str | Path, report_text: str) -> None:
    output_path = Path(report_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")


def build_wiki(
    data_dir: str = DATA_DIR,
    database_path: str = WIKI_DB_PATH,
    report_path: str = WIKI_REPORT_PATH,
) -> tuple[list[WikiPage], list[tuple[str, str, str]], list[str]]:
    documents, warnings = load_corpus_documents(data_dir)
    if not documents:
        raise ValueError(f"No supported study documents found in {data_dir}.")

    pages = build_wiki_pages(documents)
    links = build_page_links(pages)
    write_database(database_path, pages, links)
    report_text = build_report(documents, pages, links, warnings)
    write_report(report_path, report_text)
    return pages, links, warnings


def main() -> None:
    try:
        pages, links, warnings = build_wiki()
    except Exception as error:
        log.error("Wiki build failed: %s", error)
        sys.exit(1)

    log.info(
        "Built wiki with %s pages, %s links, %s warnings",
        len(pages),
        len(links),
        len(warnings),
    )
    log.info("Wrote wiki database to %s", WIKI_DB_PATH)
    log.info("Wrote wiki report to %s", WIKI_REPORT_PATH)


if __name__ == "__main__":
    main()
