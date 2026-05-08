from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from src.pipeline.chunker import chunk_all_pages
from src.pipeline.corpus import discover_corpus_paths, load_corpus_documents


class CorpusLoadingTests(unittest.TestCase):
    def test_discover_corpus_paths_finds_structured_files_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_path = Path(temporary_directory)
            markdown_path = data_path / "md" / "cmsc_27100"
            markdown_path.mkdir(parents=True)
            nested_markdown_path = markdown_path / "nested"
            nested_markdown_path.mkdir(parents=True)

            markdown_file = markdown_path / "cmsc_27100_fall_2025_pset1_ng.md"
            nested_markdown_file = nested_markdown_path / "cmsc_27100_fall_2025_notes_ng.md"
            ignored_file = markdown_path / "ignore.txt"

            markdown_file.write_text("# Problem 1\nProof text", encoding="utf-8")
            nested_markdown_file.write_text("# Notes\nExtra notes", encoding="utf-8")
            ignored_file.write_bytes(b"not relevant")

            discovered_paths = discover_corpus_paths(data_path)

            self.assertEqual(
                [path.relative_to(data_path).as_posix() for path in discovered_paths],
                [
                    "md/cmsc_27100/cmsc_27100_fall_2025_pset1_ng.md",
                    "md/cmsc_27100/nested/cmsc_27100_fall_2025_notes_ng.md",
                ],
            )

    def test_load_corpus_documents_preserves_structured_upload_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_path = Path(temporary_directory)
            markdown_path = data_path / "md" / "cmsc_27100"
            markdown_path.mkdir(parents=True)

            markdown_file = markdown_path / "cmsc_27100_fall_2025_pset1_ng.md"
            markdown_file.write_text(
                "# Problem 1\nDivide and conquer analysis.",
                encoding="utf-8",
            )

            documents, warnings = load_corpus_documents(data_path)

            self.assertEqual(warnings, [])
            self.assertEqual(len(documents), 1)

            document = documents[0]
            self.assertEqual(document.metadata["source_tree"], "md")
            self.assertEqual(document.metadata["course_folder"], "cmsc_27100")
            self.assertEqual(document.metadata["course_key"], "cmsc_27100")
            self.assertEqual(document.metadata["course_category"], "cmsc")
            self.assertEqual(document.metadata["course_number"], "27100")
            self.assertEqual(document.metadata["quarter"], "fall")
            self.assertEqual(document.metadata["year"], "2025")
            self.assertEqual(document.metadata["work_segment"], "pset1")
            self.assertEqual(document.metadata["work_type"], "pset")
            self.assertEqual(document.metadata["work_number"], "1")
            self.assertEqual(document.metadata["author"], "ng")
            self.assertEqual(
                document.metadata["source_path"],
                "md/cmsc_27100/cmsc_27100_fall_2025_pset1_ng.md",
            )
            self.assertIn("CMSC 27100", document.title)

    def test_load_corpus_documents_ignores_non_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_path = Path(temporary_directory)
            markdown_path = data_path / "md" / "cmsc_27100"
            markdown_path.mkdir(parents=True)

            markdown_file = markdown_path / "cmsc_27100_fall_2025_pset1_ng.md"
            ignored_text_file = markdown_path / "cmsc_27100_fall_2025_pset1_ng.txt"

            markdown_file.write_text(
                "# Problem 1\nMarkdown source content wins.",
                encoding="utf-8",
            )
            ignored_text_file.write_text("text file should be ignored", encoding="utf-8")

            documents, warnings = load_corpus_documents(data_path)

            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0].metadata["source_extension"], ".md")
            self.assertIn("Markdown source content wins.", documents[0].text)
            self.assertEqual(warnings, [])

    def test_chunk_all_pages_carries_document_metadata_into_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_path = Path(temporary_directory)
            markdown_path = data_path / "md" / "cmsc_27100"
            markdown_path.mkdir(parents=True)

            repeated_graph_text = "Shortest paths and graph cuts stay grounded in the course notes. " * 5
            repeated_tree_text = "Spanning trees and exchange arguments stay grounded in the course notes. " * 5
            markdown_file = markdown_path / "cmsc_27100_fall_2025_notes_ng.md"
            markdown_file.write_text(
                f"# Graphs\n{repeated_graph_text}\n"
                f"## Trees\n{repeated_tree_text}",
                encoding="utf-8",
            )

            documents, _ = load_corpus_documents(data_path)
            chunks = chunk_all_pages(
                [
                    (document.title, document.text, document.metadata)
                    for document in documents
                ]
            )

            self.assertEqual(len(chunks), 2)
            self.assertTrue(
                all(chunk.metadata["course_key"] == "cmsc_27100" for chunk in chunks)
            )
            self.assertEqual(
                [chunk.metadata["section"] for chunk in chunks],
                ["Graphs", "Trees"],
            )
            self.assertTrue(
                all(
                    chunk.metadata["source_path"].startswith("md/cmsc_27100/")
                    for chunk in chunks
                )
            )


if __name__ == "__main__":
    unittest.main()
