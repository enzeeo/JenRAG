import time
import logging

from .config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_DOC_PREFIX,
    EMBEDDING_QUERY_PREFIX,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        kwargs: dict = {"api_key": OPENAI_API_KEY}
        if OPENAI_BASE_URL:
            kwargs["base_url"] = OPENAI_BASE_URL
        _client = OpenAI(**kwargs)
    return _client

MAX_RETRIES = 3
RETRY_DELAY = 5


def embed_chunks(chunk_texts: list[str]) -> list[list[float]]:
    all_embeddings = []
    total = len(chunk_texts)
    num_batches = (total + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
    start_time = time.time()

    for batch_idx, i in enumerate(range(0, total, EMBEDDING_BATCH_SIZE)):
        batch = [
            EMBEDDING_DOC_PREFIX + t for t in chunk_texts[i : i + EMBEDDING_BATCH_SIZE]
        ]

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = _get_client().embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=batch,
                )
                all_embeddings.extend(item.embedding for item in response.data)
                break
            except Exception as e:
                log.warning(
                    f"Batch {batch_idx+1}/{num_batches} attempt {attempt} failed: {e}"
                )
                if attempt == MAX_RETRIES:
                    raise RuntimeError(
                        f"Failed after {MAX_RETRIES} retries on batch {batch_idx+1}. "
                        f"Embedded {len(all_embeddings)}/{total} chunks before failure."
                    )
                time.sleep(RETRY_DELAY * attempt)

        elapsed = time.time() - start_time
        done = len(all_embeddings)
        rate = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / rate if rate > 0 else 0
        log.info(
            f"Batch {batch_idx+1}/{num_batches} done — "
            f"{done}/{total} chunks ({done*100/total:.1f}%) — "
            f"ETA {eta/60:.1f}min"
        )

    log.info(
        f"Embedding complete: {len(all_embeddings)} vectors in {(time.time()-start_time)/60:.1f}min"
    )
    return all_embeddings


def embed_query(query_text: str) -> list[float]:
    response = _get_client().embeddings.create(
        model=EMBEDDING_MODEL,
        input=EMBEDDING_QUERY_PREFIX + query_text,
    )
    return response.data[0].embedding


def embed_queries(query_texts: list[str]) -> list[list[float]]:
    """Batch-embed multiple queries at once, reusing the same batching logic as embed_chunks."""
    all_embeddings: list[list[float]] = []
    total = len(query_texts)
    num_batches = (total + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
    start_time = time.time()

    for batch_idx, i in enumerate(range(0, total, EMBEDDING_BATCH_SIZE)):
        batch = [
            EMBEDDING_QUERY_PREFIX + t for t in query_texts[i : i + EMBEDDING_BATCH_SIZE]
        ]

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = _get_client().embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=batch,
                )
                all_embeddings.extend(item.embedding for item in response.data)
                break
            except Exception as e:
                log.warning(
                    f"Query batch {batch_idx+1}/{num_batches} attempt {attempt} failed: {e}"
                )
                if attempt == MAX_RETRIES:
                    raise RuntimeError(
                        f"Failed after {MAX_RETRIES} retries on query batch {batch_idx+1}."
                    )
                time.sleep(RETRY_DELAY * attempt)

    log.info(
        f"Embedded {total} queries in {time.time()-start_time:.1f}s "
        f"({num_batches} batches)"
    )
    return all_embeddings


if __name__ == "__main__":
    import os
    from src.pipeline.chunker import chunk_all_pages

    test_file = os.path.join(os.path.dirname(__file__), "../../data/cs_algos_2023_272_4")
    title = os.path.splitext(os.path.basename(test_file))[0]
    with open(test_file) as f:
        pages = {title: f.read()}

    chunks = chunk_all_pages(pages)
    print(f"Chunked into {len(chunks)} chunks:")
    for i, c in enumerate(chunks):
        tok = len(c.text) // 4
        sec = c.metadata["section"] or "(preamble)"
        print(f"  [{i}] {sec:30s} ({tok} tok)")

    texts = [c.to_embed_text() for c in chunks]
    embeddings = embed_chunks(texts)

    print(f"\nEmbedded {len(embeddings)} chunks, dim={len(embeddings[0])}")
    for i, (c, emb) in enumerate(zip(chunks, embeddings)):
        sec = c.metadata["section"] or "(preamble)"
        preview = str(emb[:5])
        print(f"  [{i}] {sec:30s} -> {preview}...")
