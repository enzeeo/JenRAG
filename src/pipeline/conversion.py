"""OpenAI-compatible raw-source to Markdown conversion helpers."""

from __future__ import annotations

import logging
from pathlib import Path

from .config import (
    CHAT_MODEL,
    CONVERSION_MAX_TOKENS,
    CONVERSION_MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

_client = None

CONVERSION_SYSTEM_PROMPT = """\
You convert course material into faithful Markdown for a study corpus.

Rules:
- Preserve source meaning. Do not invent missing content.
- Use concise Markdown headings and lists when structure is obvious.
- Keep equations in LaTeX math syntax when present.
- Remove boilerplate that does not help study or retrieval.
- If source text is incomplete or noisy, keep only reliable content.
- Return Markdown only. No code fences. No explanations outside converted content.
"""


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        client_kwargs: dict = {"api_key": OPENAI_API_KEY}
        if OPENAI_BASE_URL:
            client_kwargs["base_url"] = OPENAI_BASE_URL
        _client = OpenAI(**client_kwargs)
    return _client


def convert_latex_file_to_markdown(file_path: str | Path) -> str:
    """Convert a LaTeX file into canonical Markdown."""
    source_path = Path(file_path)
    latex_text = source_path.read_text(encoding="utf-8")
    return convert_source_text_to_markdown(
        source_type="tex",
        source_path=source_path,
        source_text=latex_text,
    )


def convert_pdf_file_to_markdown(file_path: str | Path) -> str:
    """Extract text from a PDF file, then convert it into canonical Markdown."""
    source_path = Path(file_path)
    extracted_text = extract_pdf_text(source_path)
    return convert_source_text_to_markdown(
        source_type="pdf",
        source_path=source_path,
        source_text=extracted_text,
    )


def convert_source_text_to_markdown(
    source_type: str,
    source_path: Path,
    source_text: str,
) -> str:
    """Convert extracted raw source text into reviewed Markdown."""
    conversion_model = CONVERSION_MODEL or CHAT_MODEL
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required for source conversion.")
    if not conversion_model:
        raise RuntimeError("Set CONVERSION_MODEL or CHAT_MODEL before running conversion.")
    if not source_text.strip():
        raise ValueError(f"No usable text found in source file: {source_path}")

    user_prompt = (
        f"Source type: {source_type}\n"
        f"Source path: {source_path}\n\n"
        "Convert the following study material into clean Markdown for retrieval.\n\n"
        f"{source_text}"
    )

    log.info("Converting %s with model %s", source_path, conversion_model)
    response = _get_client().chat.completions.create(
        model=conversion_model,
        messages=[
            {"role": "system", "content": CONVERSION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=int(CONVERSION_MAX_TOKENS),
    )
    content = response.choices[0].message.content
    if content is None or not content.strip():
        raise RuntimeError(f"Conversion model returned empty Markdown for {source_path}")
    return content.strip() + "\n"


def extract_pdf_text(file_path: str | Path) -> str:
    """Extract PDF text locally before LLM conversion."""
    from pypdf import PdfReader

    reader = PdfReader(str(file_path))
    page_text_blocks: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            page_text_blocks.append(page_text.strip())

    combined_text = "\n\n".join(page_text_blocks)
    if not combined_text.strip():
        raise ValueError(f"No text could be extracted from PDF: {file_path}")
    return combined_text

