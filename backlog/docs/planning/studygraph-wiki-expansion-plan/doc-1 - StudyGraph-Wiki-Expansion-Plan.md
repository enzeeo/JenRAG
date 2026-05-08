---
id: doc-1
title: StudyGraph Wiki Expansion Plan
type: specification
created_date: '2026-05-07 17:45'
tags:
  - planning
  - wiki
  - studygraph
  - rag
---
# StudyGraph Wiki Expansion Plan

## Summary

Plan from actual repo state, not the aspirational claims in `plan/requirements.md`.

Current repo already has:
- Streamlit chat UI
- ChromaDB retrieval
- optional reranking
- GitHub PR upload flow
- ingestion and evaluation scaffolding

Current repo does **not** yet have:
- `build-wiki` command
- SQLite wiki build artifacts
- runtime wiki retrieval
- wiki debug views in the chat flow
- generated `data/wiki_report.md`

The next implementation sequence should add the wiki/study-graph capability in four phases while preserving existing RAG and upload behavior.

## Key Changes

### 1. Corpus normalization and ingestion alignment
- Make the ingestion pipeline consume the same file layout that the upload flow writes today.
- Support recursive ingestion for organized LaTeX and PDF content instead of assuming a flat `data/psets/` style input root.
- Preserve course and assignment metadata so downstream retrieval and wiki generation can group content correctly.
- Keep ChromaDB as the chunk index for semantic retrieval.

### 2. Wiki build pipeline and prompt/spec cleanup
- Add a `build-wiki` workflow that reads processed corpus content and emits SQLite-backed wiki artifacts plus a review report.
- Replace the current course-specific `plan/AGENT.md` reference with a reusable course-agnostic wiki generation spec that still enforces source citation and contradiction handling.
- Generate structured wiki pages, page-to-source mappings, and topic links suitable for runtime lookup.

### 3. Runtime wiki retrieval and response composition
- Extend retrieval output so chat can show source chunks, matched wiki pages, and related topics together.
- Update answer generation so the model can use both chunk evidence and wiki summaries while still preferring course-grounded material over generic prior knowledge.
- Add debug UI in Streamlit for wiki matches and related-topic navigation alongside existing retrieved chunk inspection.

### 4. Admin workflow, evaluation, and docs
- Define the operator loop after upload PRs merge: pull content, run ingestion, rebuild embeddings, rebuild wiki, review report, publish generated artifacts.
- Update README/deployment/admin docs so the hosted app and local maintenance flow describe both retrieval and wiki artifacts.
- Add targeted evaluation and smoke-test coverage for wiki-backed answers, practice-question generation, and corpus rebuild regressions.

## Public Interfaces / Artifacts
- New CLI entrypoint: `build-wiki`
- New generated artifact set under `data/`: SQLite wiki database and markdown review report
- Retrieval result contract expanded to include wiki-page hits and related topics in addition to chunk hits
- Wiki generation prompt/spec becomes a reusable course-agnostic reference instead of the current options-volatility example

## Test Plan
- Upload and ingestion fixtures cover LaTeX/PDF file placement, metadata preservation, and recursive corpus discovery.
- Wiki build tests validate SQLite artifact creation, citation/source mappings, and report generation.
- Runtime tests validate combined chunk + wiki retrieval and prompt assembly.
- Streamlit-level tests or smoke checks validate debug panels for chunks, wiki pages, and related topics.
- Regression checks preserve current upload PR behavior and existing chunk retrieval flow.

## Assumptions
- The requirements document's statements that wiki build pieces already exist are treated as target-state requirements, not current implementation truth.
- Milestone one should include both the wiki build pipeline and the course-agnostic prompt/spec rewrite.
- Existing Chroma retrieval remains the primary evidence store; the wiki layer is a generated sidecar, not a replacement.
- Generated wiki artifacts can be committed and reviewed by the operator as part of the existing admin workflow.
