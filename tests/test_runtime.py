from __future__ import annotations

import importlib
import os
import sys
import types
import unittest
from unittest import mock

from src.pipeline.generator import build_context
from src.pipeline.retriever import (
    ChunkHit,
    RelatedTopicHit,
    RetrievalResult,
    WikiPageHit,
    retrieve,
)
from src.wiki.query import RelatedTopicMatch, WikiPageMatch


class RetrievalRuntimeTests(unittest.TestCase):
    def test_retrieve_returns_chunk_wiki_and_related_topic_hits(self) -> None:
        fake_results = {
            "documents": [["Chunk body text"]],
            "metadatas": [[
                {
                    "title": "CMSC 27100 Pset 1",
                    "section": "Problem 1",
                    "source_path": "latex/cmsc_27100/cmsc_27100_fall_2025_pset1_ng.tex",
                    "course_key": "cmsc_27100",
                }
            ]],
            "distances": [[0.25]],
        }
        fake_wiki_matches = [
            WikiPageMatch(
                slug="divide-and-conquer",
                title="Divide and Conquer",
                page_type="concept",
                summary="Break problem into subproblems.",
                body="Combine solved subproblems into final answer.",
                course_key="cmsc_27100",
                source_path="latex/cmsc_27100/cmsc_27100_fall_2025_pset1_ng.tex",
                source_title="CMSC 27100 Pset 1",
                section="Problem 1",
                aliases=["recurrence"],
                score=12,
            )
        ]
        fake_related_topics = [
            RelatedTopicMatch(
                slug="master-theorem",
                title="Master Theorem",
                relation="related_topic",
            )
        ]
        fake_collection = mock.Mock()
        fake_collection.count.return_value = 1

        with (
            mock.patch("src.pipeline.retriever.init_collection", return_value=fake_collection),
            mock.patch("src.pipeline.retriever.embed_query", return_value=[0.1, 0.2]),
            mock.patch("src.pipeline.retriever.query", return_value=fake_results),
            mock.patch("src.pipeline.retriever.find_wiki_matches", return_value=fake_wiki_matches) as find_wiki_matches_mock,
            mock.patch("src.pipeline.retriever.find_related_topics", return_value=fake_related_topics) as find_related_topics_mock,
        ):
            retrieval_result = retrieve(
                "How does divide and conquer work?",
                use_reranker=False,
                wiki_db_path="/tmp/wiki.sqlite3",
                wiki_top_k=3,
            )

        self.assertEqual(len(retrieval_result.chunk_hits), 1)
        self.assertEqual(retrieval_result.chunk_hits[0].source_path, fake_wiki_matches[0].source_path)
        self.assertEqual(len(retrieval_result.wiki_page_hits), 1)
        self.assertEqual(retrieval_result.wiki_page_hits[0].slug, "divide-and-conquer")
        self.assertEqual(len(retrieval_result.related_topics), 1)
        self.assertEqual(retrieval_result.related_topics[0].slug, "master-theorem")

        find_wiki_matches_mock.assert_called_once_with(
            query_text="How does divide and conquer work?",
            chunk_source_paths=["latex/cmsc_27100/cmsc_27100_fall_2025_pset1_ng.tex"],
            course_keys=["cmsc_27100"],
            database_path="/tmp/wiki.sqlite3",
            top_k=3,
        )
        find_related_topics_mock.assert_called_once_with(
            ["divide-and-conquer"],
            database_path="/tmp/wiki.sqlite3",
            top_k=3,
        )

    def test_build_context_prefers_grounded_chunk_and_wiki_sections(self) -> None:
        retrieval_result = RetrievalResult(
            chunk_hits=[
                ChunkHit(
                    text="Runtime follows recurrence T(n) = 2T(n/2) + n.",
                    title="CMSC 27100 Notes",
                    section="Merge Sort",
                    source_path="latex/cmsc_27100/notes.tex",
                    course_key="cmsc_27100",
                    score=0.1,
                )
            ],
            wiki_page_hits=[
                WikiPageHit(
                    slug="merge-sort",
                    title="Merge Sort",
                    page_type="concept",
                    summary="Sort recursively, then merge.",
                    body="Each level costs linear work.",
                    course_key="cmsc_27100",
                    source_path="latex/cmsc_27100/notes.tex",
                    source_title="CMSC 27100 Notes",
                    section="Merge Sort",
                    aliases=["divide and conquer sorting"],
                    score=10,
                )
            ],
            related_topics=[
                RelatedTopicHit(
                    slug="master-theorem",
                    title="Master Theorem",
                    relation="related_topic",
                )
            ],
        )

        context = build_context(retrieval_result)

        self.assertIn("## Chunk Evidence", context)
        self.assertIn("Runtime follows recurrence", context)
        self.assertIn("## Wiki Page Matches", context)
        self.assertIn("Aliases: divide and conquer sorting", context)
        self.assertIn("Details: Each level costs linear work.", context)
        self.assertIn("## Related Topics", context)
        self.assertIn("Master Theorem (master-theorem) [related_topic]", context)


