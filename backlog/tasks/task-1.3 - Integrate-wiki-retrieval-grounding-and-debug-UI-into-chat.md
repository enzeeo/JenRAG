---
id: TASK-1.3
title: 'Integrate wiki retrieval, grounding, and debug UI into chat'
status: Done
assignee: []
created_date: '2026-05-07 17:45'
updated_date: '2026-05-07 18:15'
labels:
  - wiki
  - runtime
  - streamlit
milestone: StudyGraph Wiki Expansion
dependencies: []
documentation:
  - README.md
  - plan/requirements.md
  - >-
    backlog/docs/planning/studygraph-wiki-expansion-plan/doc-1 -
    StudyGraph-Wiki-Expansion-Plan.md
modified_files:
  - src/pipeline/retriever.py
  - src/pipeline/generator.py
  - src/pipeline/embedder.py
  - src/pipeline/vectorstore.py
  - src/app/main.py
  - tests/test_runtime.py
parent_task_id: TASK-1
priority: high
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend the current chat path so retrieval and answer generation can use both chunk evidence and generated wiki knowledge. The Streamlit app should expose wiki matches and related topics in the same debugging surface that currently shows retrieved chunks and timings.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Runtime retrieval returns both chunk matches and wiki-sidecar matches in a structured form the app and generator can consume.
- [x] #2 Answer generation prefers course-grounded chunk and wiki evidence over unsupported generic knowledge when relevant corpus material exists.
- [x] #3 The Streamlit chat UI displays matched wiki pages and related topics alongside existing retrieved chunk debugging information.
- [x] #4 Tests cover combined retrieval/generation behavior and prevent regressions in the current chat flow.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Inspect current retriever/generator/UI/test state and close any gaps required for combined chunk + wiki retrieval plus debug rendering.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Execution started in fresh session. Inspecting runtime retrieval, prompt grounding, debug UI, and coverage before targeted edits.

Closed the runtime task with targeted hardening and regression coverage. Added prompt-format helpers for wiki pages and related topics, kept optional reranker/OpenAI/Chroma imports lazy so retrieval and generation modules stay importable in test environments, and wrapped Streamlit bootstrap in a callable entrypoint with an environment guard so the debug renderer can be smoke-tested without launching the full app.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed the wiki runtime integration slice by confirming combined chunk plus wiki retrieval stays structured end-to-end, tightening prompt assembly so wiki pages and related topics are rendered explicitly for grounded answers, and adding runtime smoke coverage for the Streamlit debug surface. Supporting lazy imports in the embedder, retriever, generator, and vectorstore paths keep existing chat behavior intact while allowing isolated tests to run without optional runtime dependencies installed.
<!-- SECTION:FINAL_SUMMARY:END -->
