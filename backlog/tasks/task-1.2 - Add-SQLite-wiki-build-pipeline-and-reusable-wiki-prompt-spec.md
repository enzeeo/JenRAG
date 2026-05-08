---
id: TASK-1.2
title: Add SQLite wiki build pipeline and reusable wiki prompt spec
status: Done
assignee: []
created_date: '2026-05-07 17:45'
updated_date: '2026-05-07 18:09'
labels:
  - wiki
  - prompting
  - studygraph
milestone: StudyGraph Wiki Expansion
dependencies: []
documentation:
  - plan/requirements.md
  - plan/AGENT.md
  - >-
    backlog/docs/planning/studygraph-wiki-expansion-plan/doc-1 -
    StudyGraph-Wiki-Expansion-Plan.md
modified_files:
  - pyproject.toml
  - src/pipeline/config.py
  - src/pipeline/vectorstore.py
  - src/wiki/build.py
  - src/wiki/query.py
  - plan/AGENT.md
  - tests/test_wiki_build.py
parent_task_id: TASK-1
priority: high
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create the generated wiki sidecar that requirements call for. This includes a build workflow that turns the processed corpus into reviewable wiki artifacts and a course-agnostic prompt/spec that replaces the current options-volatility reference while retaining citation discipline and contradiction handling.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A documented `build-wiki` workflow produces a SQLite-backed wiki artifact and a markdown review report from the processed corpus.
- [x] #2 The wiki generation prompt/spec is rewritten as a reusable course-agnostic reference based on the citation and verification rules in `plan/AGENT.md`.
- [x] #3 Generated wiki artifacts include page content, source mappings, and topic relationships needed for runtime lookup.
- [x] #4 Automated tests or fixture-based checks validate artifact creation and basic source-link integrity.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Starting wiki build pipeline verification and prompt/spec rewrite. Existing code paths will be re-read and covered with artifact tests before closing this task.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed the SQLite wiki build slice by wiring the public `build-wiki` entrypoint to generated `data/wiki.sqlite3` and `data/wiki_report.md` artifacts, rewriting the wiki spec as a reusable course-agnostic StudyGraph reference, and adding a fixture-based regression test that validates page creation, source mappings, and related-topic links.
<!-- SECTION:FINAL_SUMMARY:END -->
