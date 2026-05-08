import logging

from .config import OPENAI_API_KEY, OPENAI_BASE_URL, CHAT_MODEL
from .retriever import RetrievalResult, retrieve

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

_client = None

PRACTICE_REQUEST_KEYWORDS = (
    "practice question",
    "practice questions",
    "practice problem",
    "practice problems",
    "similar question",
    "similar questions",
    "similar problem",
    "similar problems",
    "new question",
    "new questions",
    "new problem",
    "new problems",
    "homework problem",
    "homework problems",
    "generate a question",
    "generate questions",
    "generate a problem",
    "generate problems",
    "come up with",
)


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
- Format math with standard LaTeX delimiters only: use `$...$` for inline math and `$$...$$` for standalone display math.

--- RETRIEVED EVIDENCE ---

{context}

--- END EVIDENCE ---"""

PRACTICE_GENERATION_PROMPT_SUFFIX = """

Practice-generation rules:
- If the user asks for a homework problem, practice problem, or similar question, you may create a NEW question instead of copying a retrieved one.
- The new question must stay grounded in retrieved material: same course topics, same kind of reasoning, and comparable difficulty/style.
- The new question must be meaningfully different from retrieved questions. Change the surface form enough to create variation, not a near-duplicate.
- Before you present the question, solve it completely in private and verify that the final answer is correct and consistent with the retrieved evidence.
- If you cannot privately verify a correct solution from the retrieved evidence, do not invent a question. Say the evidence is not strong enough to safely generate a verified problem.
- Do not reveal your private verification process or chain-of-thought.
- In the final answer, provide:
  1. a clearly labeled new practice question,
  2. a concise final answer or solution check,
  3. a short note explaining which retrieved material inspired it.
"""


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


def is_practice_generation_request(query: str) -> bool:
    """Return whether the user is asking for a new grounded practice-style problem."""
    normalized_query = query.casefold()
    return any(keyword in normalized_query for keyword in PRACTICE_REQUEST_KEYWORDS)


def build_system_prompt(query: str, retrieval_result: RetrievalResult) -> str:
    """Build the system prompt, adding stricter practice-generation rules when needed."""
    context = build_context(retrieval_result)
    system_prompt = SYSTEM_PROMPT.format(context=context)
    if is_practice_generation_request(query):
        system_prompt += PRACTICE_GENERATION_PROMPT_SUFFIX
    return system_prompt


def generate(
    query: str,
    retrieval_result: RetrievalResult,
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> str:
    """Generate an answer from retrieved chunks."""
    system = build_system_prompt(query, retrieval_result)

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
