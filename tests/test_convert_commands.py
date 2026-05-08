from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.ingest.convert import (
    build_conversion_candidate,
    build_requested_conversion_candidates,
    detect_source_type_from_path,
    discover_missing_conversion_candidates,
)


class ConvertCommandTests(unittest.TestCase):
    def test_detect_source_type_from_unmatched_pdf_path(self) -> None:
        source_type = detect_source_type_from_path(
            Path("unmatched-pdf/cmsc_27100/cmsc_27100_fall_2025_pset1_ng.pdf")
        )

        self.assertEqual(source_type, "pdf")

    def test_build_conversion_candidate_maps_unmatched_tex_into_canonical_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_path = Path(temporary_directory)
            source_path = data_path / "unmatched-tex" / "cmsc_27100" / "cmsc_27100_fall_2025_pset1_ng.tex"
            source_path.parent.mkdir(parents=True)
            source_path.write_text("\\section{Problem 1}", encoding="utf-8")

            candidate = build_conversion_candidate(data_path, source_path)

        self.assertEqual(
            candidate.markdown_target_path,
            Path(temporary_directory) / "md" / "cmsc_27100" / "cmsc_27100_fall_2025_pset1_ng.md",
        )
        self.assertEqual(candidate.source_type, "tex")

    def test_discover_missing_conversion_candidates_prefers_tex_over_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_path = Path(temporary_directory)
            latex_path = data_path / "latex" / "cmsc_27100" / "cmsc_27100_fall_2025_pset1_ng.tex"
            pdf_path = data_path / "pdf" / "cmsc_27100" / "cmsc_27100_fall_2025_pset1_ng.pdf"
            latex_path.parent.mkdir(parents=True)
            pdf_path.parent.mkdir(parents=True)
            latex_path.write_text("\\section{Problem 1}", encoding="utf-8")
            pdf_path.write_bytes(b"%PDF-1.4")

            candidates = discover_missing_conversion_candidates(data_path, source_type="all")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].source_type, "tex")
        self.assertEqual(candidates[0].source_path, latex_path)

    def test_discover_missing_conversion_candidates_skips_existing_markdown_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_path = Path(temporary_directory)
            pdf_path = data_path / "unmatched-pdf" / "cmsc_27100" / "cmsc_27100_fall_2025_pset1_ng.pdf"
            markdown_path = data_path / "md" / "cmsc_27100" / "cmsc_27100_fall_2025_pset1_ng.md"
            pdf_path.parent.mkdir(parents=True)
            markdown_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF-1.4")
            markdown_path.write_text("# Existing Markdown", encoding="utf-8")

            candidates = discover_missing_conversion_candidates(data_path, source_type="all")

        self.assertEqual(candidates, [])

    def test_build_requested_conversion_candidates_rejects_source_type_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_path = Path(temporary_directory)
            pdf_path = data_path / "pdf" / "cmsc_27100" / "cmsc_27100_fall_2025_pset1_ng.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF-1.4")

            with self.assertRaises(ValueError):
                build_requested_conversion_candidates(
                    data_dir=data_path,
                    requested_paths=["pdf/cmsc_27100/cmsc_27100_fall_2025_pset1_ng.pdf"],
                    source_type="tex",
                )


if __name__ == "__main__":
    unittest.main()