class StreamlitDebugRenderingTests(unittest.TestCase):
    def test_render_retrieval_debug_renders_chunks_wiki_pages_and_related_topics(self) -> None:
        os.environ["JENRAG_SKIP_STREAMLIT_BOOTSTRAP"] = "1"
        try:
            sys.modules.pop("src.app.main", None)
            streamlit_stub = types.ModuleType("streamlit")
            streamlit_stub.secrets = {}
            with mock.patch.dict(sys.modules, {"streamlit": streamlit_stub}):
                main_module = importlib.import_module("src.app.main")
        finally:
            os.environ.pop("JENRAG_SKIP_STREAMLIT_BOOTSTRAP", None)

        fake_streamlit = FakeStreamlit()
        main_module.st = fake_streamlit

        retrieval_result = RetrievalResult(
            chunk_hits=[
                ChunkHit(
                    text="Graph cut proof text",
                    title="CMSC 27100 Notes",
                    section="Minimum Cut",
                    source_path="latex/cmsc_27100/notes.tex",
                    course_key="cmsc_27100",
                    score=0.2,
                )
            ],
            wiki_page_hits=[
                WikiPageHit(
                    slug="minimum-cut",
                    title="Minimum Cut",
                    page_type="concept",
                    summary="Separates source and sink.",
                    body="Max-flow min-cut duality explains why.",
                    course_key="cmsc_27100",
                    source_path="latex/cmsc_27100/notes.tex",
                    source_title="CMSC 27100 Notes",
                    section="Minimum Cut",
                    aliases=[],
                    score=9,
                )
            ],
            related_topics=[
                RelatedTopicHit(
                    slug="max-flow",
                    title="Max Flow",
                    relation="related_topic",
                )
            ],
        )

        main_module.render_retrieval_debug(retrieval_result)

        self.assertEqual(
            fake_streamlit.expander_labels,
            [
                "Retrieved chunks (1)",
                "Matched wiki pages (1)",
                "Related topics (1)",
            ],
        )
        self.assertTrue(any("Chunk 1" in text for text in fake_streamlit.text_calls))
        self.assertTrue(any("minimum-cut" in text for text in fake_streamlit.markdown_calls))
        self.assertTrue(any("max-flow" in text for text in fake_streamlit.markdown_calls))


class FakeStreamlit:
    def __init__(self) -> None:
        self.expander_labels: list[str] = []
        self.text_calls: list[str] = []
        self.markdown_calls: list[str] = []
        self.caption_calls: list[str] = []

    def expander(self, label: str):
        self.expander_labels.append(label)
        return _FakeContextManager()

    def text(self, value: str) -> None:
        self.text_calls.append(value)

    def markdown(self, value: str) -> None:
        self.markdown_calls.append(value)

    def caption(self, value: str) -> None:
        self.caption_calls.append(value)


class _FakeContextManager:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        return False


if __name__ == "__main__":
    unittest.main()
