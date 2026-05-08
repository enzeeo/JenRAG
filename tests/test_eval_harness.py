from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest
from unittest import mock

from src.eval import harness
from src.pipeline.retriever import ChunkHit, RelatedTopicHit, RetrievalResult, WikiPageHit


class EvalHarnessTests(unittest.TestCase):
    def test_load_test_set_falls_back_to_example_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            example_cases_path = Path(temporary_directory) / "eval_cases.example.json"
            example_cases = [
                {
                    "query": "Explain recurrence trees.",
                    "reference": "Ground answer in retrieved notes.",
                    "category": "grounded_explanation",
                }
            ]
            example_cases_path.write_text(
                json.dumps(example_cases),
                encoding="utf-8",
            )

            with mock.patch.object(
                harness,
                "EXAMPLE_EVALUATION_CASES_PATH",
                str(example_cases_path),
            ):
                loaded_cases = harness.load_test_set(
                    cases_path=str(Path(temporary_directory) / "missing.json")
                )

        self.assertEqual(loaded_cases, example_cases)

    def test_build_judge_context_includes_chunks_wiki_pages_and_related_topics(self) -> None:
        retrieval_result = RetrievalResult(
            chunk_hits=[
                ChunkHit(
                    text="Master theorem applies to balanced recurrence.",
                    title="CMSC 27100 Notes",
                    section="Merge Sort",
                    source_path="latex/cmsc_27100/notes.tex",
                    course_key="cmsc_27100",
                    score=0.2,
                )
            ],
            wiki_page_hits=[
                WikiPageHit(
                    slug="master-theorem",
                    title="Master Theorem",
                    page_type="concept",
                    summary="Solves common divide-and-conquer recurrences.",
                    body="Compare f(n) against n^{log_b a}.",
                    course_key="cmsc_27100",
                    source_path="latex/cmsc_27100/notes.tex",
                    source_title="CMSC 27100 Notes",
                    section="Merge Sort",
                    aliases=["recurrence analysis"],
                    score=12,
                )
            ],
            related_topics=[
                RelatedTopicHit(
                    slug="divide-and-conquer",
                    title="Divide and Conquer",
                    relation="related_topic",
                )
            ],
        )

        context = harness.build_judge_context(retrieval_result)

        self.assertIn("## Chunk Evidence", context)
        self.assertIn("Master theorem applies to balanced recurrence.", context)
        self.assertIn("## Wiki Page Matches", context)
        self.assertIn("Aliases: recurrence analysis", context)
        self.assertIn("## Related Topics", context)
        self.assertIn("Divide and Conquer (divide-and-conquer) [related_topic]", context)

    def test_run_eval_uses_structured_retrieval_counts_and_writes_output(self) -> None:
        retrieval_result = RetrievalResult(
            chunk_hits=[
                ChunkHit(
                    text="Proof uses induction on subproblem size.",
                    title="CMSC 27100 Notes",
                    section="Induction",
                    source_path="latex/cmsc_27100/notes.tex",
                    course_key="cmsc_27100",
                    score=0.1,
                )
            ],
            wiki_page_hits=[
                WikiPageHit(
                    slug="induction",
                    title="Induction",
                    page_type="concept",
                    summary="Prove base case, then inductive step.",
                    body="Assume smaller case and extend to larger case.",
                    course_key="cmsc_27100",
                    source_path="latex/cmsc_27100/notes.tex",
                    source_title="CMSC 27100 Notes",
                    section="Induction",
                    aliases=[],
                    score=9,
                )
            ],
            related_topics=[
                RelatedTopicHit(
                    slug="loop-invariant",
                    title="Loop Invariant",
                    relation="related_topic",
                )
            ],
        )
        test_set = [
            {
                "query": "Explain induction.",
                "reference": "Ground answer in notes.",
                "category": "grounded_explanation",
            }
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "eval_results.json"
            with (
                mock.patch("src.eval.harness.retrieve", return_value=retrieval_result),
                mock.patch("src.eval.harness.generate", return_value="Grounded answer"),
                mock.patch(
                    "src.eval.harness.judge",
                    return_value={
                        "context_relevance": 5,
                        "context_recall": 4,
                        "faithfulness": 5,
                        "answer_correctness": 4,
                        "notes": "Grounded in retrieved evidence.",
                    },
                ),
            ):
                results = harness.run_eval(
                    use_reranker=False,
                    test_set=test_set,
                    output_path=str(output_path),
                )

            written_results = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["num_chunks"], 1)
        self.assertEqual(results[0]["num_wiki_pages"], 1)
        self.assertEqual(results[0]["num_related_topics"], 1)
        self.assertEqual(written_results[0]["category"], "grounded_explanation")


if __name__ == "__main__":
    unittest.main()
