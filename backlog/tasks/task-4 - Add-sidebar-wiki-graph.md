---
id: TASK-4
title: Add sidebar wiki graph
status: Done
assignee: []
created_date: '2026-05-08 02:39'
updated_date: '2026-05-08 02:44'
labels: []
dependencies: []
modified_files:
  - src/app/main.py
  - src/wiki/query.py
  - tests/test_runtime.py
  - tests/test_wiki_query.py
  - pyproject.toml
priority: high
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a local interactive wiki-link graph to the Streamlit sidebar, driven by the latest retrieval result. Include empty-state handling, a wiki query neighborhood helper, and targeted runtime/query tests.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Sidebar shows a dedicated wiki graph panel under the wiki sidecar caption.
- [x] #2 Panel shows empty/unavailable states when there is no graph payload or wiki DB.
- [x] #3 Retrieval-driven matched wiki pages plus direct related topics render as a local graph neighborhood.
- [x] #4 Runtime tests and wiki query tests cover the new behavior.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented retrieval-driven sidebar wiki graph panel, local wiki graph neighborhood query helper, and targeted runtime/query tests. Manual Streamlit drag/pan smoke not run in this session.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the sidebar wiki graph feature. Added retrieval-driven sidebar graph state/rendering, local wiki graph neighborhood loading, and targeted runtime/query tests. Verified with: python3 -m unittest tests.test_runtime tests.test_wiki_query. Manual Streamlit drag/pan/zoom/click smoke still not run in this session.
<!-- SECTION:FINAL_SUMMARY:END -->
