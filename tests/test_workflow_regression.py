from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest
from unittest import mock

from src import workflow_regression


class WorkflowRegressionTests(unittest.TestCase):
    def test_run_workflow_regression_builds_fixture_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            summary = workflow_regression.run_workflow_regression(
                working_directory=Path(temporary_directory)
            )

            self.assertGreater(summary.chunk_count, 0)
            self.assertGreater(summary.wiki_page_count, 0)
            self.assertEqual(summary.evaluation_case_count, 2)
            self.assertTrue(summary.artifacts.chroma_db_path.is_dir())
            self.assertTrue(summary.artifacts.wiki_db_path.is_file())
            self.assertTrue(summary.artifacts.wiki_report_path.is_file())
            self.assertTrue(summary.artifacts.eval_results_path.is_file())

            saved_results = json.loads(
                summary.artifacts.eval_results_path.read_text(encoding="utf-8")
            )
            self.assertEqual(len(saved_results), 2)
            self.assertTrue(all(result["num_chunks"] > 0 for result in saved_results))
            self.assertTrue(all(result["num_wiki_pages"] > 0 for result in saved_results))

    def test_run_workflow_regression_reports_app_runtime_phase(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with mock.patch.object(
                workflow_regression,
                "check_app_runtime",
                side_effect=RuntimeError("import broke"),
            ):
                with self.assertRaises(workflow_regression.WorkflowPhaseError) as context:
                    workflow_regression.run_workflow_regression(
                        working_directory=Path(temporary_directory)
                    )

        self.assertEqual(
            context.exception.phase_name,
            workflow_regression.APP_RUNTIME_PHASE,
        )

    def test_run_workflow_regression_reports_wiki_build_phase(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with (
                mock.patch.object(
                    workflow_regression,
                    "run_ingest",
                    return_value=2,
                ),
                mock.patch.object(
                    workflow_regression,
                    "build_wiki",
                    side_effect=RuntimeError("wiki broke"),
                ),
            ):
                with self.assertRaises(workflow_regression.WorkflowPhaseError) as context:
                    workflow_regression.run_workflow_regression(
                        working_directory=Path(temporary_directory)
                    )

        self.assertEqual(
            context.exception.phase_name,
            workflow_regression.WIKI_BUILD_PHASE,
        )

    def test_run_workflow_regression_reports_evaluation_phase(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with (
                mock.patch.object(
                    workflow_regression,
                    "run_ingest",
                    return_value=2,
                ),
                mock.patch.object(
                    workflow_regression,
                    "run_wiki_build",
                    return_value=5,
                ),
                mock.patch.object(
                    workflow_regression.harness,
                    "run_eval",
                    side_effect=RuntimeError("eval broke"),
                ),
            ):
                with self.assertRaises(workflow_regression.WorkflowPhaseError) as context:
                    workflow_regression.run_workflow_regression(
                        working_directory=Path(temporary_directory)
                    )

        self.assertEqual(
            context.exception.phase_name,
            workflow_regression.EVALUATION_PHASE,
        )


if __name__ == "__main__":
    unittest.main()
