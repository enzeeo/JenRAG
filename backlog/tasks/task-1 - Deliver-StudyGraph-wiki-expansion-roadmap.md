---
id: TASK-1
title: Deliver StudyGraph wiki expansion roadmap
status: Done
assignee: []
created_date: '2026-05-07 17:45'
updated_date: '2026-05-07 18:06'
labels:
  - planning
  - wiki
  - studygraph
milestone: StudyGraph Wiki Expansion
dependencies: []
documentation:
  - README.md
  - plan/requirements.md
  - plan/AGENT.md
  - >-
    backlog/docs/planning/studygraph-wiki-expansion-plan/doc-1 -
    StudyGraph-Wiki-Expansion-Plan.md
modified_files:
  - src/app/main.py
  - src/app/uploads.py
  - src/ingest/ingest.py
  - src/pipeline/retriever.py
  - src/pipeline/generator.py
  - src/pipeline/corpus.py
  - src/pipeline/chunker.py
  - src/pipeline/embedder.py
  - src/pipeline/vectorstore.py
  - src/wiki/query.py
  - src/wiki/build.py
  - src/eval/harness.py
  - pyproject.toml
  - README.md
  - DEPLOYMENT.md
  - plan/AGENT.md
  - data/eval_cases.example.json
  - tests/test_corpus.py
  - tests/test_runtime.py
  - tests/test_wiki_build.py
  - tests/test_eval_harness.py
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Track the phased delivery of the new StudyGraph/wiki capability alongside the existing JenRAG retrieval and upload flow. This roadmap must start from actual repo state: Streamlit chat, Chroma retrieval, ingestion scaffolding, and GitHub PR uploads already exist, while SQLite wiki build, runtime wiki retrieval, and wiki review artifacts do not yet exist.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A shared plan exists in Backlog that distinguishes current repo behavior from target wiki capabilities.
- [x] #2 Follow-on implementation tasks exist for ingestion alignment, wiki build/prompting, runtime integration, and admin workflow/evaluation.
- [x] #3 Each follow-on task includes enough context and acceptance criteria for an independent agent to execute safely.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Align ingestion with the uploaded corpus layout and preserve metadata needed by both chunk retrieval and wiki generation.
2. Add a `build-wiki` pipeline plus a reusable course-agnostic wiki prompt/spec.
3. Integrate wiki retrieval, grounding, and debug surfaces into the Streamlit chat flow.
4. Document and validate the operator rebuild-review-publish workflow, including evaluation coverage.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Execution is complete.

Delivered across four subtasks:
- `TASK-1.1` aligned ingestion with the uploaded structured corpus layout, recursive discovery, and metadata preservation for downstream retrieval and wiki grouping.
- `TASK-1.2` added the `build-wiki` pipeline, SQLite wiki artifacts, markdown review report generation, and a reusable course-agnostic wiki prompt/spec.
- `TASK-1.3` integrated wiki retrieval into runtime grounding, expanded the retrieval contract, and exposed chunk/wiki/topic debugging in the Streamlit flow.
- `TASK-1.4` documented the rebuild-review-publish operator workflow and replaced the stale evaluation harness with StudyGraph-oriented smoke coverage.

The roadmap is now implemented rather than just planned, and the repo state matches the intended wiki expansion target.
<!-- SECTION:NOTES:END -->
