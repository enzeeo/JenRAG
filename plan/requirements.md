# JenRAG StudyGraph Requirements

## 1. Project Overview

JenRAG is a study-oriented RAG application for shared course materials and practice content.

The current repository already has:

```text
Streamlit UI
GitHub-backed upload pull request flow
ChromaDB vector store
SQLite generated study-wiki sidecar
OpenAI-compatible chat and embedding endpoints
Optional BGE reranker
Offline Claude/Codex review workflow
```

The updated product goal is to make the current repo workflow match a StudyGraph-style system:

```text
Online Streamlit app for users
+ GitHub pull request upload flow
+ Local admin ingestion/rebuild workflow
+ Claude/Codex-assisted wiki and concept-link review
+ ChromaDB vector retrieval
+ SQLite study wiki with pages, aliases, sources, and links
+ Grounded study assistant for explanations and practice generation
```

The system should help students ask questions about course materials, generate similar practice problems, understand how ideas connect, and receive answers grounded in the uploaded lectures, homework, exams, notes, and worked solutions.

The user should not manually create every concept connection. The system should generate candidate wiki pages, aliases, source mappings, and links. The admin can use Claude/Codex to review and improve the generated wiki artifacts before committing them.

---

## 2. Current Repository Reality

This requirements document should reflect the current JenRAG setup, not a hypothetical new architecture.

The current repository uses:

```text
Frontend: Streamlit
Runtime vector database: ChromaDB
Generated wiki database: SQLite
Embedding endpoint: OpenAI-compatible HTTP endpoint
Chat endpoint: OpenAI-compatible HTTP endpoint
Optional reranker: BGE cross-encoder
Package manager: uv
Upload storage: GitHub pull requests
Admin review: offline Claude/Codex review of generated wiki artifacts
```

The current canonical local operator loop is:

```bash
uv sync
uv run ingest
uv run build-wiki
uv run streamlit run src/app/main.py
```

The hosted v1 app is intentionally simple:

```text
private Streamlit Community Cloud app
shared read-only study corpus
per-session private chat history
viewer allowlist through Streamlit sharing
uploads routed into GitHub pull requests
manual maintainer review and merge
manual re-ingest and wiki rebuild after merge
```

---

## 3. Core Product Goals

The app must allow approved users to:

1. Upload study files through Streamlit.
2. Submit uploads into GitHub pull requests rather than writing directly to runtime storage.
3. Ask questions grounded in the shared processed corpus.
4. Retrieve relevant source chunks from uploaded materials.
5. Map retrieved passages to generated wiki pages and related topics.
6. View retrieved chunks, matched wiki pages, and related topics when debugging.
7. Generate similar practice questions from prior homework, exams, notes, and solutions.
8. Receive explanations that use course-specific notation and source material.
9. Compare how the same concept appears across different documents.
10. Avoid relying only on generic model knowledge when course material exists.

The app must allow the admin/operator to:

1. Pull newly merged uploads from GitHub.
2. Run ingestion locally.
3. Rebuild ChromaDB embeddings.
4. Rebuild the SQLite study wiki.
5. Review `data/wiki_report.md` with Claude/Codex.
6. Improve or validate generated wiki artifacts when needed.
7. Commit and push updated generated artifacts.
8. Make the updated corpus available to the hosted Streamlit app.

---

## 4. End-to-End Workflow

### 4.1 User Online Workflow

The user workflow happens inside the hosted Streamlit app.

```text
User opens Streamlit
    ↓
User selects or enters required course metadata
    ↓
User uploads one supported file
    ↓
Streamlit validates file type, size, and metadata
    ↓
Streamlit creates an upload branch in GitHub
    ↓
Streamlit commits the uploaded file to the branch
    ↓
Streamlit opens a pull request against the base branch
    ↓
User sees that the upload was submitted for review
    ↓
Maintainer reviews and merges the pull request
    ↓
Admin later re-ingests and rebuilds the generated corpus
    ↓
File becomes searchable in the online app after processed artifacts are committed
```

The online upload flow is a review workflow, not direct runtime indexing.

A newly uploaded file is not searchable immediately. It becomes searchable only after:

