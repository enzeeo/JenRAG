"""Embedding commands for full rebuilds, missing-only updates, and targeted refreshes."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from src.pipeline.chunker import chunk_all_pages
from src.pipeline.config import CHROMA_COLLECTION_NAME, CHROMA_DB_PATH, DATA_DIR
from src.pipeline.corpus import CorpusDocument, load_corpus_documents
from src.pipeline.embedder import embed_chunks
from src.pipeline.vectorstore import (
    add_chunks,
    delete_chunks_by_source_path,
    get_embedded_source_paths,
    init_collection,
    reset_collection,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main_embed_all() -> None:
    """Rebuild the entire Chroma collection from all Markdown files."""
    start_time = time.time()
    documents = load_documents_or_exit()
    collection = reset_collection(CHROMA_DB_PATH, CHROMA_COLLECTION_NAME)
    embed_documents_into_collection(documents, collection)
    log.info("embed-all complete in %.1f minutes", (time.time() - start_time) / 60)


def main_embed_missing() -> None:
    """Embed only Markdown files missing from collection metadata."""
    start_time = time.time()
    documents = load_documents_or_exit()
    collection = init_collection(CHROMA_DB_PATH, CHROMA_COLLECTION_NAME)
    embedded_source_paths = get_embedded_source_paths(collection)
    documents_to_embed = [
        document
        for document in documents
        if document.metadata.get("source_path", "") not in embedded_source_paths
    ]

    if not documents_to_embed:
        log.info("embed-missing skipped. No new Markdown files found.")
        return

    log.info(
        "embed-missing found %s new Markdown files out of %s total.",
        len(documents_to_embed),
        len(documents),
    )
    embed_documents_into_collection(documents_to_embed, collection)
    log.info("embed-missing complete in %.1f minutes", (time.time() - start_time) / 60)


def main_embed_files() -> None:
    """Re-embed only requested Markdown files."""
    parser = argparse.ArgumentParser(description="Embed specific Markdown files.")
    parser.add_argument(
        "--path",
        dest="paths",
        action="append",
        required=True,
        help="Markdown file path under data/md. May be repeated.",
    )
    args = parser.parse_args()

    start_time = time.time()
    documents = load_documents_or_exit(args.paths)
    collection = init_collection(CHROMA_DB_PATH, CHROMA_COLLECTION_NAME)
    for document in documents:
        source_path = str(document.metadata.get("source_path", ""))
        if source_path:
            delete_chunks_by_source_path(collection, source_path)
    embed_documents_into_collection(documents, collection)
    log.info("embed-files complete in %.1f minutes", (time.time() - start_time) / 60)


def load_documents_or_exit(
    requested_paths: list[str] | None = None,
) -> list[CorpusDocument]:
    """Load Markdown documents or exit with a clear operator-facing error."""
    try:
        documents, warnings = load_corpus_documents(DATA_DIR, requested_paths=requested_paths)
    except ValueError as error:
        log.error(str(error))
        sys.exit(1)

    for warning_message in warnings:
        log.warning(warning_message)

    if not documents:
        requested_path_text = ""
        if requested_paths:
            requested_path_text = f" for requested paths: {', '.join(requested_paths)}"
        log.error(
            "No supported study documents found in %s%s. Add structured markdown files under data/md.",
            DATA_DIR,
            requested_path_text,
        )
        sys.exit(1)

    log.info(
        "Loaded %s Markdown documents: %s",
        len(documents),
        ", ".join(document.title for document in documents),
    )
    return documents


def embed_documents_into_collection(documents: list[CorpusDocument], collection) -> None:
    """Chunk, embed, and store one batch of Markdown documents."""
    chunks = chunk_all_pages(
        [
            (document.title, document.text, document.metadata)
            for document in documents
        ]
    )
    log.info("Created %s chunks", len(chunks))

    texts = [chunk.to_embed_text() for chunk in chunks]
    embeddings = embed_chunks(texts)
    log.info("Got %s embeddings", len(embeddings))

    add_chunks(collection, chunks, embeddings)
    log.info("Collection now has %s documents", collection.count())

