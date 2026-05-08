import logging

from .config import OPENAI_API_KEY, OPENAI_BASE_URL, CHAT_MODEL
from .retriever import RetrievalResult, retrieve

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

SYSTEM_PROMPT = """\
You are a study assistant for course materials. Answer user question using ONLY \
retrieved corpus evidence below.

Rules:
- Treat chunk evidence as highest-trust source because it comes directly from uploaded corpus files.
- Use generated wiki pages only as grounded summaries of those source files, never as license to invent missing facts.
- If chunk evidence and wiki summary disagree, trust chunk evidence and mention discrepancy.
- If evidence is insufficient, say so clearly.
- Do not use unsupported outside knowledge.
- Cite source titles, section names, or source paths when useful.
- When asked for practice questions, derive them from retrieved material instead of introducing unrelated topics.

--- RETRIEVED EVIDENCE ---

{context}

--- END EVIDENCE ---"""


def build_context(retrieval_result: RetrievalResult) -> str:
    """Format chunk hits, wiki hits, and related topics for the system prompt."""
    lines: list[str] = []

    lines.append("## Chunk Evidence")
    if retrieval_result.chunk_hits:
        for chunk_index, chunk_hit in enumerate(retrieval_result.chunk_hits, start=1):
            lines.append(f"[Chunk {chunk_index}] {chunk_hit.format_for_prompt()}")
    else:
        lines.append("No direct chunk evidence retrieved.")

    lines.append("")
    lines.append("## Wiki Page Matches")
    if retrieval_result.wiki_page_hits:
        for page_index, wiki_page_hit in enumerate(retrieval_result.wiki_page_hits, start=1):
            lines.append(f"[Wiki {page_index}] {wiki_page_hit.format_for_prompt()}")
    else:
        lines.append("No wiki page matches retrieved.")

    lines.append("")
    lines.append("## Related Topics")
    if retrieval_result.related_topics:
        for related_topic in retrieval_result.related_topics:
            lines.append(f"- {related_topic.format_for_prompt()}")
    else:
        lines.append("- None")

    return "\n".join(lines)


def generate(
    query: str,
    retrieval_result: RetrievalResult,
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> str:
    """Generate an answer from retrieved chunks."""
    context = build_context(retrieval_result)
    system = SYSTEM_PROMPT.format(context=context)

    log.info(
        "Generating with %s chunks, %s wiki pages, %s related topics, ~%s prompt tokens",
        len(retrieval_result.chunk_hits),
        len(retrieval_result.wiki_page_hits),
        len(retrieval_result.related_topics),
        len(system) // 4,
    )

    response = _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": query},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content


def ask(query: str, use_reranker: bool = True) -> str:
    """Full pipeline: query -> retrieve -> (rerank) -> generate."""
    retrieval_result = retrieve(query, use_reranker=use_reranker)
    return generate(query, retrieval_result)


if __name__ == "__main__":
    TEST_QUERIES = [
        "What is the running time of the card equivalence algorithm in Problem 1?",
        "How does the lucky entry search work?",
        "What is the correctness argument for Problem 3?",
    ]

    for q in TEST_QUERIES:
        print(f"\n{'='*80}")
        print(f"Q: {q}")
        print(f"{'='*80}")
        answer = ask(q)
        print(f"\n{answer}")
