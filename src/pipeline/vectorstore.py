from __future__ import annotations

import hashlib
import logging

from .chunker import Chunk
from .config import CHROMA_DB_PATH, CHROMA_COLLECTION_NAME

CHROMA_BATCH_SIZE = 5000
log = logging.getLogger(__name__)


def init_collection(path: str, name: str):
    import chromadb

    client = chromadb.PersistentClient(path=path)
    return client.get_or_create_collection(name=name)


def chunk_id(chunk: Chunk) -> str:
    """Deterministic ID from chunk content so re-runs are idempotent."""
    title = chunk.metadata.get("title", "")
    section = chunk.metadata.get("section", "")
    key = f"{title}|{section}|{chunk.text}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def add_chunks(
    collection: chromadb.Collection,
    chunks: list[Chunk],
    embeddings: list[list[float]],
):
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings"
        )

    all_ids = [chunk_id(c) for c in chunks]
    all_texts = [c.text for c in chunks]
    all_metas = [c.metadata for c in chunks]

    seen: set[str] = set()
    ids, texts, metadatas, deduped_embeddings = [], [], [], []
    for cid, text, meta, emb in zip(all_ids, all_texts, all_metas, embeddings):
        if cid in seen:
            continue
        seen.add(cid)
        ids.append(cid)
        texts.append(text)
        metadatas.append(meta)
        deduped_embeddings.append(emb)
    embeddings = deduped_embeddings

    if len(ids) < len(chunks):
        log.info(f"Deduplicated {len(chunks) - len(ids)} duplicate chunks")

    for i in range(0, len(ids), CHROMA_BATCH_SIZE):
        end = min(i + CHROMA_BATCH_SIZE, len(ids))
        collection.upsert(
            ids=ids[i:end],
            documents=texts[i:end],
            metadatas=metadatas[i:end],
            embeddings=embeddings[i:end],
        )
        log.info(f"Upserted {end}/{len(ids)} chunks to ChromaDB")


def query(
    collection: chromadb.Collection,
    query_embedding: list[float],
    n_results: int,
    where_filter: dict | None = None,
):
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_filter,
    )


def get_all_documents(collection: chromadb.Collection) -> dict[str, list]:
    """Return all stored chunks with ids, documents, and metadata."""
    return collection.get(include=["documents", "metadatas"])
