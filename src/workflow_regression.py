from __future__ import annotations

import importlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import types
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from src.eval import harness
from src.ingest import embed as embed_module
from src.pipeline import retriever as retriever_module
from src.pipeline.vectorstore import init_collection
from src.wiki.build import build_wiki

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "workflow"
FIXTURE_DATA_ROOT = FIXTURE_ROOT / "data"
WORKFLOW_COLLECTION_NAME = "workflow_regression"
APP_RUNTIME_PHASE = "app/runtime"
INGEST_PHASE = "ingest"
WIKI_BUILD_PHASE = "wiki build"
EVALUATION_PHASE = "evaluation"
EMBEDDING_DIMENSIONS = 32
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class WorkflowArtifacts:
    working_directory: Path
    data_dir: Path
    chroma_db_path: Path
    wiki_db_path: Path
    wiki_report_path: Path
    eval_cases_path: Path
    eval_results_path: Path


@dataclass(frozen=True)
class WorkflowSummary:
    artifacts: WorkflowArtifacts
    chunk_count: int
    wiki_page_count: int
    evaluation_case_count: int


class WorkflowPhaseError(RuntimeError):
    """Raised when one workflow phase fails."""

    def __init__(self, phase_name: str, message: str):
        super().__init__(message)
        self.phase_name = phase_name


