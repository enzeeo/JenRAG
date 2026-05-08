from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from src.wiki.build import initialize_database
from src.wiki.query import load_wiki_graph_neighborhood


class WikiGraphNeighborhoodTests(unittest.TestCase):
    def test_load_wiki_graph_neighborhood_returns_seed_nodes_and_related_topics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = self.create_wiki_database(Path(temporary_directory))

            nodes, edges = load_wiki_graph_neighborhood(
                ["merge-sort"],
                database_path=str(database_path),
            )

        returned_slugs = {node.slug for node in nodes}
        self.assertEqual(returned_slugs, {"merge-sort", "master-theorem", "sorting"})
        self.assertTrue(any(node.slug == "merge-sort" and node.is_seed for node in nodes))
        self.assertIn(
            ("merge-sort", "master-theorem", "related_topic"),
            {(edge.from_slug, edge.to_slug, edge.relation) for edge in edges},
        )

    def test_load_wiki_graph_neighborhood_excludes_duplicates_and_self_loops(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = self.create_wiki_database(Path(temporary_directory))

            nodes, edges = load_wiki_graph_neighborhood(
                ["merge-sort", "merge-sort"],
                database_path=str(database_path),
            )

        self.assertEqual([node.slug for node in nodes].count("merge-sort"), 1)
        self.assertFalse(
            any(edge.from_slug == edge.to_slug for edge in edges)
        )

    def test_load_wiki_graph_neighborhood_returns_empty_results_for_empty_seed_list(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = self.create_wiki_database(Path(temporary_directory))

            nodes, edges = load_wiki_graph_neighborhood(
                [],
                database_path=str(database_path),
            )

        self.assertEqual(nodes, [])
        self.assertEqual(edges, [])

    def test_load_wiki_graph_neighborhood_does_not_include_unrelated_global_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = self.create_wiki_database(Path(temporary_directory))

            nodes, edges = load_wiki_graph_neighborhood(
                ["merge-sort"],
                database_path=str(database_path),
            )

        returned_slugs = {node.slug for node in nodes}
        self.assertNotIn("ford-fulkerson", returned_slugs)
        self.assertFalse(
            any(edge.to_slug == "ford-fulkerson" for edge in edges)
        )

    def create_wiki_database(self, temporary_directory: Path) -> Path:
        database_path = temporary_directory / "wiki.sqlite3"
        with sqlite3.connect(database_path) as connection:
            initialize_database(connection)
            connection.executemany(
                """
                INSERT INTO pages (
                    slug, title, page_type, summary, body, course_key, source_path, source_title, section
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "merge-sort",
                        "Merge Sort",
                        "concept",
                        "Sort by split and merge.",
                        "Uses divide and conquer recursion.",
                        "cmsc_27100",
                        "md/cmsc_27100/notes.md",
                        "Notes",
                        "Sorting",
                    ),
                    (
                        "master-theorem",
                        "Master Theorem",
                        "concept",
                        "Solves divide and conquer recurrences.",
                        "Useful for recurrence analysis.",
                        "cmsc_27100",
                        "md/cmsc_27100/notes.md",
                        "Notes",
                        "Analysis",
                    ),
                    (
                        "sorting",
                        "Sorting",
                        "topic",
                        "Ordering values.",
                        "Parent topic for sorting algorithms.",
                        "cmsc_27100",
                        "md/cmsc_27100/notes.md",
                        "Notes",
                        "Overview",
                    ),
                    (
                        "ford-fulkerson",
                        "Ford-Fulkerson",
                        "concept",
                        "Max flow algorithm.",
                        "Unrelated graph algorithm page.",
                        "cmsc_27100",
                        "md/cmsc_27100/flows.md",
                        "Flows",
                        "Max Flow",
                    ),
                ],
            )
            connection.executemany(
                """
                INSERT INTO page_links (from_slug, to_slug, relation)
                VALUES (?, ?, ?)
                """,
                [
                    ("merge-sort", "master-theorem", "related_topic"),
                    ("merge-sort", "master-theorem", "related_topic"),
                    ("merge-sort", "sorting", "related_topic"),
                    ("merge-sort", "merge-sort", "related_topic"),
                    ("master-theorem", "merge-sort", "prerequisite"),
                    ("sorting", "merge-sort", "structural_parent"),
                    ("ford-fulkerson", "master-theorem", "related_topic"),
                ],
            )
            connection.commit()
        return database_path


if __name__ == "__main__":
    unittest.main()
