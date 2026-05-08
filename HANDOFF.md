# Handoff Summary

## Current Status

Incremental upload, conversion, and embedding workflow is now implemented.

- Raw upload routing now distinguishes matched vs unmatched `.tex` / `.pdf`
- Canonical Markdown remains `data/md/...`
- Embedding now supports full rebuild, missing-only, and targeted refresh
- Raw-source conversion commands now exist for missing-only and targeted runs

## Completed This Session

- Added matched vs unmatched raw upload routing for GitHub-backed uploads.
- Added `embed-all`, `embed-missing`, and `embed-files` commands.
- Added `convert-missing` and `convert-files` commands with `--source-type all|tex|pdf`.
- Added OpenAI-compatible conversion service for `.tex` and extracted `.pdf` text.
- Updated `README.md` to document the new workflow.

## Files Changed

| File | Purpose |
|---|---|
| `src/app/uploads.py` | Added canonical Markdown path helper and matched/unmatched raw upload path routing. |
| `src/app/main.py` | Resolved upload target paths against base-branch Markdown presence and updated upload UI copy. |
| `src/pipeline/corpus.py` | Added requested-Markdown path loading for targeted embedding. |
| `src/pipeline/vectorstore.py` | Added collection reset, embedded source-path lookup, and delete-by-source-path helpers. |
| `src/pipeline/config.py` | Added conversion config values. |
| `src/pipeline/conversion.py` | Added OpenAI-compatible raw-source to Markdown conversion service. |
| `src/ingest/ingest.py` | Converted old ingest entrypoint into backward-compatible full rebuild alias. |
| `src/ingest/embed.py` | Added full rebuild, missing-only, and targeted embedding commands. |
| `src/ingest/convert.py` | Added missing-only and targeted raw-source conversion commands. |
| `pyproject.toml` | Registered new CLI scripts and `pypdf` dependency. |
| `tests/test_uploads.py` | Added matched/unmatched upload routing coverage. |
| `tests/test_embed_commands.py` | Added embed helper coverage. |
| `tests/test_convert_commands.py` | Added conversion candidate and path-mapping coverage. |
| `README.md` | Updated operator workflow and command documentation. |
| `HANDOFF.md` | Replaced stale summary with current session state. |

## Commands Run

```bash
python3 -m unittest tests.test_uploads tests.test_embed_commands tests.test_convert_commands
python3 -m compileall src tests
python3 -m unittest tests.test_corpus tests.test_runtime tests.test_uploads tests.test_embed_commands tests.test_convert_commands
python3 -m compileall src tests
git -C /Users/enzeeo/bluescreen/JenRAG diff -- src/app/uploads.py src/app/main.py src/pipeline/corpus.py src/pipeline/vectorstore.py src/ingest/ingest.py src/ingest/embed.py src/ingest/convert.py src/pipeline/conversion.py pyproject.toml tests/test_uploads.py tests/test_embed_commands.py tests/test_convert_commands.py
```

## Tests and Checks

- `python3 -m unittest tests.test_uploads tests.test_embed_commands tests.test_convert_commands`: passed
- `python3 -m unittest tests.test_corpus tests.test_runtime tests.test_uploads tests.test_embed_commands tests.test_convert_commands`: passed
- `python3 -m compileall src tests`: passed

## Important Decisions

- Upload routing decision happens at upload time, not after PR merge.
- Same-stem Markdown presence on `GITHUB_BASE_BRANCH` decides whether raw uploads go to matched or unmatched folders.
- `uv run ingest` remains available as the full rebuild alias for backward compatibility.
- `embed-missing` treats existing Chroma `source_path` metadata as the embedded-state marker.
- Raw conversion scans both matched and unmatched raw trees and prefers `.tex` over `.pdf` when both map to the same missing Markdown target.

## Known Issues

- PDF conversion depends on `pypdf` text extraction quality. Image-only or poorly encoded PDFs may still need manual cleanup after conversion.
- Conversion commands were verified through path-selection tests, not live API conversion calls.

## Next Recommended Steps

1. Run a live smoke test with a real `.tex` upload, a real unmatched `.pdf` upload, `uv run convert-missing`, `uv run ingest`, and `uv run build-wiki`.
2. If conversion quality is noisy on real PDFs, add review heuristics or chunked conversion later.
