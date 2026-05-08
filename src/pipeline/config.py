import os
from pathlib import Path
from typing import Callable, TypeVar

try:
    import tomllib
except Exception:
    tomllib = None

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv() -> bool:
        return False

load_dotenv()

ValueType = TypeVar("ValueType")
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LOCAL_STREAMLIT_SECRETS_PATH = REPOSITORY_ROOT / ".streamlit" / "secrets.toml"


def _read_local_streamlit_secret(secret_name: str) -> str | None:
    """Read a value from local `.streamlit/secrets.toml` for CLI workflows."""
    if tomllib is None:
        return None

    if not LOCAL_STREAMLIT_SECRETS_PATH.exists():
        return None

    try:
        with LOCAL_STREAMLIT_SECRETS_PATH.open("rb") as secrets_file:
            secrets_data = tomllib.load(secrets_file)
    except Exception:
        return None

    secret_value = secrets_data.get(secret_name)
    if secret_value is None:
        return None

    return str(secret_value)


def _read_streamlit_secret(secret_name: str) -> str | None:
    """Read a value from Streamlit secrets when running in hosted mode."""
    try:
        import streamlit as streamlit_module
    except Exception:
        return None

    try:
        secret_value = streamlit_module.secrets.get(secret_name)
    except Exception:
        return None

    if secret_value is None:
        return None

    return str(secret_value)


def _read_setting(
    setting_name: str,
    default_value: ValueType | None = None,
    caster: Callable[[str], ValueType] | None = None,
) -> ValueType | str | None:
    """Read settings from env, local secrets, hosted secrets, then defaults."""
    raw_value = os.getenv(setting_name)
    if raw_value is None:
        raw_value = _read_local_streamlit_secret(setting_name)
    if raw_value is None:
        raw_value = _read_streamlit_secret(setting_name)

    if raw_value is None:
        return default_value

    if caster is None:
        return raw_value

    return caster(raw_value)


DATA_DIR = _read_setting("DATA_DIR", "./data")

OPENAI_API_KEY = _read_setting("OPENAI_API_KEY")
OPENAI_BASE_URL = _read_setting("OPENAI_BASE_URL")
CHAT_MODEL = _read_setting("CHAT_MODEL")
EMBEDDING_MODEL = _read_setting("EMBEDDING_MODEL")
EMBEDDING_BATCH_SIZE = _read_setting("EMBEDDING_BATCH_SIZE", 32, int)
CHROMA_DB_PATH = _read_setting(
    "CHROMA_DB_PATH",
    os.path.join(DATA_DIR, "chroma_db"),
)
CHROMA_COLLECTION_NAME = _read_setting("CHROMA_COLLECTION_NAME", "pset_problems")
WIKI_DB_PATH = _read_setting("WIKI_DB_PATH", os.path.join(DATA_DIR, "wiki.sqlite3"))
WIKI_REPORT_PATH = _read_setting(
    "WIKI_REPORT_PATH",
    os.path.join(DATA_DIR, "wiki_report.md"),
)
EMBEDDING_DOC_PREFIX = _read_setting("EMBEDDING_DOC_PREFIX", "")
EMBEDDING_QUERY_PREFIX = _read_setting("EMBEDDING_QUERY_PREFIX", "")
RETRIEVAL_TOP_K = _read_setting("RETRIEVAL_TOP_K", 20, int)
RERANK_TOP_K = _read_setting("RERANK_TOP_K", 5, int)
WIKI_TOP_K = _read_setting("WIKI_TOP_K", 5, int)
RERANK_MODEL = _read_setting("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
USER_AGENT = _read_setting("USER_AGENT", "JenRAG/1.0")
GITHUB_API_BASE_URL = _read_setting("GITHUB_API_BASE_URL", "https://api.github.com")
GITHUB_REPOSITORY = _read_setting("GITHUB_REPOSITORY")
GITHUB_BASE_BRANCH = _read_setting("GITHUB_BASE_BRANCH", "main")
GITHUB_UPLOAD_TOKEN = _read_setting("GITHUB_UPLOAD_TOKEN")
