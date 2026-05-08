from __future__ import annotations

import importlib
import os
import sys
import types
import unittest
from unittest import mock

from src.pipeline.generator import (
    build_context,
    build_system_prompt,
    is_practice_generation_request,
)
from src.pipeline.retriever import (
    ChunkHit,
    RelatedTopicHit,
    RetrievalResult,
    WikiPageHit,
    retrieve,
)
from src.wiki.query import RelatedTopicMatch, WikiPageMatch


def import_main_module():
    os.environ["JENRAG_SKIP_STREAMLIT_BOOTSTRAP"] = "1"
    try:
        sys.modules.pop("src.app.main", None)
        streamlit_stub = types.ModuleType("streamlit")
        streamlit_stub.secrets = {}
        streamlit_agraph_stub = types.ModuleType("streamlit_agraph")
        streamlit_agraph_stub.agraph = lambda *args, **kwargs: None
        streamlit_agraph_stub.Node = object
        streamlit_agraph_stub.Edge = object
        streamlit_agraph_stub.Config = object
        with mock.patch.dict(
            sys.modules,
            {
                "streamlit": streamlit_stub,
                "streamlit_agraph": streamlit_agraph_stub,
            },
        ):
            return importlib.import_module("src.app.main")
    finally:
        os.environ.pop("JENRAG_SKIP_STREAMLIT_BOOTSTRAP", None)


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

    def test_is_practice_generation_request_detects_homework_generation_queries(self) -> None:
        self.assertTrue(
            is_practice_generation_request(
                "Create a new homework problem similar to problem 4."
            )
        )
        self.assertTrue(
            is_practice_generation_request(
                "Come up with a practice question about graph cuts."
            )
        )
        self.assertFalse(
            is_practice_generation_request(
                "Explain why the graph cut proof works."
            )
        )

    def test_build_system_prompt_adds_private_verification_rules_for_practice_requests(
        self,
    ) -> None:
        retrieval_result = RetrievalResult(
            chunk_hits=[
                ChunkHit(
                    text="Use max-flow min-cut duality to reason about cuts.",
                    title="CMSC 27100 Notes",
                    section="Minimum Cut",
                    source_path="latex/cmsc_27100/notes.tex",
                    course_key="cmsc_27100",
                    score=0.2,
                )
            ],
            wiki_page_hits=[],
            related_topics=[],
        )

        system_prompt = build_system_prompt(
            "Generate a new practice problem about graph cuts.",
            retrieval_result,
        )

        self.assertIn("you may create a NEW question", system_prompt)
        self.assertIn("solve it completely in private", system_prompt)
        self.assertIn("concise final answer or solution check", system_prompt)

    def test_build_system_prompt_leaves_normal_explanations_on_base_prompt(self) -> None:
        retrieval_result = RetrievalResult(
            chunk_hits=[],
            wiki_page_hits=[],
            related_topics=[],
        )

        system_prompt = build_system_prompt(
            "Explain the recurrence used in merge sort.",
            retrieval_result,
        )

        self.assertNotIn("solve it completely in private", system_prompt)
        self.assertNotIn("you may create a NEW question", system_prompt)

    def test_build_system_prompt_includes_conversation_memory_block(self) -> None:
        retrieval_result = RetrievalResult(
            chunk_hits=[],
            wiki_page_hits=[],
            related_topics=[],
        )

        system_prompt = build_system_prompt(
            "What does this relate to?",
            retrieval_result,
            conversation_memory_context="## Active References\n- [explained_concept] Max Flow",
        )

        self.assertIn("--- CONVERSATION MEMORY ---", system_prompt)
        self.assertIn("[explained_concept] Max Flow", system_prompt)
        self.assertIn("Use conversation memory only to resolve", system_prompt)


