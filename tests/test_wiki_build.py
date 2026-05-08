from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from src.wiki.build import build_wiki


class WikiBuildTests(unittest.TestCase):
    def test_build_wiki_writes_database_report_and_source_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_path = Path(temporary_directory) / "data"
            markdown_path = data_path / "md" / "cmsc_27100"
            markdown_path.mkdir(parents=True)

            first_document_path = markdown_path / "cmsc_27100_fall_2025_notes_ng.md"
            second_document_path = markdown_path / "cmsc_27100_fall_2025_pset1_ng.md"

            first_document_path.write_text(
                "# Divide and Conquer\n"
                + ("Recurrence trees and master theorem explain the split and combine pattern. " * 5)
                + "\n## Dynamic Programming\n"
                + ("Optimal substructure and repeated subproblems guide the table design. " * 5),
                encoding="utf-8",
            )
            second_document_path.write_text(
                "# Dynamic Programming Practice\n"
                + ("Repeated subproblems and optimal substructure appear in shortest path exercises. " * 5)
                + "\n## Graph Review\n"
                + ("Graph traversal and path structure reuse earlier course notes for review. " * 5),
                encoding="utf-8",
            )

            database_path = data_path / "wiki.sqlite3"
            report_path = data_path / "wiki_report.md"

            pages, links, warnings = build_wiki(
                data_dir=str(data_path),
                database_path=str(database_path),
                report_path=str(report_path),
            )

            self.assertEqual(warnings, [])
            self.assertTrue(database_path.is_file())
            self.assertTrue(report_path.is_file())
            self.assertGreaterEqual(len(pages), 7)
            self.assertGreater(len(links), 0)

            with sqlite3.connect(database_path) as connection:
                page_count = connection.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
                source_count = connection.execute("SELECT COUNT(*) FROM page_sources").fetchone()[0]
                related_count = connection.execute(
                    "SELECT COUNT(*) FROM page_links WHERE relation = 'related_topic'"
                ).fetchone()[0]
                source_rows = connection.execute(
                    """
                    SELECT source_path, source_title
                    FROM page_sources
                    ORDER BY source_path, source_title
                    """
                ).fetchall()

            self.assertEqual(page_count, len(pages))
            self.assertEqual(source_count, len(pages))
            self.assertGreaterEqual(related_count, 1)
            self.assertIn(
                (
                    "md/cmsc_27100/cmsc_27100_fall_2025_notes_ng.md",
                    "CMSC 27100 fall 2025 notes ng",
                ),
                source_rows,
            )

            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("# StudyGraph Wiki Report", report_text)
            self.assertIn("Wiki pages created", report_text)
            self.assertIn(
                "`md/cmsc_27100/cmsc_27100_fall_2025_pset1_ng.md`",
                report_text,
            )


if __name__ == "__main__":
    unittest.main()
