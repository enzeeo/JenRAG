from dataclasses import dataclass
import logging
import time

from .embedder import embed_query
from .vectorstore import init_collection, query
from .config import (
    CHROMA_DB_PATH,
    CHROMA_COLLECTION_NAME,
    RETRIEVAL_TOP_K,
    RERANK_TOP_K,
    RERANK_MODEL,
    WIKI_DB_PATH,
    WIKI_TOP_K,
)
from src.wiki.query import (
    find_related_topics,
    find_wiki_matches,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

_reranker_tokenizer = None
_reranker_model = None
_reranker_device = None


@dataclass(frozen=True)
class ChunkHit:
    text: str
    title: str
    section: str
    source_path: str
    course_key: str
    score: float | None = None

    def format_for_prompt(self) -> str:
        header = self.title
        if self.section:
            header = f"{header} — {self.section}"
        if self.source_path:
            header = f"{header} (source: {self.source_path})"
        return f"{header}\n{self.text}"


@dataclass(frozen=True)
class RelatedTopicHit:
    slug: str
    title: str
    relation: str

    def format_for_prompt(self) -> str:
        return f"{self.title} ({self.slug}) [{self.relation}]"


@dataclass(frozen=True)
class WikiPageHit:
    slug: str
    title: str
    page_type: str
    summary: str
    body: str
    course_key: str
    source_path: str
    source_title: str
    section: str
    aliases: list[str]
    score: int

    def format_for_prompt(self) -> str:
        lines = [
            f"{self.title} [{self.page_type}] (source: {self.source_path})",
            f"Summary: {self.summary}",
        ]
        if self.section:
            lines.append(f"Section: {self.section}")
        if self.aliases:
            lines.append("Aliases: " + ", ".join(self.aliases))
        if self.body and self.body != self.summary:
            lines.append(f"Details: {self.body}")
        return "\n".join(lines)


@dataclass(frozen=True)
class RetrievalResult:
    chunk_hits: list[ChunkHit]
    wiki_page_hits: list[WikiPageHit]
    related_topics: list[RelatedTopicHit]

    def formatted_chunks(self) -> list[str]:
        return [chunk_hit.format_for_prompt() for chunk_hit in self.chunk_hits]


def _get_reranker():
    """Lazy-load the reranker model on first use."""
    global _reranker_tokenizer, _reranker_model, _reranker_device

    if _reranker_model is not None:
        return _reranker_tokenizer, _reranker_model, _reranker_device

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    log.info(f"Loading reranker model: {RERANK_MODEL}")
    start = time.time()

    _reranker_tokenizer = AutoTokenizer.from_pretrained(RERANK_MODEL)
    _reranker_model = AutoModelForSequenceClassification.from_pretrained(RERANK_MODEL)
    _reranker_model.eval()

    if torch.backends.mps.is_available():
        _reranker_device = "mps"
    elif torch.cuda.is_available():
        _reranker_device = "cuda"
    else:
        _reranker_device = "cpu"

    if _reranker_device in ("cuda", "mps"):
        _reranker_model = _reranker_model.half()
    _reranker_model = _reranker_model.to(_reranker_device)

    log.info(f"Reranker loaded on {_reranker_device} in {time.time() - start:.1f}s")
    return _reranker_tokenizer, _reranker_model, _reranker_device

RERANK_BATCH_SIZE = 16


def rerank(
    query_text: str,
    docs: list[str],
    metadatas: list[dict],
    top_k: int,
) -> tuple[list[str], list[dict]]:
    """Rerank candidates using BGE cross-encoder and return the top_k."""
    import torch

    tokenizer, model, device = _get_reranker()

    pairs = [[query_text, doc] for doc in docs]
    scores: list[float] = []

    with torch.no_grad():
        for i in range(0, len(pairs), RERANK_BATCH_SIZE):
            batch = pairs[i : i + RERANK_BATCH_SIZE]
            inputs = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}
            batch_scores = model(**inputs).logits.view(-1).float().cpu().tolist()
            scores.extend(batch_scores)
            del inputs
        if device == "mps":
            torch.mps.empty_cache()

    ranked = sorted(
        zip(scores, docs, metadatas),
        key=lambda x: x[0],
        reverse=True,
    )

    top = ranked[:top_k]
    log.info(
        f"Rerank scores: best={top[0][0]:.4f}, worst={top[-1][0]:.4f}, "
        f"cutoff={ranked[top_k][0]:.4f}"
        if len(ranked) > top_k
        else f"Rerank scores: best={top[0][0]:.4f}, worst={top[-1][0]:.4f}"
    )

    return [doc for _, doc, _ in top], [meta for _, _, meta in top]


