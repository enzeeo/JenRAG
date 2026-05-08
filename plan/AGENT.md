# StudyGraph Wiki Spec

This file defines the target behavior for the generated StudyGraph wiki sidecar.

The wiki is course-agnostic. It should work for any study corpus built from
uploaded LaTeX or PDF materials such as homework, exams, lecture notes, or
topic summaries.

## Purpose

The wiki is a derived artifact, not a freeform notebook.

Its job is to:

1. organize the corpus into reviewable course, document, and section pages
2. preserve source mappings for every generated page
3. expose topic relationships that can help runtime retrieval
4. make contradictions and weak grounding visible to a maintainer

The wiki must stay grounded in the source corpus. It is allowed to compress or
rephrase the material, but it must not introduce unsupported claims.

## Artifact Model

The build pipeline produces:

- `data/wiki.sqlite3`
- `data/wiki_report.md`

The SQLite database is the runtime sidecar.

## Rebuild Workflow

After corpus updates land on the main branch:

1. run `uv run ingest` to rebuild chunk embeddings
2. run `uv run build-wiki` to regenerate wiki artifacts
3. review `data/wiki_report.md`
4. keep `data/wiki.sqlite3` and `data/wiki_report.md` in sync with the corpus

Expected page categories:

- `course`
- `document`
- `section`

Expected relationship categories include:

- course membership
- document-to-section links
- section ordering links
- related-topic links

## Grounding Rules

- Every generated page must map back to a real source path from the corpus.
- Summaries should be compressed from the underlying source text, not invented.
- If source text is weak, noisy, or obviously extracted from a low-quality PDF,
  prefer a shorter summary over a speculative one.
- If two sources appear to disagree, preserve both viewpoints in the review
  report or downstream prompts rather than silently resolving the conflict.
- If a claim cannot be supported by the source material, omit it or mark it as
  needing human review.

## Citation Rules

- Source identity must be preserved with `source_path` and `source_title`.
- Section-derived pages should preserve the originating section title when one
  exists.
- Generated explanations should be traceable to specific uploaded files.
- Runtime answer generation should cite the originating chunk or wiki page
  rather than presenting unsupported generic knowledge as fact.

## Review Rules

Maintainers should review `data/wiki_report.md` after each wiki rebuild.

Review should focus on:

1. incorrect course grouping
2. duplicated document or section pages
3. weak summaries caused by poor extraction quality
4. suspicious related-topic links
5. missing or misleading source mappings
6. contradictions that need explicit handling in prompts or answers

## Authoring Constraints

- Keep the spec course-agnostic.
- Prefer clear, plain language over subject-specific jargon.
- Do not assume economics, algorithms, or any single discipline.
- Do not require hand-written markdown wiki pages as the primary artifact.
- Treat the generated SQLite wiki as the source of runtime lookup truth.
