import unittest

from src.app.uploads import (
    UploadValidationError,
    build_filename_stem,
    build_target_path,
    normalize_upload_metadata,
    validate_uploaded_file,
)


class UploadHelpersTests(unittest.TestCase):
    def test_normalize_upload_metadata_builds_expected_filename_stem(self) -> None:
        metadata = normalize_upload_metadata(
            course_category="CMSC",
            course_number="27100",
            quarter="fall",
            year="2025",
            work_type="pset",
            work_number="1",
            custom_work_type="",
            professor_last_name="Ng",
            submitter_email="student@example.edu",
            submission_note="",
        )

        self.assertEqual(build_filename_stem(metadata), "cmsc_27100_fall_2025_pset1_ng")

    def test_custom_work_type_is_normalized_to_lowercase_alphanumeric(self) -> None:
        metadata = normalize_upload_metadata(
            course_category="STAT",
            course_number="25100",
            quarter="win",
            year="2026",
            work_type="custom",
            work_number="99",
            custom_work_type="Take Home Exam 2",
            professor_last_name="Smith-Jones",
            submitter_email="student@example.edu",
            submission_note="",
        )

        self.assertEqual(build_filename_stem(metadata), "stat_25100_win_2026_takehomeexam2_smith-jones")

    def test_lecture_work_type_supports_numbered_filename_stem(self) -> None:
        metadata = normalize_upload_metadata(
            course_category="CMSC",
            course_number="27100",
            quarter="fall",
            year="2025",
            work_type="lec",
            work_number="2",
            custom_work_type="",
            professor_last_name="Ng",
            submitter_email="student@example.edu",
            submission_note="",
        )

        self.assertEqual(build_filename_stem(metadata), "cmsc_27100_fall_2025_lec2_ng")

    def test_target_path_uses_latex_tree_for_tex_files(self) -> None:
        metadata = normalize_upload_metadata(
            course_category="MATH",
            course_number="20400",
            quarter="win",
            year="2026",
            work_type="hw",
            work_number="1",
            custom_work_type="",
            professor_last_name="Janos",
            submitter_email="student@example.edu",
            submission_note="",
        )

        target_path = build_target_path(metadata, ".tex")

        self.assertEqual(
            target_path,
            "data/latex/math_20400/math_20400_win_2026_hw1_janos.tex",
        )

    def test_target_path_uses_pdf_tree_for_pdf_files(self) -> None:
        metadata = normalize_upload_metadata(
            course_category="MATH",
            course_number="20400",
            quarter="win",
            year="2026",
            work_type="hw",
            work_number="1",
            custom_work_type="",
            professor_last_name="Janos",
            submitter_email="student@example.edu",
            submission_note="",
        )

        target_path = build_target_path(metadata, ".pdf")

        self.assertEqual(
            target_path,
            "data/pdf/math_20400/math_20400_win_2026_hw1_janos.pdf",
        )

    def test_target_path_uses_markdown_tree_for_markdown_files(self) -> None:
        metadata = normalize_upload_metadata(
            course_category="MATH",
            course_number="20400",
            quarter="win",
            year="2026",
            work_type="hw",
            work_number="1",
            custom_work_type="",
            professor_last_name="Janos",
            submitter_email="student@example.edu",
            submission_note="",
        )

        target_path = build_target_path(metadata, ".md")

        self.assertEqual(
            target_path,
            "data/md/math_20400/math_20400_win_2026_hw1_janos.md",
        )

    def test_validate_uploaded_file_accepts_valid_tex_content(self) -> None:
        validated_upload = validate_uploaded_file(
            file_name="assignment.tex",
            file_bytes=b"\\section*{Problem #1}\nHello",
        )

        self.assertEqual(validated_upload.extension, ".tex")
        self.assertEqual(validated_upload.file_bytes, b"\\section*{Problem #1}\nHello")

    def test_validate_uploaded_file_accepts_valid_markdown_content(self) -> None:
        validated_upload = validate_uploaded_file(
            file_name="assignment.md",
            file_bytes=b"# Problem Set 1\n\nSolution notes",
        )

        self.assertEqual(validated_upload.extension, ".md")
        self.assertEqual(validated_upload.file_bytes, b"# Problem Set 1\n\nSolution notes")

    def test_validate_uploaded_file_rejects_empty_markdown_file(self) -> None:
        with self.assertRaises(UploadValidationError):
            validate_uploaded_file(
                file_name="assignment.md",
                file_bytes=b"",
            )

    def test_validate_uploaded_file_rejects_non_utf8_markdown_file(self) -> None:
        with self.assertRaises(UploadValidationError):
            validate_uploaded_file(
                file_name="assignment.md",
                file_bytes=b"\xff\xfe\x00\x00",
            )

    def test_validate_uploaded_file_rejects_invalid_pdf_header(self) -> None:
        with self.assertRaises(UploadValidationError):
            validate_uploaded_file(
                file_name="assignment.pdf",
                file_bytes=b"not a pdf",
            )

    def test_validate_uploaded_file_rejects_unsupported_extension(self) -> None:
        with self.assertRaises(UploadValidationError):
            validate_uploaded_file(
                file_name="assignment.docx",
                file_bytes=b"not supported",
            )

    def test_normalize_upload_metadata_rejects_invalid_professor_name(self) -> None:
        with self.assertRaises(UploadValidationError):
            normalize_upload_metadata(
                course_category="CMSC",
                course_number="27100",
                quarter="fall",
                year="2025",
                work_type="pset",
                work_number="1",
                custom_work_type="",
                professor_last_name="Ng 3",
                submitter_email="student@example.edu",
                submission_note="",
            )


if __name__ == "__main__":
    unittest.main()
