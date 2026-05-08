# JenRAG

JenRAG is a study-oriented RAG application for course materials and practice content.

You provide a document collection such as:

- old homework problems
- exam questions
- worked solutions
- lecture or reading notes
- topic summaries or study guides

The system then:

1. chunks the documents
2. embeds them
3. stores them in ChromaDB
4. retrieves relevant passages for a user query
5. optionally reranks them with a BGE cross-encoder
6. uses an LLM to answer, recap, summarize, or generate similar practice questions

## Current Status

The repo now includes the full StudyGraph wiki workflow:

- structured ingestion from `data/md/`
- Chroma-backed chunk retrieval
- generated SQLite wiki artifacts for topic lookup
- Streamlit chat debugging for chunk hits, wiki hits, and related topics
- GitHub pull request uploads for new Markdown and source files
- operator docs for rebuild, review, and publish steps

Typical use cases:

- recap a topic from your notes
- explain an idea using past solutions as grounding
- answer a question about prior homework or exams
- generate practice questions similar to older assignments
- compare how a concept appears across different documents

## Stack

- OpenAI-compatible embedding endpoint
- ChromaDB vector store
- optional BGE reranker
- OpenAI-compatible chat endpoint for generation
- Streamlit UI
- GitHub pull request flow for user uploads

The repository currently targets local study documents first. A legacy scraper is still included, but it is optional and not required for the main workflow.

## Setup

Requirements:

- Python 3.12+
- `uv` recommended

From the repository root:

```bash
uv sync
```

Create a `.env` file in the project root.

## Quick Start

For a full local rebuild from the current Markdown corpus:

```bash
uv run ingest
uv run build-wiki
uv run streamlit run src/app/main.py
```

That sequence rebuilds embeddings for all current Markdown files under
`data/md/`, rebuilds the wiki sidecar, and starts the chat UI.

For incremental updates after adding raw source files:

```bash
uv run convert-missing
uv run embed-missing
uv run build-wiki
```

That sequence converts missing raw source files into canonical Markdown, updates
only new embeddings, and rebuilds the wiki sidecar.

## Online Deployment

This repo now includes the files needed for a hosted Streamlit Community Cloud deployment:

- `requirements.txt` for Cloud dependency installation
- `.streamlit/config.toml` for hosted app settings
- `.streamlit/secrets.toml.example` as the secrets template
- `DEPLOYMENT.md` for the admin workflow

The intended v1 online setup is:

- private Streamlit Community Cloud app
- shared read-only study corpus
- per-session private chat history
- viewer allowlist managed by Streamlit by email
- upload submissions routed into GitHub pull requests

See [DEPLOYMENT.md](/Users/enzeeo/bluescreen/JenRAG/DEPLOYMENT.md) for the full deployment steps.

## Environment

Core variables:

| Variable | What it does |
| --- | --- |
| `OPENAI_API_KEY` | API key for the configured OpenAI-compatible API |
| `OPENAI_BASE_URL` | Base URL for your OpenAI-compatible API. Leave unset only if you want the provider default |
| `CHAT_MODEL` | Chat model used for answer generation |
| `EMBEDDING_MODEL` | Embedding model used for document and query embeddings |
| `CONVERSION_MODEL` | Chat model used to convert `.tex` and extracted `.pdf` text into Markdown |
| `DATA_DIR` | Root directory for generated and input data. Default: `./data` |
| `CHROMA_DB_PATH` | ChromaDB directory. Default: `./data/chroma_db` |
| `CHROMA_COLLECTION_NAME` | Collection name. Default in code: `pset_problems` |

Optional variables:

- `EMBEDDING_BATCH_SIZE`
- `EMBEDDING_DOC_PREFIX`
- `EMBEDDING_QUERY_PREFIX`
- `CONVERSION_MAX_TOKENS`
- `RETRIEVAL_TOP_K`
- `RERANK_TOP_K`
- `WIKI_DB_PATH`
- `WIKI_REPORT_PATH`
- `WIKI_TOP_K`
- `RERANK_MODEL`
- `USER_AGENT`

Evaluation-only variables:

- `EVAL_API_KEY`

Upload variables:

| Variable | What it does |
| --- | --- |
| `GITHUB_REPOSITORY` | Target GitHub repository in `owner/repo` format |
| `GITHUB_UPLOAD_TOKEN` | Bot token used to create upload branches, commits, and pull requests |
| `GITHUB_BASE_BRANCH` | Base branch for upload pull requests. Default: `main` |
| `GITHUB_API_BASE_URL` | GitHub API root. Default: `https://api.github.com` |

See [src/pipeline/config.py](/Users/enzeeo/bluescreen/JenRAG/src/pipeline/config.py) for the actual defaults.

For Streamlit Community Cloud, place the same values in app secrets using
[.streamlit/secrets.toml.example](/Users/enzeeo/bluescreen/JenRAG/.streamlit/secrets.toml.example)
as the template.

