from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.ingest.embed import load_documents_or_exit
from src.pipeline.vectorstore import delete_chunks_by_source_path, get_embedded_source_paths


class VectorstoreHelpersTests(unittest.TestCase):
    def test_get_embedded_source_paths_collects_unique_source_paths(self) -> None:
        fake_collection = mock.Mock()
        fake_collection.get.return_value = {
            "metadatas": [
                {"source_path": "md/cmsc_27100/doc1.md"},
                {"source_path": "md/cmsc_27100/doc1.md"},
                {"source_path": "md/cmsc_27100/doc2.md"},
                {},
                None,
            ]
        }

        source_paths = get_embedded_source_paths(fake_collection)

        self.assertEqual(
            source_paths,
            {"md/cmsc_27100/doc1.md", "md/cmsc_27100/doc2.md"},
        )

    def test_delete_chunks_by_source_path_uses_metadata_filter(self) -> None:
        fake_collection = mock.Mock()

        delete_chunks_by_source_path(fake_collection, "md/cmsc_27100/doc1.md")

        fake_collection.delete.assert_called_once_with(
            where={"source_path": "md/cmsc_27100/doc1.md"}
        )


class EmbedCommandPathTests(unittest.TestCase):
    def test_load_documents_or_exit_accepts_specific_markdown_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_path = Path(temporary_directory)
            markdown_directory = data_path / "md" / "cmsc_27100"
            markdown_directory.mkdir(parents=True)
            markdown_file = markdown_directory / "cmsc_27100_fall_2025_pset1_ng.md"
            markdown_file.write_text("# Problem 1\nProof", encoding="utf-8")

            with mock.patch("src.ingest.embed.DATA_DIR", str(data_path)):
                documents = load_documents_or_exit(
                    ["md/cmsc_27100/cmsc_27100_fall_2025_pset1_ng.md"]
                )

        self.assertEqual(len(documents), 1)
        self.assertEqual(
            documents[0].metadata["source_path"],
            "md/cmsc_27100/cmsc_27100_fall_2025_pset1_ng.md",
        )

    def test_load_documents_or_exit_rejects_non_markdown_requested_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_path = Path(temporary_directory)
            latex_directory = data_path / "latex" / "cmsc_27100"
            latex_directory.mkdir(parents=True)
            latex_file = latex_directory / "cmsc_27100_fall_2025_pset1_ng.tex"
            latex_file.write_text("\\section{Problem 1}", encoding="utf-8")

            with mock.patch("src.ingest.embed.DATA_DIR", str(data_path)):
                with self.assertRaises(SystemExit):
                    load_documents_or_exit(
                        ["latex/cmsc_27100/cmsc_27100_fall_2025_pset1_ng.tex"]
                    )


if __name__ == "__main__":
    unittest.main()
