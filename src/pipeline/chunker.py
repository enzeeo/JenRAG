"""Chunk study documents into embeddable pieces.

Pipeline per document:
  1. Split at major LaTeX or Markdown section boundaries when possible.
  2. Sub-chunk oversized sections with overlap at paragraph/line breaks.
  3. Drop anything still below the minimum size.
  4. Prefix each chunk with document + section labels for the embedding model.
"""

import json
import os
import re
from dataclasses import dataclass, field

MAX_CHUNK_TOKENS = 512
MIN_CHUNK_TOKENS = 64
OVERLAP_TOKENS = 64
CHARS_PER_TOKEN = 4
MAX_CHUNK_CHARS = MAX_CHUNK_TOKENS * CHARS_PER_TOKEN
MIN_CHUNK_CHARS = MIN_CHUNK_TOKENS * CHARS_PER_TOKEN
OVERLAP_CHARS = OVERLAP_TOKENS * CHARS_PER_TOKEN

LATEX_SECTION_PATTERN = re.compile(
    r"\\(?P<command>section|subsection)\*?\{(?P<title>[^}]{1,160})\}"
)
MARKDOWN_SECTION_PATTERN = re.compile(
    r"^(?P<hashes>#{1,6})\s+(?P<title>[^\n#][^\n]{0,159})\s*$",
    re.MULTILINE,
)


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)

    def to_embed_text(self) -> str:
        title = self.metadata.get("title", "")
        section = self.metadata.get("section", "")
        prefix = f"{title} — {section}\n" if section else f"{title}\n"
        return prefix + self.text

    def __str__(self):
        tok = len(self.text) // CHARS_PER_TOKEN
        return f"[{tok} tok] {self.metadata} | {self.text[:120]}..."


def _normalize_section_title(raw_title: str) -> str:
    normalized_title = re.sub(r"\s+", " ", raw_title).strip()
    normalized_title = normalized_title.replace("\\", "")
    return normalized_title


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """Split LaTeX or Markdown source into (heading, body) pairs."""
    latex_matches = list(LATEX_SECTION_PATTERN.finditer(text))
    if latex_matches:
        return _split_with_heading_matches(text, latex_matches)

    markdown_matches = list(MARKDOWN_SECTION_PATTERN.finditer(text))
    if markdown_matches:
        return _split_with_heading_matches(text, markdown_matches)

    if not text.strip():
        return []

    return [("", text.strip())]


def _split_with_heading_matches(
    text: str,
    heading_matches: list[re.Match[str]],
) -> list[tuple[str, str]]:
    """Build section tuples from heading regex matches."""
    if not heading_matches:
        return [("", text.strip())] if text.strip() else []

    sections: list[tuple[str, str]] = []

    preamble = text[: heading_matches[0].start()].strip()
    if preamble:
        sections.append(("", preamble))

    for i, match in enumerate(heading_matches):
        heading = _normalize_section_title(match.group("title"))
        start = match.end()
        end = (
            heading_matches[i + 1].start()
            if i + 1 < len(heading_matches)
            else len(text)
        )
        body = text[start:end].strip()
        if body:
            sections.append((heading, body))

    return sections


_SENTENCE_END_RE = re.compile(r"[.!?]\s")


def _overlap_tail(text: str) -> str:
    """Return the last ~OVERLAP_CHARS of text, trimmed to a sentence boundary."""
    if len(text) <= OVERLAP_CHARS:
        return text
    window = text[-OVERLAP_CHARS:]
    m = _SENTENCE_END_RE.search(window)
    if m:
        return window[m.end():]
    return window