## GitHub-Backed Uploads

The Streamlit app includes an upload tab that lets approved users submit
study files for storage in the configured GitHub repository.

The upload flow:

1. accepts one `.md`, `.tex`, or `.pdf` file
2. validates the file type, size, and required course metadata
3. builds a normalized repository path
4. creates a new `upload/...` branch
5. commits the uploaded file to that branch
6. opens a pull request against `GITHUB_BASE_BRANCH`

Uploaded files are stored in these repository paths:

```text
data/md/<course_category>_<course_number>/<normalized_filename>.md
data/latex/<course_category>_<course_number>/<normalized_filename>.tex
data/pdf/<course_category>_<course_number>/<normalized_filename>.pdf
data/unmatched-latex/<course_category>_<course_number>/<normalized_filename>.tex
data/unmatched-pdf/<course_category>_<course_number>/<normalized_filename>.pdf
```

Routing rules:

- `.md` uploads always go to `data/md/...`
- `.tex` uploads go to `data/latex/...` when the canonical Markdown path already
  exists on `GITHUB_BASE_BRANCH`; otherwise they go to `data/unmatched-latex/...`
- `.pdf` uploads go to `data/pdf/...` when the canonical Markdown path already
  exists on `GITHUB_BASE_BRANCH`; otherwise they go to `data/unmatched-pdf/...`

Examples:

```text
data/md/cmsc_27200/cmsc_27200_win_2026_pset1_janos.md
data/latex/cmsc_27100/cmsc_27100_fall_2025_pset1_ng.tex
data/pdf/cmsc_27200/cmsc_27200_win_2026_pset2_janos.pdf
data/unmatched-latex/cmsc_27100/cmsc_27100_fall_2025_lec2_ng.tex
data/unmatched-pdf/cmsc_27200/cmsc_27200_win_2026_pset5_janos.pdf
```

This is a review workflow, not direct runtime storage. A maintainer still needs
to review and merge the pull request before the file exists on the main branch.
After merge:

1. `.md` uploads are ingest-ready and can go straight into the rebuild flow
2. matched `.pdf` and `.tex` uploads stay in `data/pdf/` or `data/latex/`
3. unmatched `.pdf` and `.tex` uploads stay in `data/unmatched-pdf/` or
   `data/unmatched-latex/`
4. raw uploads may need conversion into reviewed Markdown under `data/md/`
5. the file is not searchable until a maintainer rebuilds both search artifacts
   locally

1. `uv run convert-missing`
2. review generated Markdown under `data/md/`
3. `uv run ingest` for a full rebuild of all current Markdown files, or
   `uv run embed-missing` for new Markdown only
4. `uv run build-wiki`
5. review `data/wiki_report.md`
6. commit `data/chroma_db/`, `data/wiki.sqlite3`, and `data/wiki_report.md`

Current upload limits:

- `.md`: valid UTF-8 text, up to 2 MB
- `.tex`: valid UTF-8 text, up to 2 MB
- `.pdf`: valid PDF header, up to 20 MB

Supported work type tokens include `pset`, `hw`, `midterm`, `final`, `exam`,
`quiz`, `notes`, `lec`, and `custom`. Numbered values use the selected work type
plus the work number, such as `pset1`, `exam2`, or `lec2`.

## Input Data

The canonical ingestion flow reads Markdown from the structured corpus layout:

```text
data/md/<course_category>_<course_number>/**/*.md
```

Recursive discovery is enabled under that root, so course folders can contain
subdirectories.

The upload workflow may also store raw source artifacts under:

```text
data/latex/<course_category>_<course_number>/**/*.tex
data/pdf/<course_category>_<course_number>/**/*.pdf
data/unmatched-latex/<course_category>_<course_number>/**/*.tex
data/unmatched-pdf/<course_category>_<course_number>/**/*.pdf
```

Those raw files are kept for provenance and review, but they are not the
canonical ingest input. Maintainers may need to convert them into reviewed
Markdown files under `data/md/` before running an embedding command.

## Main Workflow

1. Add or merge ingest-ready study documents under `data/md/`
2. Convert missing raw source files if needed
3. Rebuild Chroma retrieval artifacts
4. Rebuild the wiki sidecar and review its report
5. Run the Streamlit app
6. Ask for summaries, explanations, or similar practice questions

### 1. Convert raw files when needed

```bash
uv run convert-missing
```

Optional filters:

```bash
uv run convert-missing --source-type tex
uv run convert-missing --source-type pdf
uv run convert-files --source-type all --path data/unmatched-latex/cmsc_27100/file.tex
```

This will:

- scan matched and unmatched raw source trees
- derive canonical Markdown targets under `data/md/`
- skip sources whose Markdown target already exists
- prefer `.tex` over `.pdf` when both map to the same missing Markdown file