```text
1. the upload pull request is reviewed and merged
2. the admin pulls the updated repo
3. the admin runs ingestion
4. the admin rebuilds the wiki
5. the admin commits updated ChromaDB and SQLite wiki artifacts
6. the hosted app receives the updated generated data
```

### 4.2 Admin Local Workflow

The admin workflow happens locally from the repository root.

```text
Admin pulls latest main branch
    ↓
Admin runs uv sync if dependencies changed
    ↓
Admin runs uv run ingest
    ↓
Ingestion loads source files, chunks them, embeds them, and stores them in ChromaDB
    ↓
Admin runs uv run build-wiki
    ↓
Wiki builder scans canonical source files and generated chunks
    ↓
Wiki builder creates or updates SQLite study-wiki records
    ↓
Wiki builder writes data/wiki_report.md
    ↓
Admin reviews data/wiki_report.md with Claude/Codex
    ↓
Admin uses AGENT.md rules to improve wiki pages, aliases, links, and explanations if needed
    ↓
Admin runs the Streamlit app locally for spot checks
    ↓
Admin commits generated artifacts
    ↓
Admin pushes updated data back to GitHub
```

Canonical command flow:

```bash
git pull origin main
uv sync
uv run ingest
uv run build-wiki
uv run streamlit run src/app/main.py
git add data/chroma_db data/wiki.sqlite3 data/wiki_report.md
git commit -m "Rebuild study corpus and wiki"
git push origin main
```

If more generated files are added later, the `git add` command should include those paths too.

---

## 5. Upload Requirements

### 5.1 Supported Upload Types

The current hosted upload flow must support:

```text
.tex
.pdf
```

Current limits:

```text
.tex: valid UTF-8 text, up to 2 MB
.pdf: valid PDF header, up to 20 MB
```

### 5.2 Upload Metadata

Each upload must include enough metadata to build a normalized repository path.

Required metadata:

```yaml
course_category: example cmsc, stat, econ
course_number: example 27100
term: example fall_2025
work_type: pset | hw | midterm | final | exam | quiz | notes | lec | custom
work_number: optional number or label
professor_or_author: optional but recommended
original_filename: uploaded filename
uploader_identifier: user/session/email if available
created_at: timestamp
```

The current repository path convention is:

```text
data/latex/<course_category>_<course_number>/<normalized_filename>.tex
data/pdf/<course_category>_<course_number>/<normalized_filename>.pdf
```

Examples:

```text
data/latex/cmsc_27100/cmsc_27100_fall_2025_pset1_ng.tex
data/pdf/cmsc_27200/cmsc_27200_win_2026_pset2_janos.pdf
data/latex/cmsc_27100/cmsc_27100_fall_2025_lec2_ng.tex
```

### 5.3 Upload Pull Request Behavior

The Streamlit upload tab must:

1. Accept one supported file at a time.
2. Validate file extension and size.
3. Validate required metadata.
4. Build a normalized repository path.
5. Create a new branch with an `upload/...` prefix.
6. Commit the file to the upload branch.
7. Open a pull request against `GITHUB_BASE_BRANCH`.
8. Tell the user that a maintainer must merge and rebuild before the file is searchable.

The upload flow must not directly mutate the hosted runtime corpus.

---

## 6. Input Data and Ingestion Requirements

### 6.1 Current Input Data Contract

The main ingestion flow currently expects LaTeX source files under:

```text
data/latex/<course_category>_<course_number>/
```

The current chunker is optimized for LaTeX problem-set style files and splits on patterns like:

```tex
\section*{Problem #N}
```

This is a good fit for:

```text
homework files
problem sets
exams
quizzes
worked solutions with clearly labeled problems
```

General notes and lecture files can still be ingested, but chunking quality depends on how structured those files are.

### 6.2 PDF Indexing Caveat

The hosted upload flow accepts PDF files for review, but PDF text extraction is not currently part of the v1 indexing workflow.

MVP requirement:

```text
PDF uploads may be stored through the GitHub PR flow, but they are not guaranteed to become searchable until a PDF text extraction step is implemented.
```

Near-term improvement requirement:

```text
Add PDF text extraction so data/pdf/... files can be included in uv run ingest.
```

### 6.3 Ingest Command

The ingestion command is:

```bash
uv run ingest
```