class StreamlitDebugRenderingTests(unittest.TestCase):
    def test_get_missing_upload_configuration_treats_placeholder_values_as_missing(
        self,
    ) -> None:
        main_module = import_main_module()

        with (
            mock.patch.object(main_module, "GITHUB_REPOSITORY", " enzeeo/JenRAG "),
            mock.patch.object(main_module, "GITHUB_UPLOAD_TOKEN", " None "),
        ):
            self.assertEqual(
                main_module.get_missing_upload_configuration(),
                ["GITHUB_UPLOAD_TOKEN"],
            )

    def test_build_github_upload_client_raises_clear_error_when_token_missing(self) -> None:
        main_module = import_main_module()

        with (
            mock.patch.object(main_module, "GITHUB_REPOSITORY", "enzeeo/JenRAG"),
            mock.patch.object(main_module, "GITHUB_UPLOAD_TOKEN", None),
        ):
            with self.assertRaises(main_module.GitHubUploadError) as raised_error:
                main_module.build_github_upload_client()

        self.assertIn("GITHUB_UPLOAD_TOKEN", str(raised_error.exception))

    def test_render_retrieval_debug_renders_chunks_wiki_pages_and_related_topics(self) -> None:
        main_module = import_main_module()
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

    def test_render_assistant_message_content_renders_inline_dollar_math(self) -> None:
        main_module = import_main_module()
        fake_streamlit = FakeStreamlit()
        main_module.st = fake_streamlit

        main_module.render_assistant_message_content("Probability is $p_i$ for item i.")

        self.assertEqual(
            fake_streamlit.markdown_calls,
            ["Probability is $p_i$ for item i."],
        )
        self.assertEqual(fake_streamlit.latex_calls, [])

    def test_render_assistant_message_content_normalizes_inline_parentheses_math(self) -> None:
        main_module = import_main_module()
        fake_streamlit = FakeStreamlit()
        main_module.st = fake_streamlit

        main_module.render_assistant_message_content("Probability is \\(p_i\\) for item i.")

        self.assertEqual(
            fake_streamlit.markdown_calls,
            ["Probability is $p_i$ for item i."],
        )
        self.assertEqual(fake_streamlit.latex_calls, [])

    def test_render_assistant_message_content_renders_display_dollar_math(self) -> None:
        main_module = import_main_module()
        fake_streamlit = FakeStreamlit()
        main_module.st = fake_streamlit

        main_module.render_assistant_message_content(
            "Indices:\n\n$$i \\in \\{1, \\ldots, n\\}$$\n\nDone."
        )

        self.assertEqual(fake_streamlit.markdown_calls, ["Indices:\n\n", "\n\nDone."])
        self.assertEqual(fake_streamlit.latex_calls, ["i \\in \\{1, \\ldots, n\\}"])

    def test_render_assistant_message_content_renders_display_bracket_math(self) -> None:
        main_module = import_main_module()
        fake_streamlit = FakeStreamlit()
        main_module.st = fake_streamlit

        main_module.render_assistant_message_content(
            "Indices:\n\n\\[i \\in \\{1, \\ldots, n\\}\\]\n\nDone."
        )

        self.assertEqual(fake_streamlit.markdown_calls, ["Indices:\n\n", "\n\nDone."])
        self.assertEqual(fake_streamlit.latex_calls, ["i \\in \\{1, \\ldots, n\\}"])

    def test_render_assistant_message_content_keeps_mixed_prose_order(self) -> None:
        main_module = import_main_module()
        fake_streamlit = FakeStreamlit()
        main_module.st = fake_streamlit

        main_module.render_assistant_message_content(
            "Start $p_i$ middle $$q_i = q_{i-1} + 1$$ end."
        )

        self.assertEqual(fake_streamlit.markdown_calls, ["Start $p_i$ middle ", " end."])
        self.assertEqual(fake_streamlit.latex_calls, ["q_i = q_{i-1} + 1"])

    def test_render_assistant_message_content_falls_back_for_unclosed_inline_math(self) -> None:
        main_module = import_main_module()
        fake_streamlit = FakeStreamlit()
        main_module.st = fake_streamlit

        main_module.render_assistant_message_content("Broken math starts at \\(p_i and stays raw.")

        self.assertEqual(
            fake_streamlit.markdown_calls,
            ["Broken math starts at \\(p_i and stays raw."],
        )
        self.assertEqual(fake_streamlit.latex_calls, [])

    def test_resolve_follow_up_query_uses_recent_explained_concept(self) -> None:
        main_module = import_main_module()
        memory_state = main_module.build_initial_conversation_memory_state()
        concept_entity = main_module.build_conversation_entity(
            entity_type="explained_concept",
            label="Dynamic Programming",
            canonical_text="Dynamic programming solves overlapping subproblems.",
            source_turn_index=2,
            related_hints=["Lecture 8"],
        )
        memory_state.conversation_entities = [concept_entity]
        memory_state.active_references = [
            main_module.ConversationReferenceState(
                entity_id=concept_entity.entity_id,
                entity_type=concept_entity.entity_type,
                label=concept_entity.label,
                source_turn_index=concept_entity.source_turn_index,
                reason="recent explanation",
            )
        ]

        resolution = main_module.resolve_follow_up_query(
            "I don't understand that part.",
            memory_state,
        )

        self.assertTrue(resolution.is_follow_up)
        self.assertEqual(resolution.resolution_confidence, "high")
        self.assertIn("Dynamic Programming", resolution.resolved_query_text)

    def test_resolve_follow_up_query_prefers_source_section_for_note_grounding(self) -> None:
        main_module = import_main_module()
        memory_state = main_module.build_initial_conversation_memory_state()
        section_entity = main_module.build_conversation_entity(
            entity_type="source_section",
            label="Lecture 5 - Max Flow",
            canonical_text="Source: lecture notes on augmenting paths.",
            source_turn_index=6,
            related_hints=["CMSC 27200 Notes"],
        )
        memory_state.conversation_entities = [section_entity]
        memory_state.active_references = main_module.build_active_references_from_entities(
            memory_state.conversation_entities
        )

        resolution = main_module.resolve_follow_up_query(
            "Where did that come from in the notes?",
            memory_state,
        )

        self.assertEqual(resolution.resolved_reference_entities[0].entity_type, "source_section")
        self.assertIn("Lecture 5 - Max Flow", resolution.resolved_query_text)

    def test_resolve_follow_up_query_returns_low_confidence_when_memory_empty(self) -> None:
        main_module = import_main_module()
        memory_state = main_module.build_initial_conversation_memory_state()

        resolution = main_module.resolve_follow_up_query(
            "What does this relate to?",
            memory_state,
        )

        self.assertTrue(resolution.is_follow_up)
        self.assertEqual(resolution.resolution_confidence, "low")
        self.assertEqual(
            resolution.unresolved_reason,
            "Follow-up target is unclear from current session memory.",
        )

    def test_compact_conversation_memory_preserves_summary_recent_turns_and_entities(self) -> None:
        main_module = import_main_module()
        memory_state = main_module.build_initial_conversation_memory_state()

        for content in (
            "Explain max flow.",
            "Max flow pushes capacity through a graph.",
            "What is a common exam trap here?",
            "Confusing residual edges with original edges is a trap.",
            "Where was that in the notes?",
            "Lecture 9 discusses residual graphs directly.",
        ):
            role = "user" if len(memory_state.recent_turns) % 2 == 0 else "assistant"
            main_module.store_conversation_turn(memory_state, role, content)

        archived_entity = main_module.build_conversation_entity(
            entity_type="exam_trap",
            label="Residual edges trap",
            canonical_text="Do not confuse residual capacity with original capacity.",
            source_turn_index=2,
            related_hints=["Residual graph"],
        )
        retained_entity = main_module.build_conversation_entity(
            entity_type="source_section",
            label="Lecture 9 residual graph notes",
            canonical_text="Lecture 9 covers residual graphs.",
            source_turn_index=6,
            related_hints=["Lecture 9"],
        )
        memory_state.conversation_entities = [archived_entity, retained_entity]

        main_module.compact_conversation_memory(memory_state, maximum_token_budget=1)

        self.assertEqual(len(memory_state.recent_turns), main_module.COMPACTION_RECENT_TURN_COUNT)
        self.assertIn(
            "Residual edges trap",
            memory_state.compacted_summary["exam_traps"],
        )
        self.assertEqual(len(memory_state.conversation_entities), 1)
        self.assertEqual(memory_state.conversation_entities[0].label, retained_entity.label)
        self.assertEqual(memory_state.compaction_metadata["compaction_count"], 1)

    def test_run_pipeline_uses_resolved_query_for_retrieval_and_passes_memory_to_generation(self) -> None:
        main_module = import_main_module()
        memory_state = main_module.build_initial_conversation_memory_state()
        concept_entity = main_module.build_conversation_entity(
            entity_type="explained_concept",
            label="Greedy stays ahead",
            canonical_text="This proof compares the greedy prefix against any optimal prefix.",
            source_turn_index=2,
        )
        memory_state.conversation_entities = [concept_entity]
        memory_state.active_references = main_module.build_active_references_from_entities(
            memory_state.conversation_entities
        )
        retrieval_result = RetrievalResult(chunk_hits=[], wiki_page_hits=[], related_topics=[])

        with (
            mock.patch.object(main_module, "retrieve", return_value=retrieval_result) as retrieve_mock,
            mock.patch.object(main_module, "generate", return_value="Answer text") as generate_mock,
        ):
            result = main_module.run_pipeline(
                "I don't understand that part.",
                memory_state,
                use_reranker=True,
                rerank_top_k=5,
            )

        retrieve_mock.assert_called_once()
        self.assertIn("Greedy stays ahead", retrieve_mock.call_args.args[0])
        generate_mock.assert_called_once()
        self.assertIn(
            "Greedy stays ahead",
            generate_mock.call_args.kwargs["conversation_memory_context"],
        )
        self.assertEqual(result["answer"], "Answer text")

    def test_run_pipeline_falls_back_when_generate_rejects_memory_keyword(self) -> None:
        main_module = import_main_module()
        memory_state = main_module.build_initial_conversation_memory_state()
        retrieval_result = RetrievalResult(chunk_hits=[], wiki_page_hits=[], related_topics=[])

        def fake_generate(*args, **kwargs):
            if "conversation_memory_context" in kwargs:
                raise TypeError(
                    "generate() got an unexpected keyword argument 'conversation_memory_context'"
                )
            return "Fallback answer"

        with (
            mock.patch.object(main_module, "retrieve", return_value=retrieval_result),
            mock.patch.object(main_module, "generate", side_effect=fake_generate) as generate_mock,
        ):
            result = main_module.run_pipeline(
                "Explain max flow.",
                memory_state,
                use_reranker=True,
                rerank_top_k=5,
            )

        self.assertEqual(generate_mock.call_count, 2)
        self.assertEqual(result["answer"], "Fallback answer")

    def test_inject_application_theme_includes_bottom_chat_composer_rules(self) -> None:
        main_module = import_main_module()
        fake_streamlit = FakeStreamlit()
        main_module.st = fake_streamlit

        main_module.inject_application_theme()

        injected_theme = "".join(fake_streamlit.markdown_calls)
        self.assertIn('[data-testid="stAppViewBlockContainer"]', injected_theme)
        self.assertIn("padding-bottom: 6rem", injected_theme)
        self.assertIn('[data-testid="stChatInput"]', injected_theme)
        self.assertIn("position: fixed !important", injected_theme)
        self.assertIn("left: var(--jenrag-chat-composer-left, 1rem)", injected_theme)
        self.assertIn("transform: none", injected_theme)
        self.assertIn(
            "width: var(--jenrag-chat-composer-width, calc(100vw - (1rem * 2)))",
            injected_theme,
        )
        self.assertIn("max-width: calc(100vw - (1rem * 2))", injected_theme)
        self.assertIn("padding-bottom: max(1rem, env(safe-area-inset-bottom))", injected_theme)
        self.assertIn('[data-testid="stChatInput"] textarea', injected_theme)
        self.assertNotIn('[data-testid="stBottom"]', injected_theme)
        self.assertIn("env(safe-area-inset-bottom)", injected_theme)
        self.assertIn("ResizeObserver", injected_theme)
        self.assertIn("MutationObserver", injected_theme)
        self.assertIn("--jenrag-chat-composer-left", injected_theme)
        self.assertIn("--jenrag-chat-composer-width", injected_theme)


