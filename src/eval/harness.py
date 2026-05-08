"""StudyGraph evaluation harness.

Runs operator-facing smoke evaluations over the current study corpus and uses
an external judge to score whether answers stay grounded in retrieved chunk and
wiki evidence. The default cases focus on the main hosted workflows: grounded
explanations, practice-question generation, and cross-document synthesis.
"""

import json
import time
import logging
import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in minimal test environments
    def load_dotenv() -> bool:
        return False

from src.pipeline.retriever import retrieve
from src.pipeline.generator import generate
from src.pipeline.config import DATA_DIR

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

EVAL_MODEL = "claude-sonnet-4-20250514"
EVALUATION_CASES_PATH = os.path.join(DATA_DIR, "eval_cases.json")
EXAMPLE_EVALUATION_CASES_PATH = os.path.join(DATA_DIR, "eval_cases.example.json")
EVALUATION_RESULTS_PATH = os.path.join(DATA_DIR, "eval_results.json")

DEFAULT_TEST_SET = [
    {
        "query": "Explain the proof strategy used in the retrieved course materials.",
        "reference": (
            "The answer should give a plain-language explanation grounded in the "
            "retrieved course materials, identify the specific source-backed "
            "strategy or technique, and state clearly when the current corpus "
            "does not provide enough evidence."
        ),
        "category": "grounded_explanation",
    },
    {
        "query": "Generate one new practice question that is similar in style to the retrieved assignment material.",
        "reference": (
            "The answer should produce a new practice question inspired by the "
            "retrieved assignments or notes, keep the difficulty and topic close "
            "to the evidence, and avoid claiming it is copied directly from the "
            "source material."
        ),
        "category": "practice_generation",
    },
    {
        "query": "Compare how the retrieved materials present the same concept across multiple documents.",
        "reference": (
            "The answer should synthesize patterns across multiple retrieved "
            "documents or wiki pages, point out similarities or differences, and "
            "stay anchored to the available evidence instead of generic textbook "
            "knowledge."
        ),
        "category": "cross_document_synthesis",
    },
    {
        "query": "What should a student do if the retrieved course materials do not fully answer the question?",
        "reference": (
            "The answer should say that missing evidence must be acknowledged, "
            "summarize whatever support is present in the retrieved context, and "
            "avoid inventing unsupported course-specific details."
        ),
        "category": "grounding_gap_handling",
    },
]

_judge_client = None


def load_test_set(cases_path: str = EVALUATION_CASES_PATH) -> list[dict]:
    """Load evaluation cases from disk, falling back to bundled smoke cases."""
    if os.path.exists(cases_path):
        with open(cases_path, encoding="utf-8") as file_handle:
            loaded_cases = json.load(file_handle)
        return validate_test_set(loaded_cases)

    if os.path.exists(EXAMPLE_EVALUATION_CASES_PATH):
        with open(EXAMPLE_EVALUATION_CASES_PATH, encoding="utf-8") as file_handle:
            loaded_cases = json.load(file_handle)
        return validate_test_set(loaded_cases)

    return validate_test_set(DEFAULT_TEST_SET)


def validate_test_set(test_set: list[dict]) -> list[dict]:
    """Validate the minimal structure required for smoke evaluation cases."""
    validated_cases: list[dict] = []
    for index, case in enumerate(test_set, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"Evaluation case #{index} must be a JSON object.")
        for field_name in ("query", "reference", "category"):
            if not case.get(field_name):
                raise ValueError(
                    f"Evaluation case #{index} is missing required field "
                    f"`{field_name}`."
                )
        validated_cases.append(
            {
                "query": str(case["query"]),
                "reference": str(case["reference"]),
                "category": str(case["category"]),
            }
        )
    return validated_cases


def get_judge_client():
    """Create the Anthropic judge client lazily for CLI use."""
    global _judge_client
    if _judge_client is None:
        import anthropic

        evaluation_api_key = os.getenv("EVAL_API_KEY")
        if not evaluation_api_key:
            raise RuntimeError(
                "EVAL_API_KEY is required to run `uv run evaluate`."
            )
        _judge_client = anthropic.Anthropic(api_key=evaluation_api_key)
    return _judge_client


JUDGE_PROMPT = """\
You are evaluating a study-material RAG system. Score the output on four \
metrics, each 1-5.

## Input

**User query:** {query}

**Reference answer (ground truth):**
{reference}

**Retrieved evidence:**
{context}

**RAG system's answer:**
{answer}

## Scoring rubric

1. **context_relevance** (1-5): Does the retrieved evidence contain the \
information needed to answer the query? 5 = all necessary support present, \
1 = completely irrelevant evidence.

2. **context_recall** (1-5): Does the retrieved evidence cover ALL the key \
facts from the reference answer? 5 = every key point from the reference is \
represented in the context. 1 = almost none of the reference facts appear.

3. **faithfulness** (1-5): Is every claim in the RAG answer supported by \
the retrieved evidence? 5 = fully grounded, zero hallucination. 1 = mostly \
fabricated claims not in context.

4. **answer_correctness** (1-5): Compared to the reference answer, how \
complete and accurate is the RAG answer? 5 = covers all key points correctly. \
1 = wrong or missing most key information.

## Output format

Respond with ONLY a JSON object, no other text:
{{"context_relevance": <int>, "context_recall": <int>, "faithfulness": <int>, "answer_correctness": <int>, "notes": "<brief explanation of scores>"}}"""