def _run_phase(phase_name: str, action):
    try:
        return action()
    except WorkflowPhaseError:
        raise
    except Exception as error:
        raise WorkflowPhaseError(phase_name, str(error)) from error


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def deterministic_embed_text(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    tokens = _tokenize(text)
    if not tokens:
        return vector

    for token in tokens:
        token_index = sum(ord(character) for character in token) % EMBEDDING_DIMENSIONS
        vector[token_index] += 1.0

    total_weight = float(len(tokens))
    return [value / total_weight for value in vector]


def deterministic_embed_chunks(chunk_texts: list[str]) -> list[list[float]]:
    return [deterministic_embed_text(chunk_text) for chunk_text in chunk_texts]


def deterministic_embed_query(query_text: str) -> list[float]:
    return deterministic_embed_text(query_text)


def prepare_fixture_data(working_directory: Path | None = None) -> WorkflowArtifacts:
    if working_directory is None:
        working_directory = Path(
            tempfile.mkdtemp(prefix="jenrag-workflow-regression-")
        )
    else:
        working_directory.mkdir(parents=True, exist_ok=True)

    data_dir = working_directory / "data"
    shutil.copytree(FIXTURE_DATA_ROOT, data_dir, dirs_exist_ok=True)

    return WorkflowArtifacts(
        working_directory=working_directory,
        data_dir=data_dir,
        chroma_db_path=data_dir / "chroma_db",
        wiki_db_path=data_dir / "wiki.sqlite3",
        wiki_report_path=data_dir / "wiki_report.md",
        eval_cases_path=data_dir / "eval_cases.example.json",
        eval_results_path=data_dir / "eval_results.json",
    )


def check_app_runtime() -> None:
    skip_env_var_name = "JENRAG_SKIP_STREAMLIT_BOOTSTRAP"
    previous_env_value = os.environ.get(skip_env_var_name)
    os.environ[skip_env_var_name] = "1"

    try:
        sys.modules.pop("src.app.main", None)
        streamlit_stub = types.ModuleType("streamlit")
        streamlit_stub.secrets = {}
        with mock.patch.dict(sys.modules, {"streamlit": streamlit_stub}):
            app_module = importlib.import_module("src.app.main")
    finally:
        if previous_env_value is None:
            os.environ.pop(skip_env_var_name, None)
        else:
            os.environ[skip_env_var_name] = previous_env_value

    if not hasattr(app_module, "render_application"):
        raise RuntimeError("Streamlit app import missing `render_application`.")
    app_module.validate_work_type_configuration()


def run_ingest(artifacts: WorkflowArtifacts) -> int:
    with (
        mock.patch.object(embed_module, "DATA_DIR", str(artifacts.data_dir)),
        mock.patch.object(embed_module, "CHROMA_DB_PATH", str(artifacts.chroma_db_path)),
        mock.patch.object(
            embed_module,
            "CHROMA_COLLECTION_NAME",
            WORKFLOW_COLLECTION_NAME,
        ),
        mock.patch.object(
            embed_module,
            "embed_chunks",
            side_effect=deterministic_embed_chunks,
        ),
    ):
        embed_module.main_embed_all()

    collection = init_collection(
        str(artifacts.chroma_db_path),
        WORKFLOW_COLLECTION_NAME,
    )
    chunk_count = int(collection.count())

    chroma_sqlite_path = artifacts.chroma_db_path / "chroma.sqlite3"
    if chunk_count <= 0:
        raise RuntimeError("ChromaDB collection is empty after ingest.")
    if not chroma_sqlite_path.is_file():
        raise RuntimeError(
            f"Expected ChromaDB artifact missing: {chroma_sqlite_path}"
        )

    return chunk_count


def run_wiki_build(artifacts: WorkflowArtifacts) -> int:
    pages, _, warnings = build_wiki(
        data_dir=str(artifacts.data_dir),
        database_path=str(artifacts.wiki_db_path),
        report_path=str(artifacts.wiki_report_path),
    )

    if warnings:
        raise RuntimeError("Wiki build emitted warnings for regression fixtures.")
    if not artifacts.wiki_db_path.is_file():
        raise RuntimeError(
            f"Expected wiki database missing: {artifacts.wiki_db_path}"
        )
    if not artifacts.wiki_report_path.is_file():
        raise RuntimeError(
            f"Expected wiki report missing: {artifacts.wiki_report_path}"
        )

    with sqlite3.connect(artifacts.wiki_db_path) as connection:
        page_count = int(
            connection.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        )

    if page_count != len(pages):
        raise RuntimeError(
            "Wiki database page count does not match in-memory build output."
        )

    return page_count


def fake_generate(query: str, retrieval_result) -> str:
    if not retrieval_result.chunk_hits:
        raise RuntimeError("No chunk hits retrieved during evaluation smoke test.")

    first_chunk = retrieval_result.chunk_hits[0]
    answer_lines = [
        f"Grounded answer for: {query}",
        f"Primary source: {first_chunk.title}",
        f"Primary section: {first_chunk.section or 'document body'}",
    ]

    if retrieval_result.wiki_page_hits:
        first_wiki_page = retrieval_result.wiki_page_hits[0]
        answer_lines.append(
            f"Wiki support: {first_wiki_page.title} ({first_wiki_page.slug})"
        )

    return "\n".join(answer_lines)


def fake_judge(query: str, context: str, answer: str, reference: str) -> dict:
    del query
    del reference

    if "No direct chunk evidence retrieved." in context:
        raise RuntimeError("Evaluation context missing chunk evidence.")
    if "No wiki page matches retrieved." in context:
        raise RuntimeError("Evaluation context missing wiki evidence.")
    if "Grounded answer for:" not in answer:
        raise RuntimeError("Smoke answer did not use fake generator contract.")

    return {
        "context_relevance": 5,
        "context_recall": 4,
        "faithfulness": 5,
        "answer_correctness": 4,
        "notes": "Fixture smoke judge passed.",
    }


def run_evaluation(artifacts: WorkflowArtifacts) -> int:
    evaluation_cases = harness.load_test_set(str(artifacts.eval_cases_path))

    def retrieve_for_workflow(query_text: str, use_reranker: bool = False):
        del use_reranker
        return retriever_module.retrieve(
            query_text,
            use_reranker=False,
            wiki_db_path=str(artifacts.wiki_db_path),
            wiki_top_k=3,
        )

    with (
        mock.patch.object(
            retriever_module,
            "CHROMA_DB_PATH",
            str(artifacts.chroma_db_path),
        ),
        mock.patch.object(
            retriever_module,
            "CHROMA_COLLECTION_NAME",
            WORKFLOW_COLLECTION_NAME,
        ),
        mock.patch.object(
            retriever_module,
            "embed_query",
            side_effect=deterministic_embed_query,
        ),
        mock.patch.object(harness, "retrieve", side_effect=retrieve_for_workflow),
        mock.patch.object(harness, "generate", side_effect=fake_generate),
        mock.patch.object(harness, "judge", side_effect=fake_judge),
    ):
        results = harness.run_eval(
            use_reranker=False,
            test_set=evaluation_cases,
            output_path=str(artifacts.eval_results_path),
        )

    if not artifacts.eval_results_path.is_file():
        raise RuntimeError(
            f"Expected evaluation results missing: {artifacts.eval_results_path}"
        )

    saved_results = json.loads(artifacts.eval_results_path.read_text(encoding="utf-8"))
    if len(saved_results) != len(evaluation_cases):
        raise RuntimeError("Evaluation results count does not match fixture cases.")

    if any(result["num_chunks"] <= 0 for result in results):
        raise RuntimeError("Evaluation smoke test found case with zero chunk hits.")
    if any(result["num_wiki_pages"] <= 0 for result in results):
        raise RuntimeError("Evaluation smoke test found case with zero wiki hits.")

    return len(results)


def run_workflow_regression(
    working_directory: Path | None = None,
) -> WorkflowSummary:
    artifacts = prepare_fixture_data(working_directory)

    _run_phase(APP_RUNTIME_PHASE, check_app_runtime)
    chunk_count = _run_phase(INGEST_PHASE, lambda: run_ingest(artifacts))
    wiki_page_count = _run_phase(WIKI_BUILD_PHASE, lambda: run_wiki_build(artifacts))
    evaluation_case_count = _run_phase(
        EVALUATION_PHASE,
        lambda: run_evaluation(artifacts),
    )

    return WorkflowSummary(
        artifacts=artifacts,
        chunk_count=chunk_count,
        wiki_page_count=wiki_page_count,
        evaluation_case_count=evaluation_case_count,
    )


def main() -> None:
    try:
        summary = run_workflow_regression()
    except WorkflowPhaseError as error:
        print(f"FAIL [{error.phase_name}] {error}")
        sys.exit(1)

    print(f"PASS [{APP_RUNTIME_PHASE}] Streamlit app import and guard path work.")
    print(
        f"PASS [{INGEST_PHASE}] Built {summary.chunk_count} chunks in "
        f"{summary.artifacts.chroma_db_path}."
    )
    print(
        f"PASS [{WIKI_BUILD_PHASE}] Built {summary.wiki_page_count} wiki pages in "
        f"{summary.artifacts.wiki_db_path}."
    )
    print(
        f"PASS [{EVALUATION_PHASE}] Ran {summary.evaluation_case_count} fixture cases. "
        f"Results: {summary.artifacts.eval_results_path}"
    )
    print(f"PASS [workflow] Temp artifacts: {summary.artifacts.working_directory}")


if __name__ == "__main__":
    main()
