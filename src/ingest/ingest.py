"""Full ingestion pipeline: corpus discovery → chunk → embed → store."""

import logging
import sys
import time
from src.pipeline.chunker import chunk_all_pages
from src.pipeline.corpus import load_corpus_documents
from src.pipeline.embedder import embed_chunks
from src.pipeline.vectorstore import init_collection, add_chunks
from src.pipeline.config import CHROMA_DB_PATH, CHROMA_COLLECTION_NAME, DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

def main():
    t0 = time.time()

    log.info(f"Loading study corpus from {DATA_DIR}...")
    documents, warnings = load_corpus_documents(DATA_DIR)
    for warning_message in warnings:
        log.warning(warning_message)

    if not documents:
        log.error(
            f"No supported study documents found in {DATA_DIR}. "
            "Add structured markdown files under data/md."
        )
        sys.exit(1)
    log.info(
        "Loaded %s documents: %s",
        len(documents),
        ", ".join(document.title for document in documents),
    )

    log.info("Chunking...")
    chunks = chunk_all_pages(
        [
            (document.title, document.text, document.metadata)
            for document in documents
        ]
    )
    log.info(f"Created {len(chunks)} chunks")

    log.info("Embedding (this may take a while)...")
    texts = [c.to_embed_text() for c in chunks]
    embeddings = embed_chunks(texts)
    log.info(f"Got {len(embeddings)} embeddings")

    log.info("Storing in ChromaDB...")
    collection = init_collection(CHROMA_DB_PATH, CHROMA_COLLECTION_NAME)
    add_chunks(collection, chunks, embeddings)
    log.info(f"Collection now has {collection.count()} documents")

    elapsed = time.time() - t0
    log.info(f"Ingestion complete in {elapsed/60:.1f} minutes")


if __name__ == "__main__":
    main()