class StreamlitSidebarWikiGraphTests(unittest.TestCase):
    def test_build_sidebar_wiki_graph_hover_title_keeps_short_title(self) -> None:
        main_module = import_main_module()

        self.assertEqual(
            main_module.build_sidebar_wiki_graph_hover_title(
                "Merge Sort",
                "concept",
            ),
            "Merge Sort",
        )

    def test_build_sidebar_wiki_graph_hover_title_shortens_long_specific_title(self) -> None:
        main_module = import_main_module()

        self.assertEqual(
            main_module.build_sidebar_wiki_graph_hover_title(
                "CMSC 27100 Notes — Dynamic Programming Recurrence Optimization Tricks",
                "section",
            ),
            "Dynamic Programming Recurrence Optim...",
        )

    def test_build_sidebar_wiki_graph_hover_title_uses_non_generic_segment(self) -> None:
        main_module = import_main_module()

        self.assertEqual(
            main_module.build_sidebar_wiki_graph_hover_title(
                "CMSC 27100 Notes — Section 3",
                "section",
            ),
            "CMSC 27100 Notes",
        )

    def test_build_sidebar_wiki_graph_payload_returns_none_without_graph_loader(self) -> None:
        main_module = import_main_module()
        main_module.load_wiki_graph_neighborhood = None

        retrieval_result = RetrievalResult(
            chunk_hits=[],
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
                    aliases=[],
                    score=10,
                )
            ],
            related_topics=[],
        )

        self.assertIsNone(
            main_module.build_sidebar_wiki_graph_payload(retrieval_result)
        )

    def test_build_sidebar_wiki_graph_payload_marks_primary_match_and_hover_title(self) -> None:
        main_module = import_main_module()
        main_module.load_wiki_graph_neighborhood = mock.Mock(
            return_value=(
                [
                    main_module.wiki_query_module.WikiGraphNode(
                        slug="merge-sort",
                        title="CMSC 27100 Notes — Merge Sort",
                        page_type="concept",
                        is_seed=True,
                    ),
                    main_module.wiki_query_module.WikiGraphNode(
                        slug="master-theorem",
                        title="CMSC 27100 Notes — Section 4",
                        page_type="section",
                        is_seed=False,
                    ),
                ],
                [],
            )
        )

        retrieval_result = RetrievalResult(
            chunk_hits=[],
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
                    aliases=[],
                    score=10,
                ),
                WikiPageHit(
                    slug="master-theorem",
                    title="Master Theorem",
                    page_type="concept",
                    summary="Analyze divide-and-conquer recurrences.",
                    body="Pick the correct comparison case.",
                    course_key="cmsc_27100",
                    source_path="latex/cmsc_27100/notes.tex",
                    source_title="CMSC 27100 Notes",
                    section="Master Theorem",
                    aliases=[],
                    score=9,
                ),
            ],
            related_topics=[],
        )

        graph_payload = main_module.build_sidebar_wiki_graph_payload(retrieval_result)

        assert graph_payload is not None
        self.assertEqual(graph_payload["nodes"][0]["slug"], "merge-sort")
        self.assertTrue(graph_payload["nodes"][0]["is_primary_match"])
        self.assertEqual(graph_payload["nodes"][0]["hover_title"], "Merge Sort")
        self.assertFalse(graph_payload["nodes"][1]["is_primary_match"])
        self.assertEqual(graph_payload["nodes"][1]["hover_title"], "CMSC 27100 Notes")

    def test_render_sidebar_shows_graph_panel_after_wiki_status(self) -> None:
        main_module = import_main_module()
        fake_streamlit = FakeStreamlit()
        main_module.st = fake_streamlit

        with mock.patch.object(main_module, "wiki_database_exists", return_value=True):
            use_reranker, rerank_top_k = main_module.render_sidebar()

        self.assertTrue(use_reranker)
        self.assertEqual(rerank_top_k, 5)
        wiki_status_index = fake_streamlit.call_log.index(
            ("caption", "Wiki sidecar: available")
        )
        graph_title_index = fake_streamlit.call_log.index(
            ("markdown", "**Local Wiki Graph**")
        )
        self.assertLess(wiki_status_index, graph_title_index)

    def test_render_sidebar_shows_empty_state_without_graph_payload(self) -> None:
        main_module = import_main_module()
        fake_streamlit = FakeStreamlit()
        main_module.st = fake_streamlit

        with mock.patch.object(main_module, "wiki_database_exists", return_value=True):
            main_module.render_sidebar()

        self.assertIn(
            "No wiki graph for this query yet.",
            fake_streamlit.caption_calls,
        )

    def test_render_sidebar_shows_conversation_memory_panel(self) -> None:
        main_module = import_main_module()
        fake_streamlit = FakeStreamlit()
        fake_streamlit.session_state[main_module.CONVERSATION_MEMORY_STATE_KEY] = (
            main_module.build_initial_conversation_memory_state()
        )
        fake_streamlit.session_state[
            main_module.CONVERSATION_MEMORY_STATE_KEY
        ].conversation_entities = [
            main_module.build_conversation_entity(
                entity_type="explained_concept",
                label="Minimum Cut",
                canonical_text="Minimum cut separates source and sink.",
                source_turn_index=2,
            )
        ]
        fake_streamlit.session_state[
            main_module.CONVERSATION_MEMORY_STATE_KEY
        ].active_references = main_module.build_active_references_from_entities(
            fake_streamlit.session_state[
                main_module.CONVERSATION_MEMORY_STATE_KEY
            ].conversation_entities
        )
        main_module.st = fake_streamlit

        with mock.patch.object(main_module, "wiki_database_exists", return_value=True):
            main_module.render_sidebar()

        self.assertIn("**Conversation Memory**", fake_streamlit.markdown_calls)
        self.assertTrue(
            any("Tracked entities: 1" in value for value in fake_streamlit.caption_calls)
        )

    def test_render_sidebar_uses_graph_renderer_for_cached_payload(self) -> None:
        main_module = import_main_module()
        fake_streamlit = FakeStreamlit()
        fake_streamlit.session_state["sidebar_wiki_graph"] = {
            "nodes": [
                {
                    "slug": "merge-sort",
                    "title": "Merge Sort",
                    "hover_title": "Merge Sort",
                    "page_type": "concept",
                    "is_seed": True,
                    "is_primary_match": True,
                },
                {
                    "slug": "master-theorem",
                    "title": "Master Theorem",
                    "hover_title": "Master Theorem",
                    "page_type": "concept",
                    "is_seed": False,
                    "is_primary_match": False,
                },
            ],
            "edges": [
                {
                    "from_slug": "merge-sort",
                    "to_slug": "master-theorem",
                    "relation": "related_topic",
                }
            ],
        }
        main_module.st = fake_streamlit
        main_module.Node = FakeGraphNode
        main_module.Edge = FakeGraphEdge
        main_module.Config = FakeGraphConfig
        main_module.agraph = mock.Mock(return_value="merge-sort")

        with mock.patch.object(main_module, "wiki_database_exists", return_value=True):
            main_module.render_sidebar()

        main_module.agraph.assert_called_once()
        graph_call = main_module.agraph.call_args.kwargs
        self.assertEqual(len(graph_call["nodes"]), 2)
        self.assertEqual(len(graph_call["edges"]), 1)
        self.assertEqual(
            graph_call["nodes"][0].kwargs["color"],
            main_module.SIDEBAR_WIKI_GRAPH_PRIMARY_NODE_COLOR,
        )
        self.assertEqual(graph_call["nodes"][0].kwargs["title"], "Merge Sort")
        self.assertEqual(
            graph_call["nodes"][1].kwargs["color"],
            main_module.SIDEBAR_WIKI_GRAPH_RELATED_COLOR,
        )

    def test_render_chat_tab_reruns_after_storing_graph_payload(self) -> None:
        main_module = import_main_module()
        fake_streamlit = FakeStreamlit()
        fake_streamlit.chat_input_value = "Explain max flow."
        main_module.st = fake_streamlit

        retrieval_result = RetrievalResult(
            chunk_hits=[],
            wiki_page_hits=[],
            related_topics=[],
        )
        graph_payload = {
            "nodes": [
                {
                    "slug": "max-flow",
                    "title": "Max Flow",
                    "page_type": "concept",
                    "is_seed": True,
                }
            ],
            "edges": [],
        }
        pipeline_result = {
            "answer": "Max flow finds the largest feasible flow.",
            "retrieval": retrieval_result,
            "timings": {
                "retrieval": 0.1,
                "generation": 0.2,
                "total": 0.3,
            },
        }

        with (
            mock.patch.object(main_module, "run_pipeline", return_value=pipeline_result),
            mock.patch.object(
                main_module,
                "build_sidebar_wiki_graph_payload",
                return_value=graph_payload,
            ),
        ):
            main_module.render_chat_tab(use_reranker=True, rerank_top_k=5)

        self.assertEqual(
            fake_streamlit.session_state[main_module.SIDEBAR_WIKI_GRAPH_STATE_KEY],
            graph_payload,
        )
        self.assertEqual(len(fake_streamlit.session_state["messages"]), 2)
        self.assertEqual(fake_streamlit.session_state["messages"][0]["role"], "user")
        self.assertEqual(
            fake_streamlit.session_state["messages"][1]["content"],
            "Max flow finds the largest feasible flow.",
        )
        self.assertIn(("rerun", None), fake_streamlit.call_log)

    def test_render_chat_tab_renders_existing_messages_before_chat_input(self) -> None:
        main_module = import_main_module()
        fake_streamlit = FakeStreamlit()
        fake_streamlit.session_state["messages"] = [
            {"role": "user", "content": "First question."},
            {"role": "assistant", "content": "First answer."},
        ]
        main_module.st = fake_streamlit

        with mock.patch.object(main_module, "render_assistant_message_content") as render_mock:
            main_module.render_chat_tab(use_reranker=True, rerank_top_k=5)

        self.assertEqual(
            fake_streamlit.call_log.count(
                (
                    "chat_input",
                    "Ask about homework, exam problems, solutions, notes, and concepts...",
                )
            ),
            1,
        )
        first_user_message_index = fake_streamlit.call_log.index(("chat_message", "user"))
        assistant_message_index = fake_streamlit.call_log.index(("chat_message", "assistant"))
        chat_input_index = fake_streamlit.call_log.index(
            (
                "chat_input",
                "Ask about homework, exam problems, solutions, notes, and concepts...",
            )
        )
        self.assertLess(first_user_message_index, chat_input_index)
        self.assertLess(assistant_message_index, chat_input_index)
        render_mock.assert_called_once_with("First answer.")

    def test_render_sidebar_clear_chat_resets_messages_and_memory(self) -> None:
        main_module = import_main_module()
        fake_streamlit = FakeStreamlit()
        fake_streamlit.session_state["messages"] = [{"role": "user", "content": "Explain DP."}]
        fake_streamlit.session_state[main_module.SIDEBAR_WIKI_GRAPH_STATE_KEY] = {"nodes": []}
        fake_streamlit.session_state[main_module.CONVERSATION_MEMORY_STATE_KEY] = (
            main_module.build_initial_conversation_memory_state()
        )
        fake_streamlit.session_state[
            main_module.CONVERSATION_MEMORY_STATE_KEY
        ].conversation_entities = [
            main_module.build_conversation_entity(
                entity_type="explained_concept",
                label="Dynamic Programming",
                canonical_text="DP solves overlapping subproblems.",
                source_turn_index=2,
            )
        ]
        fake_streamlit.button_results["Clear Chat"] = True
        main_module.st = fake_streamlit

        with mock.patch.object(main_module, "wiki_database_exists", return_value=True):
            main_module.render_sidebar()

        self.assertEqual(fake_streamlit.session_state["messages"], [])
        self.assertEqual(
            fake_streamlit.session_state[
                main_module.CONVERSATION_MEMORY_STATE_KEY
            ].conversation_entities,
            [],
        )
        self.assertNotIn(main_module.SIDEBAR_WIKI_GRAPH_STATE_KEY, fake_streamlit.session_state)
        self.assertIn(("rerun", None), fake_streamlit.call_log)


