---
id: TASK-1.4
title: Document and validate the admin rebuild-review-publish workflow
status: Done
assignee: []
created_date: '2026-05-07 17:46'
labels:
  - wiki
  - docs
  - evaluation
milestone: StudyGraph Wiki Expansion
dependencies: []
documentation:
  - README.md
  - DEPLOYMENT.md
  - plan/requirements.md
  - >-
    backlog/docs/planning/studygraph-wiki-expansion-plan/doc-1 -
    StudyGraph-Wiki-Expansion-Plan.md
modified_files:
  - README.md
  - DEPLOYMENT.md
  - src/eval/harness.py
  - data/eval_cases.example.json
  - tests/test_eval_harness.py
parent_task_id: TASK-1
priority: medium
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Finish the operator-facing workflow required to keep the hosted corpus current after upload PRs merge. The repo should clearly document how to rebuild embeddings and wiki artifacts, review generated reports, and publish updated data without breaking the existing deployment model.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Re-read the existing README, deployment guide, upload flow, and evaluation harness to identify outdated operator instructions.
2. Update the docs to describe the real rebuild-review-publish loop for both Chroma and wiki artifacts, including when upload PRs are merged, when generated artifacts are reviewed, and what gets committed.
3. Replace the stale domain-specific evaluation fixture set with StudyGraph-oriented smoke scenarios that exercise grounded explanation and practice-question workflows, then add a focused regression test around the harness contract.
4. Re-run the relevant unit tests, record the final summary, and close the task without starting follow-up work.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Execution started after TASK-1.3 completion. Current docs still describe the old `data/psets/` ingest path and the current evaluation harness still targets Minecraft, so this task will close those operator-facing gaps with minimal, targeted edits.

Completed with targeted documentation and harness updates:
- `README.md` and `DEPLOYMENT.md` now describe the real operator loop after upload PR merge: verify structured corpus placement, run `uv run ingest`, run `uv run build-wiki`, review `data/wiki_report.md`, then commit refreshed `data/chroma_db/`, `data/wiki.sqlite3`, and `data/wiki_report.md`.
- `src/eval/harness.py` now uses StudyGraph-oriented smoke cases, supports local override cases from `data/eval_cases.json`, falls back to `data/eval_cases.example.json`, and records structured retrieval counts for chunks, wiki pages, and related topics.
- `tests/test_eval_harness.py` covers example-case loading, wiki-aware judge context assembly, and regression protection for evaluation output fields.
- Validation run:
  - `python3 -m unittest tests.test_eval_harness`
  - `python3 -m unittest tests.test_runtime tests.test_corpus tests.test_uploads tests.test_wiki_build`
  - `python3 -m compileall src/eval/harness.py tests/test_eval_harness.py`
<!-- SECTION:NOTES:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 README and deployment/admin docs describe the rebuild-review-publish workflow for both Chroma and wiki artifacts.
- [x] #2 Evaluation or smoke-test coverage exists for the main wiki-backed study workflows, including grounded explanations and practice-question generation.
- [x] #3 The workflow preserves the existing GitHub PR upload model and clarifies when generated artifacts should be committed or refreshed.
- [x] #4 A future operator can follow the documented steps without needing unstated knowledge from this planning conversation.
<!-- AC:END -->