It must:

1. Load canonical source documents.
2. Split documents into chunks.
3. Attach document metadata to each chunk.
4. Embed chunks with the configured embedding endpoint.
5. Store embeddings in ChromaDB.
6. Preserve source identity so retrieved chunks can cite their original file.

### 6.4 Chunk Metadata

Each chunk should preserve:

```yaml
chunk_id: stable identifier
source_path: source file path
course_category: course category
course_number: course number
course_id: normalized course id
term: academic term if known
work_type: pset | hw | midterm | final | exam | quiz | notes | lec | custom
work_number: optional
problem_number: optional
section_title: optional
chunk_text: text content
created_at_or_indexed_at: timestamp if available
```

Chunking should prefer semantic boundaries:

```text
problem
solution
definition
theorem
proof
example
lecture section
formula block
explanation section
```

The system should avoid splitting in the middle of a problem or solution unless the section is too long for retrieval.

---

## 7. Generated Study Wiki Requirements

### 7.1 Current Wiki Storage

The current repo builds a generated study wiki as a SQLite sidecar:

```text
data/wiki.sqlite3
```

The builder also writes a human-readable report:

```text
data/wiki_report.md
```

The Streamlit app should be able to fall back to Chroma-only retrieval if `data/wiki.sqlite3` is missing, but the preferred workflow should use both ChromaDB and the generated wiki.

### 7.2 Build Command

The wiki build command is:

```bash
uv run build-wiki
```

It must:

1. Scan canonical source documents.
2. Create stable source document records.
3. Create stable chunk records.
4. Create deterministic candidate wiki pages.
5. Create aliases for concepts and pages.
6. Create links between pages and related topics.
7. Write `data/wiki.sqlite3`.
8. Write `data/wiki_report.md` for offline review.

### 7.3 Admin LLM Review Role

Claude/Codex is not part of the app runtime in this phase.

Claude/Codex should be used by the admin locally to:

```text
review data/wiki_report.md
find weak or missing concept links
suggest page improvements
identify orphan pages
identify contradictions
identify concepts that need pages
improve explanations in generated markdown-style wiki content if exported
help create better aliases and related-topic mappings
```

The admin LLM should follow the project-specific wiki rules from `AGENT.md`.

### 7.4 AGENT.md-Inspired Wiki Rules

The admin LLM context should include these rules:

```text
- Treat raw source documents as immutable.
- Do not modify files in raw or canonical source folders unless explicitly instructed.
- Maintain a structured, interlinked study wiki.
- Use wiki links in the form [[page-name]] when editing markdown wiki pages.
- Every factual claim should trace back to a source file.
- If two sources disagree, note the contradiction explicitly.
- If a claim has no source, mark it as needing verification.
- Keep explanations clear and plain-language first.
- Add mathematical detail, formulas, or graphing intuition when the course needs it.
- Update an index or table of contents when pages are added.
- Update a log when wiki files are manually changed.
- Find orphan pages and missing concept pages during audits.
- When uncertain about categorization, ask the admin instead of inventing structure.
```

The current AGENT.md is written for an economics options/volatility wiki. For this repo, it should be generalized so the same wiki-maintenance pattern can work for any course.

---

## 8. StudyGraph Concept-Linking Requirements

The generated wiki should approximate a StudyGraph even if the current storage is SQLite instead of a dedicated graph database.

The system should represent:

```text
source document → chunk
chunk → wiki page
wiki page → alias
wiki page → related page
wiki page → source evidence
query → retrieved chunk
retrieved chunk → matched wiki page
matched wiki page → related topics
```

The target conceptual model is:

```text
Concept A links to Concept B.
Both concepts link to source chunks.
Chunks have vectors.
The wiki/graph layer stores explicit relationships.
Vectors support semantic search.
```

### 8.1 Desired Relationship Types

When explicit relationship labels are added, they should use a fixed vocabulary:

```text
teaches
is_taught_in
tests
is_tested_by
solves
uses
uses_method
depends_on
prerequisite_for
related_to
contrasts_with
generalizes
special_case_of
demonstrates
causes_confusion_with
similar_to
```

Examples:

```text
Dynamic Programming depends_on Recursion
Dynamic Programming uses Recurrence Relations
Top-Down DP uses_method Memoization
Lecture 08 teaches Dynamic Programming
HW 05 Problem 2 tests Dynamic Programming
HW 05 Solution 2 solves HW 05 Problem 2
Dynamic Programming contrasts_with Divide and Conquer
```

### 8.2 Relationship Evidence Rules

Generated or reviewed relationships must follow these rules:

```text
- Do not invent unsupported relationships.
- Every important relationship should include source evidence.
- Prefer course-specific terminology over generic terminology.
- Preserve professor-specific notation when available.
- If uncertain, lower confidence or mark as needs review.
- If a relationship is implied but weak, use related_to instead of depends_on.
- If two concepts are often confused, use causes_confusion_with.
- If a homework solution uses a concept, connect the solution to that concept.
- If a homework problem tests a concept, connect the problem to that concept.
```

### 8.3 Future Graph Export

The current MVP can keep using SQLite wiki tables.

Future enhancement:

```text
Export explicit StudyGraph edges to JSON or a graph_edges table.
```

Example JSON shape:

```json
[
  {
    "edge_id": "edge_001",
    "from_node": "Dynamic Programming",
    "relationship_type": "depends_on",
    "to_node": "Recursion",
    "evidence_sources": [
      {
        "source_path": "data/latex/cmsc_27100/cmsc_27100_fall_2025_lec8.tex",
        "chunk_id": "chunk_120",
        "evidence_summary": "Lecture 8 introduces DP through recursive recurrence."
      }
    ],
    "confidence": 0.86,
    "status": "auto_generated"
  }
]
```

Default confidence behavior:

```text
confidence >= 0.80: use automatically
0.50 <= confidence < 0.80: use as weak context only
confidence < 0.50: do not use in retrieval
```

---

## 9. Retrieval Requirements

### 9.1 Query-Time Flow

When a user asks a question, the app should:

```text
1. Receive the user query in Streamlit.
2. Embed the query.
3. Retrieve relevant chunks from ChromaDB.
4. Optionally rerank retrieved chunks with the BGE cross-encoder.
5. Map retrieved chunks to wiki pages.
6. Fetch aliases, related wiki pages, and related topics from SQLite.
7. Build a context package.
8. Send the context package to the chat model.
9. Show the answer, source chunks, matched wiki pages, and related topics.
```

### 9.2 Target Query Classification

The current system may not fully classify intent yet, but the target behavior should classify user queries into:

```text
explain_concept
solve_problem
check_work
generate_practice
compare_concepts
summarize_material
quiz_mode
find_source
```

This classification should influence retrieval and generation.

Examples:

```text
explain_concept: retrieve notes, definitions, examples, related wiki pages
solve_problem: retrieve similar worked examples and relevant method pages
generate_practice: retrieve old problems plus solutions before generating
compare_concepts: retrieve multiple matched pages and contrastive examples
find_source: prioritize source document names and exact chunks
```

### 9.3 Context Package

The LLM should receive structured context similar to:

```yaml
user_question: original user question
intent: classified intent if available
retrieved_chunks:
  - source_path: data/latex/cmsc_27100/cmsc_27100_fall_2025_pset1.tex
    chunk_id: chunk_001
    excerpt: relevant source text
matched_wiki_pages:
  - title: dynamic-programming
    summary: page summary
    aliases:
      - DP
      - memoized recursion
related_topics:
  - recursion
  - recurrence-relations
  - memoization
source_notes:
  - source citation and any caveats
```

---

## 10. Answer Generation Requirements

The assistant must:

```text
- Ground answers in retrieved course materials.
- Use course-specific notation when available.
- Explain concept connections explicitly.
- List or cite the relevant source files/chunks.
- Show when the answer comes from matched wiki pages or related topics.
- Avoid unsupported claims.
- Say when the course context is insufficient.
- Avoid mixing unrelated courses by default.
- Avoid claiming an uploaded file is searchable before the admin rebuild occurs.
```

The assistant should be study-focused rather than pure fact lookup.

Good answer behaviors:

```text
- recap a topic from notes
- explain a concept using old solutions as grounding
- compare how a concept appears across documents
- generate similar practice questions from older assignments
- identify proof strategies that appear repeatedly
```