def _hard_split(text: str) -> list[str]:
    """Last-resort split for text with no paragraph/line breaks.
    Splits at sentence boundaries where possible."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + MAX_CHUNK_CHARS
        if end >= len(text):
            chunks.append(text[start:])
            break
        window = text[start:end]
        boundary = -1
        for m in _SENTENCE_END_RE.finditer(window):
            boundary = m.end()
        if boundary > MAX_CHUNK_CHARS // 2:
            end = start + boundary
        chunks.append(text[start:end])
        start = end
    return chunks


def _subchunk_text(text: str) -> list[str]:
    """Split oversized text into overlapping chunks.
    Tries paragraph breaks first, then line breaks, then sentence-aware hard split."""
    for sep in ("\n\n", "\n"):
        parts = [p.strip() for p in text.split(sep) if p.strip()]
        if len(parts) < 2:
            continue

        chunks: list[str] = []
        current = ""
        for part in parts:
            if len(part) > MAX_CHUNK_CHARS:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(_hard_split(part))
                continue
            candidate = f"{current}{sep}{part}".strip() if current else part
            if len(candidate) > MAX_CHUNK_CHARS and current:
                chunks.append(current)
                tail = _overlap_tail(current)
                current = f"{tail}{sep}{part}".strip()
            else:
                current = candidate
        if current:
            chunks.append(current)
        return chunks

    return _hard_split(text)


def chunk_document(
    title: str,
    text: str,
    base_metadata: dict | None = None,
) -> list[Chunk]:
    """Chunk a single document into embeddable pieces."""
    if not text.strip():
        return []

    sections = _split_into_sections(text)
    chunks: list[Chunk] = []
    shared_metadata = dict(base_metadata or {})
    shared_metadata["title"] = title

    for heading, body in sections:
        pieces = [body] if len(body) <= MAX_CHUNK_CHARS else _subchunk_text(body)
        for piece in pieces:
            if len(piece.strip()) < MIN_CHUNK_CHARS:
                continue
            metadata = dict(shared_metadata)
            metadata["section"] = heading
            chunks.append(
                Chunk(text=piece, metadata=metadata)
            )

    return chunks


def chunk_all_pages(
    pages: dict[str, str] | list[tuple[str, str, dict]],
) -> list[Chunk]:
    """Chunk all documents. Kept name for API compatibility with ingest pipeline."""
    if isinstance(pages, dict):
        return [
            chunk
            for title, text in pages.items()
            for chunk in chunk_document(title, text)
        ]

    return [
        chunk
        for title, text, metadata in pages
        for chunk in chunk_document(title, text, metadata)
    ]


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.pipeline.chunker <file.tex>")
        raise SystemExit(1)

    path = sys.argv[1]
    title = os.path.splitext(os.path.basename(path))[0]
    with open(path) as f:
        pages = {title: f.read()}

    chunks = chunk_all_pages(pages)

    if not chunks:
        print("No chunks produced — check that input contains \\section*{Problem #N}")
        raise SystemExit(1)

    sizes = sorted(len(c.text) // CHARS_PER_TOKEN for c in chunks)
    print(f"Documents: {len(pages)}")
    print(f"Chunks: {len(chunks)}")
    print(
        f"Tokens — min: {sizes[0]}, median: {sizes[len(sizes)//2]}, "
        f"max: {sizes[-1]}, avg: {sum(sizes)//len(sizes)}"
    )
    print()

    for lo, hi, label in [
        (0, 64, "< 64"),
        (64, 128, "64-128"),
        (128, 256, "128-256"),
        (256, 512, "256-512"),
        (512, 1024, "512-1K"),
        (1024, 99999, "1K+"),
    ]:
        count = sum(1 for s in sizes if lo <= s < hi)
        pct = count * 100 / len(sizes)
        print(f"  {label:>8}: {count:>6} ({pct:>5.1f}%) {'█' * int(pct / 2)}")
    print()

    seen_titles = set()
    for c in chunks:
        t = c.metadata["title"]
        if t not in seen_titles:
            seen_titles.add(t)
            sample = [ch for ch in chunks if ch.metadata["title"] == t]
            print(f"=== {t} ({len(sample)} chunks) ===")
            for ch in sample[:6]:
                tok = len(ch.text) // CHARS_PER_TOKEN
                sec = ch.metadata["section"] or "(preamble)"
                print(
                    f"  [{tok:>4} tok] {sec:30s} | "
                    f"{ch.text[:80].replace(chr(10), ' ')}"
                )
            if len(sample) > 6:
                print(f"  ... +{len(sample) - 6} more")
            print()
        if len(seen_titles) >= 5:
            break

    first_chunk = chunks[0]
    print("=== EMBED TEXT EXAMPLE ===")
    print(first_chunk.to_embed_text()[:500])
