---
id: TASK-2
title: Add Markdown upload support and document manual source conversion
status: Done
assignee: []
created_date: '2026-05-07 18:20'
updated_date: '2026-05-07 18:20'
labels:
  - uploads
  - docs
  - ingest
milestone: ''
dependencies: []
documentation:
  - README.md
  - DEPLOYMENT.md
modified_files:
  - src/app/main.py
  - src/app/uploads.py
  - tests/test_uploads.py
  - README.md
priority: medium
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update the GitHub-backed upload workflow so Markdown is a first-class ingest-ready format. Preserve PDF and LaTeX uploads as raw source artifacts, but explicitly document that maintainers may need to convert those raw files into reviewed Markdown under `data/md` before running `uv run ingest`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extend upload validation and target-path generation so `.md` files are accepted and routed into `data/md/<course_folder>/...` while `.tex` and `.pdf` keep their existing raw-source destinations.
2. Update the Streamlit upload tab and pull request follow-up guidance so operators understand that Markdown is ingest-ready and PDF/LaTeX may require manual conversion before ingest.
3. Rewrite stale README sections so ingestion is documented as Markdown-first and raw source uploads are described as provenance artifacts rather than direct ingest input.
4. Add focused upload tests covering Markdown validation, Markdown path generation, and unsupported-extension rejection.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Completed with narrow upload, test, and documentation edits:

- `src/app/uploads.py` now accepts `.md` files, validates them as UTF-8 text with the same 2 MB limit as `.tex`, and routes them into `data/md/<course_folder>/...`. Existing `.tex` and `.pdf` storage paths remain unchanged.
- `src/app/main.py` now advertises `.md`, `.tex`, and `.pdf` uploads, explains that Markdown is ingest-ready, and adds explicit maintainer follow-up guidance for converting raw `.pdf` or `.tex` uploads into `data/md` before ingest when needed.
- `README.md` now matches actual ingest behavior: `uv run ingest` reads canonical corpus files from `data/md`, while `data/pdf` and `data/latex` are documented as raw artifact storage.
- `tests/test_uploads.py` now covers valid Markdown uploads, empty Markdown rejection, non-UTF-8 Markdown rejection, Markdown target paths, and unsupported file extensions.

Validation run:
- `python3 -m unittest tests.test_uploads`
<!-- SECTION:NOTES:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The upload flow accepts `.md`, `.tex`, and `.pdf`, and `.md` files route into `data/md/<course_folder>/...`.
- [x] #2 Upload UI and pull request guidance clarify that Markdown is ingest-ready while `.pdf` and `.tex` may require maintainer conversion before ingest.
- [x] #3 README documentation no longer claims that `uv run ingest` directly ingests `data/pdf` or `data/latex` as the primary corpus.
- [x] #4 Focused automated tests cover Markdown validation and Markdown path generation without regressing existing upload behavior.
<!-- AC:END -->
