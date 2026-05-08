# Streamlit Community Cloud Deployment

This repository is configured for a private Streamlit Community Cloud deployment with:

- one shared, read-only study corpus
- per-session private chat history
- Streamlit-managed viewer allowlisting by email
- optional upload submissions routed into GitHub pull requests

## 1. Prepare the corpus locally

Before deploying, build both search artifacts on your machine.

1. Put your study files in `data/latex/<course>/` and `data/pdf/<course>/`
2. Set local environment variables in `.env`
3. Run:

```bash
uv sync
uv run ingest
uv run build-wiki
```

This creates:

- `data/chroma_db/` for chunk retrieval
- `data/wiki.sqlite3` for wiki retrieval
- `data/wiki_report.md` for operator review

For v1, commit the resulting read-only artifacts if they are small enough for the repository.

## 2. Push to GitHub

1. Keep the repository private if the study materials are private.
2. Push the repository to GitHub.
3. Confirm these files are present in the default branch:
   - `requirements.txt`
   - `.streamlit/config.toml`
   - `src/app/main.py`
   - `data/chroma_db/` after local ingest
   - `data/wiki.sqlite3` after local wiki build

## 3. Deploy on Streamlit Community Cloud

1. Open Streamlit Community Cloud.
2. Create a new app from this GitHub repository.
3. Use `src/app/main.py` as the entrypoint file.
4. Keep the app URL on `streamlit.app` for v1.

## 4. Add secrets

In the app settings, paste values based on `.streamlit/secrets.toml.example`.

Required:

- `OPENAI_API_KEY`
- `CHAT_MODEL`
- `EMBEDDING_MODEL`

Usually required for self-hosted or custom OpenAI-compatible providers:

- `OPENAI_BASE_URL`

Optional:

- `DATA_DIR`
- `CHROMA_DB_PATH`
- `CHROMA_COLLECTION_NAME`
- `WIKI_DB_PATH`
- `WIKI_REPORT_PATH`
- `WIKI_TOP_K`
- retrieval and reranker settings

Required for upload pull requests:

- `GITHUB_REPOSITORY`
- `GITHUB_UPLOAD_TOKEN`

Optional for upload pull requests:

- `GITHUB_BASE_BRANCH`
- `GITHUB_API_BASE_URL`

If you committed the index to `data/chroma_db/`, the default `CHROMA_DB_PATH` is usually correct.

The upload token should belong to a bot or service account with permission to:

- create branches
- commit files
- open pull requests

## 5. Lock access down

Use Streamlit Community Cloud sharing settings.

1. Make the app private.
2. Add only approved viewers by email.
3. Invite only UChicago email addresses.

This is the v1 access-control model. There is no custom login page in this version.

## 6. Admin workflow for updates

When the corpus changes:

1. Review and merge any upload pull requests
2. Confirm the merged files landed under `data/latex/` or `data/pdf/`
3. Re-run `uv run ingest` locally
4. Re-run `uv run build-wiki` locally
5. Review `data/wiki_report.md` for bad splits, contradictions, or weak topic pages
6. Commit the updated `data/chroma_db/`, `data/wiki.sqlite3`, and `data/wiki_report.md`
7. Push to GitHub
8. Let Streamlit redeploy or manually reboot the app

## 7. What not to do

- Do not treat GitHub as a live database.
- Do not rely on runtime-generated files persisting on Streamlit Community Cloud.
- Do not store API keys in tracked files.
- Do not assume a merged upload is searchable before manual `ingest` and `build-wiki`.

## 8. Verification checklist

- An invited viewer can open the app.
- An uninvited viewer cannot open the app.
- The app loads without a missing-config error.
- Retrieval works after redeploy or reboot.
- Wiki-backed retrieval works after redeploy or reboot.
- One browser session does not show another user’s chat history.
- A sample upload creates a pull request against `main`.