If stricter grounding is desired, retrieval settings and generation prompts should be tuned before changing the broader architecture.

---

## 11. Practice Problem Generation Requirements

The system must not generate practice problems from scratch when relevant course examples exist.

Required flow:

```text
1. Identify target topic, course, and difficulty.
2. Retrieve 3 to 5 similar problems, notes, or examples.
3. Retrieve corresponding worked solutions when available.
4. Retrieve matched wiki pages and related topics.
5. Generate a new problem with changed numbers, context, or framing.
6. Preserve the course's style and notation.
7. Provide hints.
8. Provide a full worked solution.
9. Label the tested concepts and methods.
10. List the original examples used as grounding.
```

Generated practice output should include:

```text
Problem
Relevant concepts
Difficulty estimate
Hint 1
Hint 2
Full solution
Connection to original course examples
Sources used
```

---

## 12. Admin Debug and Review Requirements

The Streamlit UI and generated reports should support admin/debug review.

The current UI should continue supporting:

```text
viewing retrieved chunks
viewing matched generated wiki pages
viewing related topics
viewing timing breakdowns
clearing the current session
```

The offline admin report should include or move toward including:

```text
source documents scanned
chunks created or updated
wiki pages created or updated
aliases created
links created
orphan pages
missing concept pages
low-confidence or suspicious links
retrieval test examples
warnings about unsupported PDFs or failed files
```

`data/wiki_report.md` is the main artifact that Claude/Codex should review before committing generated wiki artifacts.

---

## 13. Repository Layout Requirements

The current repository layout should remain recognizable:

```text
src/pipeline/   -- chunking, embeddings, retrieval, reranking, generation, config
src/wiki/       -- generated study-wiki schema, source scanning, page/link building
src/ingest/     -- ingestion pipeline and optional legacy scraper
src/app/        -- Streamlit chat UI
src/eval/       -- BEIR benchmark and judge-based evaluation harness
data/           -- input documents and generated artifacts
assets/         -- README images
```

Important generated/input paths:

```text
data/latex/                 -- canonical LaTeX input documents
data/pdf/                   -- uploaded PDF documents, not fully indexed in v1
data/chroma_db/             -- ChromaDB vector snapshot
data/wiki.sqlite3           -- generated SQLite study wiki
data/wiki_report.md         -- human-readable admin review report
.streamlit/config.toml       -- hosted Streamlit settings
.streamlit/secrets.toml      -- local/app secrets, not committed
.streamlit/secrets.toml.example -- secrets template
DEPLOYMENT.md                -- hosted deployment/admin workflow
README.md                    -- repo overview and setup
AGENT.md                     -- admin LLM wiki-maintenance context
```

---

## 14. Environment Requirements

Core environment variables:

```text
OPENAI_BASE_URL
OPENAI_API_KEY
CHAT_MODEL
EMBEDDING_MODEL
DATA_DIR
CHROMA_DB_PATH
CHROMA_COLLECTION_NAME
WIKI_DB_PATH
WIKI_REPORT_PATH
EVAL_API_KEY
```

Optional variables:

```text
EMBEDDING_BATCH_SIZE
EMBEDDING_DOC_PREFIX
EMBEDDING_QUERY_PREFIX
RETRIEVAL_TOP_K
RERANK_TOP_K
RERANK_MODEL
USER_AGENT
```

GitHub upload variables:

```text
GITHUB_REPOSITORY
GITHUB_UPLOAD_TOKEN
GITHUB_BASE_BRANCH
GITHUB_API_BASE_URL
```

The runtime contract should remain OpenAI-compatible HTTP, so `OPENAI_BASE_URL` may point to:

```text
OpenAI
LM Studio
Ollama
vLLM
another OpenAI-compatible provider
```

---

## 15. MVP Must Have

The MVP must have:

```text
- Streamlit UI
- Hosted private app option
- GitHub-backed upload pull request flow
- Maintainer review and merge workflow
- Local admin ingestion command: uv run ingest
- Local admin wiki build command: uv run build-wiki
- ChromaDB vector store
- SQLite generated study wiki
- data/wiki_report.md for Claude/Codex review
- Chat over processed source materials
- Source chunk display
- Matched wiki page display
- Related topic display
- Similar practice question generation grounded in retrieved materials
- Admin/operator documentation for pull, ingest, build, review, commit, push
```