def retrieve(
    query_text: str,
    top_k: int = RETRIEVAL_TOP_K,
    rerank_top_k: int = RERANK_TOP_K,
    use_reranker: bool = False,
    wiki_db_path: str = WIKI_DB_PATH,
    wiki_top_k: int = WIKI_TOP_K,
) -> RetrievalResult:
    """Return chunk hits plus wiki sidecar matches for the query."""
    collection = init_collection(CHROMA_DB_PATH, CHROMA_COLLECTION_NAME)
    log.info(f"Collection has {collection.count()} chunks")

    query_embedding = embed_query(query_text)
    results = query(collection, query_embedding, n_results=top_k)

    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    if not docs:
        log.info("Retrieved 0 chunk candidates")
        return RetrievalResult(chunk_hits=[], wiki_page_hits=[], related_topics=[])

    best_distance = distances[0] if distances and distances[0] is not None else None
    if best_distance is None:
        log.info(f"Retrieved {len(docs)} candidates")
    else:
        log.info(f"Retrieved {len(docs)} candidates (closest distance: {best_distance:.4f})")

    if use_reranker:
        docs, metadatas = rerank(query_text, docs, metadatas, rerank_top_k)
        distances = [None] * len(docs)
        log.info(f"Reranked to top {len(docs)} chunks")

    chunk_hits = [
        ChunkHit(
            text=doc,
            title=meta.get("title", "?"),
            section=meta.get("section", ""),
            source_path=meta.get("source_path", ""),
            course_key=meta.get("course_key", ""),
            score=distance,
        )
        for doc, meta, distance in zip(docs, metadatas, distances)
    ]

    wiki_matches = find_wiki_matches(
        query_text=query_text,
        chunk_source_paths=[chunk_hit.source_path for chunk_hit in chunk_hits],
        course_keys=[chunk_hit.course_key for chunk_hit in chunk_hits],
        database_path=wiki_db_path,
        top_k=wiki_top_k,
    )
    related_topics = find_related_topics(
        [wiki_match.slug for wiki_match in wiki_matches],
        database_path=wiki_db_path,
        top_k=wiki_top_k,
    )

    wiki_page_hits = [
        WikiPageHit(
            slug=wiki_match.slug,
            title=wiki_match.title,
            page_type=wiki_match.page_type,
            summary=wiki_match.summary,
            body=wiki_match.body,
            course_key=wiki_match.course_key,
            source_path=wiki_match.source_path,
            source_title=wiki_match.source_title,
            section=wiki_match.section,
            aliases=wiki_match.aliases,
            score=wiki_match.score,
        )
        for wiki_match in wiki_matches
    ]

    return RetrievalResult(
        chunk_hits=chunk_hits,
        wiki_page_hits=wiki_page_hits,
        related_topics=[
            RelatedTopicHit(
                slug=related_topic.slug,
                title=related_topic.title,
                relation=related_topic.relation,
            )
            for related_topic in related_topics
        ],
    )


if __name__ == "__main__":
    TEST_QUERIES = [
        "What is the divide and conquer approach for the card problem?",
        "How do you find a lucky entry in a sorted array?",
        "What is the time complexity of the Billy search algorithm?",
    ]

    for q in TEST_QUERIES:
        print(f"\n{'='*80}")
        print(f"QUERY: {q}")
        print(f"{'='*80}")
        formatted_chunks = retrieve(q, use_reranker=True).formatted_chunks()
        for i, chunk in enumerate(formatted_chunks, 1):
            print(f"\n--- Result {i}/{len(formatted_chunks)} ---")
            print(chunk[:300])
            if len(chunk) > 300:
                print(f"  ... ({len(chunk)} chars total)")
