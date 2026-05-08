---
id: TASK-3
title: Add full workflow regression test
status: Done
assignee: []
created_date: '2026-05-07 19:30'
labels:
  - testing
  - workflow
  - regression
milestone: StudyGraph Wiki Expansion
dependencies: []
documentation:
  - README.md
  - pyproject.toml
modified_files:
  - README.md
  - pyproject.toml
  - src/workflow_regression.py
  - tests/test_workflow_regression.py
  - tests/fixtures/workflow/data/eval_cases.example.json
  - tests/fixtures/workflow/data/md/cmsc_27100/cmsc_27100_fall_2025_notes_ng.md
  - tests/fixtures/workflow/data/md/cmsc_27100/cmsc_27100_fall_2025_pset1_ng.md
parent_task_id: TASK-1
priority: medium
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add one offline, fixture-based regression target that proves JenRAG still works end to end after changes. The target should validate app import/bootstrap, fixture-driven ingest, wiki build, and StudyGraph smoke evaluation without depending on hosted Streamlit, GitHub, or external model APIs.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inspect the existing runtime, ingest, wiki, and evaluation seams so the regression target can reuse real pipeline code instead of duplicating it.
2. Add a new top-level command that copies a small fixture corpus into a temp workspace, builds Chroma and wiki artifacts locally, and runs a deterministic evaluation smoke pass with clear phase-level failures.
3. Add focused tests that prove the orchestration succeeds on fixtures and reports distinct failing phases for app/runtime, wiki build, and evaluation regressions.
4. Document the new single-command regression check in the README and record the completed task.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Completed with one repo-level regression target:
- Added `uv run test-workflow` via `src/workflow_regression.py`.
- The harness copies a small fixture corpus into a temp data dir, imports the Streamlit app with bootstrap disabled, rebuilds Chroma with deterministic local embeddings, rebuilds the wiki SQLite/report artifacts, and runs `evaluate`-style smoke coverage with deterministic local generator/judge stubs.
- Each major phase fails as `app/runtime`, `ingest`, `wiki build`, or `evaluation` so contributors can see which layer broke.
- Added `tests/test_workflow_regression.py` plus fixture corpus/eval cases to keep the target offline and deterministic.
- Validation run:
  - `python3 -m unittest tests.test_workflow_regression`
  - `uv run test-workflow`
<!-- SECTION:NOTES:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 One top-level local command runs app/runtime smoke, fixture-based ingest, wiki build, and evaluation smoke in sequence.
- [x] #2 The regression target does not depend on hosted secrets, live GitHub, or external model APIs.
- [x] #3 Broken app import, broken wiki build, and broken evaluation each fail with a distinct named phase.
- [x] #4 README documents when contributors should run the regression command locally.
<!-- AC:END -->