class FakeStreamlit:
    def __init__(self) -> None:
        self.sidebar = _FakeContextManager()
        self.session_state = _FakeSessionState()
        self.call_log: list[tuple[str, object]] = []
        self.header_calls: list[str] = []
        self.expander_labels: list[str] = []
        self.text_calls: list[str] = []
        self.markdown_calls: list[str] = []
        self.latex_calls: list[str] = []
        self.caption_calls: list[str] = []
        self.container_calls: list[bool] = []
        self.chat_input_value: str | None = None
        self.button_results: dict[str, bool] = {}

    def header(self, value: str) -> None:
        self.header_calls.append(value)
        self.call_log.append(("header", value))

    def toggle(self, label: str, value: bool = False) -> bool:
        self.call_log.append(("toggle", label))
        return value

    def slider(self, label: str, minimum: int, maximum: int, value: int) -> int:
        self.call_log.append(("slider", label))
        return value

    def button(self, label: str, use_container_width: bool = False) -> bool:
        self.call_log.append(("button", label))
        return self.button_results.get(label, False)

    def divider(self) -> None:
        self.call_log.append(("divider", None))

    def expander(self, label: str):
        self.expander_labels.append(label)
        self.call_log.append(("expander", label))
        return _FakeContextManager()

    def text(self, value: str) -> None:
        self.text_calls.append(value)
        self.call_log.append(("text", value))

    def markdown(self, value: str, **kwargs) -> None:
        self.markdown_calls.append(value)
        self.call_log.append(("markdown", value))

    def latex(self, value: str) -> None:
        self.latex_calls.append(value)
        self.call_log.append(("latex", value))

    def caption(self, value: str) -> None:
        self.caption_calls.append(value)
        self.call_log.append(("caption", value))

    def container(self, border: bool = False):
        self.container_calls.append(border)
        self.call_log.append(("container", border))
        return _FakeContextManager()

    def rerun(self) -> None:
        self.call_log.append(("rerun", None))

    def chat_input(self, prompt: str) -> str | None:
        self.call_log.append(("chat_input", prompt))
        return self.chat_input_value

    def chat_message(self, role: str):
        self.call_log.append(("chat_message", role))
        return _FakeContextManager()

    def spinner(self, value: str):
        self.call_log.append(("spinner", value))
        return _FakeContextManager()

    def columns(self, count: int):
        self.call_log.append(("columns", count))
        return [_FakeMetricColumn(self) for _ in range(count)]

    def metric(self, label: str, value: str) -> None:
        self.call_log.append(("metric", (label, value)))


class _FakeMetricColumn:
    def __init__(self, streamlit_instance: FakeStreamlit) -> None:
        self.streamlit_instance = streamlit_instance

    def metric(self, label: str, value: str) -> None:
        self.streamlit_instance.call_log.append(("metric", (label, value)))


class _FakeSessionState(dict[str, object]):
    def __getattr__(self, name: str) -> object:
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(name) from error

    def __setattr__(self, name: str, value: object) -> None:
        self[name] = value


class FakeGraphNode:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class FakeGraphEdge:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class FakeGraphConfig:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class _FakeContextManager:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        return False


if __name__ == "__main__":
    unittest.main()
