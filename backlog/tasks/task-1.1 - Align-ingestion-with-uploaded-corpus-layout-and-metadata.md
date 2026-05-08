---
id: TASK-1.1
title: Align ingestion with uploaded corpus layout and metadata
status: Done
assignee: []
created_date: '2026-05-07 17:45'
updated_date: '2026-05-07 18:05'
labels:
  - wiki
  - ingestion
  - studygraph
milestone: StudyGraph Wiki Expansion
dependencies: []
documentation:
  - README.md
  - plan/requirements.md
  - >-
    backlog/docs/planning/studygraph-wiki-expansion-plan/doc-1 -
    StudyGraph-Wiki-Expansion-Plan.md
modified_files:
  - src/ingest/ingest.py
  - src/pipeline/__init__.py
  - src/pipeline/chunker.py
  - src/pipeline/corpus.py
  - tests/test_corpus.py
parent_task_id: TASK-1
priority: high
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Bring ingestion in line with the file organization produced by the current upload flow so the shared corpus can support both chunk retrieval and later wiki generation. Today uploads are written into structured LaTeX/PDF directories, while ingestion still assumes a flatter input shape and no wiki-oriented metadata pipeline.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Ingestion discovers uploaded corpus files from the structured data layout used by the current upload flow, including recursive traversal where needed.
- [x] #2 Course, assignment, and document metadata needed for downstream retrieval and wiki grouping are preserved in processed records.
- [x] #3 The ingestion path supports both LaTeX-derived text inputs and PDF-backed content without regressing current Chroma indexing behavior.
- [x] #4 Automated tests cover representative corpus fixtures and protect the current upload-to-ingest contract.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented structured corpus discovery for data/latex and data/pdf, preserved upload metadata for downstream retrieval, and added focused ingestion-alignment tests. Verification is in progress.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Aligned ingestion with the structured upload corpus layout by adding recursive discovery across data/latex and data/pdf, preserving course and assignment metadata through chunk creation, preferring LaTeX over duplicate PDF variants, and adding focused regression tests for upload-to-ingest compatibility.
<!-- SECTION:FINAL_SUMMARY:END -->