---

## 16. MVP Can Skip

The MVP can skip:

```text
- Neo4j or a dedicated graph database
- Full automatic concept-edge approval workflow
- Persistent user accounts inside the app
- Persistent cross-session chat history
- Fine-tuned models
- Direct Claude/Codex SDK integration into runtime
- Fully automated post-upload indexing
- Advanced OCR
- Full PDF text extraction, temporarily
- Automatic grading
- Real-time collaborative wiki editing
```

---

## 17. Near-Term Improvements

After the current workflow is stable, prioritize:

1. Add PDF text extraction to ingestion.
2. Improve chunking for lecture notes and general notes, not only problem-set LaTeX.
3. Add explicit concept relationship labels in SQLite.
4. Add confidence scores for generated links.
5. Add a richer admin debug page in Streamlit.
6. Add a one-command admin rebuild script.
7. Add retrieval smoke tests after `uv run build-wiki`.
8. Add a generated graph export such as `data/graph_edges.json`.
9. Add course/professor scoping if multiple classes share the same deployment.
10. Add stricter generation prompts for source-grounded answers.

Recommended one-command admin script:

```bash
uv run rebuild-corpus
```

Target behavior:

```text
1. run ingest
2. run build-wiki
3. run retrieval smoke tests
4. write wiki report
5. print files that should be committed
```

---

## 18. Non-Goals

The app should not:

```text
- Treat upload as immediate indexing.
- Hide the fact that uploads require maintainer review and rebuild.
- Rely only on vector search when wiki/page/topic structure exists.
- Require students to manually define concept links.
- Treat generic internet knowledge as the source of truth.
- Mix unrelated courses by default.
- Generate practice questions without retrieving course examples first.
- Hide retrieved sources from the user.
- Modify raw or canonical source documents during wiki review.
```

---

## 19. Done When

The updated repo workflow is complete when:

```text
1. An approved user can upload a .tex or .pdf file in Streamlit.
2. The upload creates a GitHub pull request.
3. The maintainer can review and merge the upload.
4. The admin can pull the updated repo locally.
5. The admin can run uv run ingest successfully.
6. The admin can run uv run build-wiki successfully.
7. ChromaDB artifacts are updated.
8. data/wiki.sqlite3 is updated.
9. data/wiki_report.md is updated.
10. Claude/Codex can review the wiki report using AGENT.md context.
11. The admin can commit and push updated generated artifacts.
12. The hosted Streamlit app can answer questions using the updated corpus.
13. The app can show retrieved chunks, matched wiki pages, and related topics.
14. The app can generate similar practice questions grounded in retrieved examples.
15. The app clearly distinguishes uploaded-but-not-yet-indexed files from searchable processed files.
```

---

## 20. Recommended Admin Prompt

Use this prompt with Claude/Codex when reviewing the generated wiki artifacts:

```text
You are helping maintain the JenRAG generated study wiki.

Goal:
Review the generated study-wiki artifacts after I run uv run ingest and uv run build-wiki.

Repository context:
- Streamlit is the online UI.
- User uploads create GitHub pull requests.
- Merged uploads are not searchable until the admin re-ingests and rebuilds the corpus.
- ChromaDB stores vector embeddings.
- data/wiki.sqlite3 stores the generated study wiki.
- data/wiki_report.md is the main review artifact.
- AGENT.md defines the wiki-maintenance rules.

Your tasks:
1. Read data/wiki_report.md.
2. Identify weak, missing, duplicated, or suspicious wiki pages and links.
3. Check whether important concepts mentioned in sources have pages or aliases.
4. Find orphan pages or pages with poor related-topic coverage.
5. Flag contradictions between sources.
6. Flag claims that need source verification.
7. Suggest improvements using clear, course-specific language.
8. Do not modify raw source documents.
9. Preserve course notation and source-grounded explanations.
10. When uncertain, mark the issue as needs review instead of inventing facts.

Done when:
- You produce a concise review of problems found.
- You list concrete edits or follow-up tasks.
- Any proposed wiki changes cite the source file they came from.
```