METRICS = ["context_relevance", "context_recall", "faithfulness", "answer_correctness"]


def build_judge_context(retrieval_result) -> str:
    """Format retrieved chunks, wiki pages, and related topics for the judge."""
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


def judge(query: str, context: str, answer: str, reference: str) -> dict:
    """Use Claude to score a single RAG result."""
    prompt = JUDGE_PROMPT.format(
        query=query,
        reference=reference,
        context=context[:8000],
        answer=answer,
    )

    response = get_judge_client().messages.create(
        model=EVAL_MODEL,
        max_tokens=300,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        log.warning(f"Failed to parse judge response: {raw}")
        return {m: 0 for m in METRICS} | {"notes": f"PARSE_ERROR: {raw}"}


def run_eval(
    use_reranker: bool = True,
    test_set: list[dict] | None = None,
    output_path: str = EVALUATION_RESULTS_PATH,
):
    """Run the full evaluation suite."""
    evaluation_cases = test_set if test_set is not None else load_test_set()
    results = []
    categories = {case["category"] for case in evaluation_cases}

    print(
        f"\nRAG Evaluation — {len(evaluation_cases)} questions "
        f"(reranker={'ON' if use_reranker else 'OFF'}, judge={EVAL_MODEL})"
    )
    print(
        "Distribution: "
        + ", ".join(
            f"{category}="
            f"{sum(1 for case in evaluation_cases if case['category'] == category)}"
            for category in sorted(categories)
        )
        + "\n"
    )

    for index, test in enumerate(evaluation_cases, start=1):
        query = test["query"]
        category = test["category"]
        print(f"[{index}/{len(evaluation_cases)}] [{category.upper()}] {query}")

        t0 = time.time()
        retrieval_result = retrieve(query, use_reranker=use_reranker)
        retrieval_time = time.time() - t0

        t0 = time.time()
        answer = generate(query, retrieval_result)
        generation_time = time.time() - t0

        context = build_judge_context(retrieval_result)

        t0 = time.time()
        scores = judge(query, context, answer, test["reference"])
        judge_time = time.time() - t0

        result = {
            "query": query,
            "category": category,
            "answer": answer,
            "reference": test["reference"],
            "num_chunks": len(retrieval_result.chunk_hits),
            "num_wiki_pages": len(retrieval_result.wiki_page_hits),
            "num_related_topics": len(retrieval_result.related_topics),
            "retrieval_time": retrieval_time,
            "generation_time": generation_time,
            "judge_time": judge_time,
            **scores,
        }
        results.append(result)

        scores_str = "  ".join(f"{m[:7]}={scores.get(m, '?')}/5" for m in METRICS)
        print(f"  {scores_str}  ({retrieval_time:.1f}s + {generation_time:.1f}s)")
        if scores.get("notes"):
            print(f"  Notes: {scores['notes']}")
        print()

    print_summary(results)

    with open(output_path, "w", encoding="utf-8") as file_handle:
        json.dump(results, file_handle, indent=2)
    print(f"\nFull results saved to {output_path}")

    return results


def print_summary(results: list[dict]):
    """Print aggregate metrics, broken down by RAGAS category."""
    valid = [r for r in results if r.get("context_relevance", 0) > 0]
    n = len(valid)
    if n == 0:
        print("No valid results to summarize.")
        return

    categories = sorted({r["category"] for r in valid})

    def avg(items, key):
        vals = [r[key] for r in items if r.get(key, 0) > 0]
        return sum(vals) / len(vals) if vals else 0

    print("\n" + "=" * 78)
    print("EVALUATION SUMMARY")
    print("=" * 78)
    print(f"  Questions evaluated:  {n}")
    print(f"  Judge model:          {EVAL_MODEL}")
    print()

    header = f"  {'Metric':<22} {'All':>5}"
    for c in categories:
        header += f" {c:>13}"
    print(header)
    print(f"  {'-'*22} {'-'*5}" + "".join(f" {'-'*13}" for _ in categories))

    for metric in METRICS:
        label = metric.replace("_", " ").title()
        row = f"  {label:<22} {avg(valid, metric):>5.2f}"
        for c in categories:
            subset = [r for r in valid if r["category"] == c]
            row += f" {avg(subset, metric):>12.2f}"
        print(row)

    print()
    print(f"  {'Avg Retrieval Time':<22} {avg(valid, 'retrieval_time'):>5.1f}s")
    print(f"  {'Avg Generation Time':<22} {avg(valid, 'generation_time'):>5.1f}s")
    print(f"  {'Avg Judge Time':<22} {avg(valid, 'judge_time'):>5.1f}s")
    print("=" * 78)

    low = [r for r in valid if any(r.get(m, 5) <= 2 for m in METRICS)]
    if low:
        print(
            f"\n  Weak spots ({len(low)} questions scored <=2 on at least one metric):"
        )
        for r in low:
            weak_metrics = [m for m in METRICS if r.get(m, 5) <= 2]
            print(f"    - [{r['category']}] {r['query']}")
            print(f"      Low: {', '.join(f'{m}={r[m]}' for m in weak_metrics)}")
            if r.get("notes"):
                print(f"      {r['notes']}")


def main():
    run_eval(use_reranker=True)


if __name__ == "__main__":
    main()