### 2. Embed documents

Full rebuild:

```bash
uv run ingest
```

Incremental update for new Markdown only:

```bash
uv run embed-missing
```

Targeted refresh for selected Markdown files:

```bash
uv run embed-files --path data/md/cmsc_27200/cmsc_27200_win_2026_pset1_janos.md
```

Embedding commands:

- load Markdown files recursively from `data/md/`
- split them into chunks
- embed the chunks
- store them in ChromaDB

Mode summary:

- `uv run ingest` or `uv run embed-all`: clear collection, then rebuild all Markdown
- `uv run embed-missing`: add only Markdown files whose `source_path` is not yet in Chroma metadata
- `uv run embed-files`: delete old chunks for specific Markdown files, then re-embed only those files

### 3. Build wiki artifacts

```bash
uv run build-wiki
```

This writes:

- `data/wiki.sqlite3` for runtime wiki retrieval
- `data/wiki_report.md` for operator review before publishing artifacts

### 4. Run the chat UI

```bash
uv run streamlit run src/app/main.py
```

The UI supports:

- normal question answering over the indexed materials
- optional reranking
- viewing retrieved chunks
- timing breakdowns for retrieval and generation
- a clear-chat action for resetting the current session
- an upload tab that opens GitHub pull requests for new `.md`, `.tex`, and `.pdf` files

## What The Chatbot Is For

The intended assistant behavior is study-focused rather than pure fact lookup.

Examples:

- "Summarize divide and conquer from the course notes."
- "Explain how dynamic programming is used in these old solutions."
- "Give me a practice question similar to Problem #4 from the midterm."
- "What themes keep showing up in the graph theory homework?"
- "Recap the proof strategy used in these notes."

Depending on prompting and model behavior, the chatbot can:

- recap or summarize topics from the provided materials
- explain ideas grounded in your notes or prior solutions
- produce similar questions based on earlier problems
- combine retrieved material with the model's own background knowledge

If you want stricter grounding, the generation prompt and retrieval settings are the main places to tune.

## Evaluation

The repository includes two evaluation-related paths:

- `beir-ingest` and `beir-eval` for retrieval benchmarking on BEIR datasets
- `evaluate` for a judge-based StudyGraph smoke harness

Run them with:

```bash
uv run beir-ingest
uv run beir-eval
uv run beir-eval --use-reranker
uv run evaluate
uv run test-workflow
```

`uv run evaluate` now checks grounded study workflows rather than the old
domain-specific fixture set. Default cases cover:

- grounded explanations from retrieved evidence
- practice-question generation tied to retrieved assignments or notes
- cross-document synthesis with chunk and wiki evidence
- correct handling when the corpus does not fully answer a question

Override the bundled smoke cases by adding `data/eval_cases.json`. Use
`data/eval_cases.example.json` as the template shape.

## Full Workflow Regression

Run this before opening a PR when you touch app bootstrap, ingest, retrieval,
wiki build, or evaluation wiring:

```bash
uv run test-workflow
```

This command is offline and fixture-based. It:

- imports `src/app/main.py` with Streamlit bootstrap disabled
- rebuilds a temp Chroma snapshot from a small local Markdown corpus
- rebuilds temp wiki SQLite and report artifacts
- runs `evaluate`-style smoke cases against those temp artifacts

Failures are reported by phase: `app/runtime`, `ingest`, `wiki build`, or
`evaluation`.

## Optional Scraper

A scraper still exists at:

```text
src/ingest/scrape.py
```

It is a legacy utility from an earlier version of the project and is not necessary for the current study-documents workflow.

## Hosted v1 Behavior

The hosted v1 deployment is intentionally simple:

- one shared document corpus for all approved users
- separate in-memory chat sessions per user/browser session
- no custom login page
- no persistent cross-session chat history
- uploads create GitHub pull requests instead of writing directly to runtime disk
- merged uploads still require manual `ingest`, `build-wiki`, report review,
  and artifact commits before retrieval can use them

Access control is handled by Streamlit Community Cloud private-app sharing, not by application-level auth code.

## Repository Layout

- `src/pipeline/` — chunking, embeddings, retrieval, reranking, generation, config
- `src/ingest/` — ingestion pipeline and optional legacy scraper
- `src/app/` — Streamlit chat UI
- `src/eval/` — BEIR benchmarking and judge-based evaluation harness
- `src/wiki/` — generated wiki build and runtime lookup helpers
- `data/` — local input documents and generated artifacts
- `backlog/` — task records for the wiki expansion work and follow-on planning
- `HANDOFF.md` — short current-state summary for future agent sessions
- `DEPLOYMENT.md` — maintainer workflow for hosted operation
- `assets/` — README images

## Current Caveats

- The chunker is tuned for problem-set style LaTeX structure
- Wiki artifacts are generated sidecars and should be reviewed before commit
