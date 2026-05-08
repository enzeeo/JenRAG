import os
from pathlib import Path
import re
import sys
import time

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    # Streamlit may execute this file with `src/app` as the import root.
    sys.path.insert(0, str(REPOSITORY_ROOT))

import streamlit as st
try:
    from streamlit_agraph import Config, Edge, Node, agraph
except ImportError:
    Config = None
    Edge = None
    Node = None
    agraph = None

from src.app.github_uploads import GitHubUploadClient, GitHubUploadError
from src.app.uploads import (
    PRESET_WORK_TYPES,
    UploadMetadata,
    UploadFormDefaults,
    UploadValidationError,
    ValidatedUploadedFile,
    build_filename_stem,
    build_target_path,
    build_upload_branch_name,
    derive_upload_form_defaults_from_file_name,
    normalize_upload_metadata,
    validate_uploaded_file,
)
from src.pipeline.retriever import retrieve
from src.pipeline.generator import generate
from src.pipeline.config import (
    CHAT_MODEL,
    CHROMA_COLLECTION_NAME,
    CHROMA_DB_PATH,
    EMBEDDING_MODEL,
    GITHUB_API_BASE_URL,
    GITHUB_BASE_BRANCH,
    GITHUB_REPOSITORY,
    GITHUB_UPLOAD_TOKEN,
    OPENAI_API_KEY,
    WIKI_DB_PATH,
)
from src.pipeline.vectorstore import init_collection
from src.wiki import query as wiki_query_module

load_wiki_graph_neighborhood = getattr(
    wiki_query_module,
    "load_wiki_graph_neighborhood",
    None,
)
wiki_database_exists = wiki_query_module.wiki_database_exists

WORK_TYPE_OPTIONS = [
    "hw",
    "midterm",
    "final",
    "exam",
    "quiz",
    "notes",
    "lec",
    "custom",
]
QUARTER_OPTIONS = ["fall", "win", "spring"]
STREAMLIT_BOOTSTRAP_SKIP_ENV_VAR = "JENRAG_SKIP_STREAMLIT_BOOTSTRAP"
MARKDOWN_UPLOAD_DIRECTORY = "data/md"
LATEX_UPLOAD_DIRECTORY = "data/latex"
PDF_UPLOAD_DIRECTORY = "data/pdf"
UNMATCHED_LATEX_UPLOAD_DIRECTORY = "data/unmatched-tex"
UNMATCHED_PDF_UPLOAD_DIRECTORY = "data/unmatched-pdf"
SIDEBAR_WIKI_GRAPH_STATE_KEY = "sidebar_wiki_graph"
SIDEBAR_WIKI_GRAPH_SELECTION_KEY = "sidebar_wiki_graph_selection"
SIDEBAR_WIKI_GRAPH_HEIGHT = 320
SIDEBAR_WIKI_GRAPH_SEED_COLOR = "#7EB6FF"
SIDEBAR_WIKI_GRAPH_RELATED_COLOR = "#4C566A"
SIDEBAR_WIKI_GRAPH_EDGE_COLOR = "#8A93A2"
SIDEBAR_WIKI_GRAPH_HIGHLIGHT_COLOR = "#F2CC8F"
SIDEBAR_WIKI_GRAPH_NODE_SPACING = 220
SIDEBAR_WIKI_GRAPH_SPRING_LENGTH = 180
SIDEBAR_WIKI_GRAPH_SPRING_STRENGTH = 0.04
UPLOAD_FILE_KEY = "upload_file"
UPLOAD_FILE_SIGNATURE_KEY = "upload_file_signature"
UPLOAD_COURSE_CATEGORY_KEY = "upload_course_category"
UPLOAD_COURSE_NUMBER_KEY = "upload_course_number"
UPLOAD_QUARTER_KEY = "upload_quarter"
UPLOAD_YEAR_KEY = "upload_year"
UPLOAD_WORK_TYPE_KEY = "upload_work_type"
UPLOAD_WORK_NUMBER_KEY = "upload_work_number"
UPLOAD_CUSTOM_WORK_TYPE_KEY = "upload_custom_work_type"
UPLOAD_PROFESSOR_LAST_NAME_KEY = "upload_professor_last_name"
UPLOAD_SUBMITTER_NAME_KEY = "upload_submitter_name"
UPLOAD_SUBMISSION_NOTE_KEY = "upload_submission_note"
INLINE_MATH_DELIMITER = "$"
DISPLAY_MATH_DELIMITER = "$$"


def _delimiter_is_escaped(text: str, delimiter_index: int) -> bool:
    """Return whether the delimiter at the given index is escaped."""
    backslash_count = 0
    check_index = delimiter_index - 1
    while check_index >= 0 and text[check_index] == "\\":
        backslash_count += 1
        check_index -= 1
    return backslash_count % 2 == 1


def _find_unescaped_delimiter(
    text: str,
    delimiter: str,
    start_index: int,
) -> int:
    """Return the next unescaped delimiter index or -1 when absent."""
    search_index = start_index
    while True:
        delimiter_index = text.find(delimiter, search_index)
        if delimiter_index == -1:
            return -1
        if not _delimiter_is_escaped(text, delimiter_index):
            if delimiter == INLINE_MATH_DELIMITER:
                if delimiter_index + 1 < len(text) and text[delimiter_index + 1] == "$":
                    search_index = delimiter_index + 1
                    continue
            return delimiter_index
        search_index = delimiter_index + 1


def _parse_math_segments(content: str) -> list[tuple[str, str]]:
    """Split content into markdown prose and display-math segments."""
    segments: list[tuple[str, str]] = []
    prose_parts: list[str] = []
    cursor = 0
    opener_pattern = re.compile(r"\\\[|\\\(|\$\$|\$")
    delimiter_pairs = {
        r"\[": r"\]",
        r"\(": r"\)",
        DISPLAY_MATH_DELIMITER: DISPLAY_MATH_DELIMITER,
        INLINE_MATH_DELIMITER: INLINE_MATH_DELIMITER,
    }
    display_delimiters = {r"\[", DISPLAY_MATH_DELIMITER}

    while cursor < len(content):
        opener_match = opener_pattern.search(content, cursor)
        if opener_match is None:
            prose_parts.append(content[cursor:])
            break

        opener = opener_match.group(0)
        opener_index = opener_match.start()
        if _delimiter_is_escaped(content, opener_index):
            prose_parts.append(content[cursor:opener_index + 1])
            cursor = opener_index + 1
            continue

        prose_parts.append(content[cursor:opener_index])
        closer = delimiter_pairs[opener]
        math_start_index = opener_match.end()
        closer_index = _find_unescaped_delimiter(content, closer, math_start_index)
        if closer_index == -1:
            prose_parts.append(content[opener_index:])
            break

        math_content = content[math_start_index:closer_index].strip()
        if opener in display_delimiters:
            prose_text = "".join(prose_parts)
            if prose_text:
                segments.append(("markdown", prose_text))
            segments.append(("display_math", math_content))
            prose_parts = []
        else:
            prose_parts.append(
                f"{INLINE_MATH_DELIMITER}{math_content}{INLINE_MATH_DELIMITER}"
            )

        cursor = closer_index + len(closer)

    prose_text = "".join(prose_parts)
    if prose_text:
        segments.append(("markdown", prose_text))

    return segments


def render_assistant_message_content(content: str) -> None:
    """Render assistant chat content with Streamlit markdown and math blocks."""
    for segment_type, segment_value in _parse_math_segments(content):
        if segment_type == "display_math":
            st.latex(segment_value)
        else:
            st.markdown(segment_value)


def get_missing_chat_configuration() -> list[str]:
    """Return any required chat settings missing from env vars or secrets."""
    missing_settings: list[str] = []
    required_settings = {
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "CHAT_MODEL": CHAT_MODEL,
        "EMBEDDING_MODEL": EMBEDDING_MODEL,
    }
    for setting_name, setting_value in required_settings.items():
        if not setting_value:
            missing_settings.append(setting_name)
    return missing_settings


def build_markdown_upload_target_path(upload_metadata: UploadMetadata) -> str:
    """Return the canonical Markdown path for an upload."""
    course_folder = (
        f"{upload_metadata.course_category}_{upload_metadata.course_number}"
    )
    filename_stem = build_filename_stem(upload_metadata)
    return f"{MARKDOWN_UPLOAD_DIRECTORY}/{course_folder}/{filename_stem}.md"


def build_raw_upload_target_path(
    upload_metadata: UploadMetadata,
    extension: str,
    matching_markdown_exists: bool,
) -> str:
    """Return matched or unmatched raw upload path for `.tex` and `.pdf` files."""
    normalized_extension = extension.strip().lower()
    course_folder = (
        f"{upload_metadata.course_category}_{upload_metadata.course_number}"
    )
    filename_stem = build_filename_stem(upload_metadata)

    if normalized_extension == ".tex":
        base_directory = (
            LATEX_UPLOAD_DIRECTORY
            if matching_markdown_exists
            else UNMATCHED_LATEX_UPLOAD_DIRECTORY
        )
        return f"{base_directory}/{course_folder}/{filename_stem}.tex"

    if normalized_extension == ".pdf":
        base_directory = (
            PDF_UPLOAD_DIRECTORY
            if matching_markdown_exists
            else UNMATCHED_PDF_UPLOAD_DIRECTORY
        )
        return f"{base_directory}/{course_folder}/{filename_stem}.pdf"

    raise UploadValidationError("Raw upload path only supports .tex and .pdf files.")


def get_missing_upload_configuration() -> list[str]:
    """Return any required upload settings missing from env vars or secrets."""
    missing_settings: list[str] = []
    required_settings = {
        "GITHUB_REPOSITORY": GITHUB_REPOSITORY,
        "GITHUB_UPLOAD_TOKEN": GITHUB_UPLOAD_TOKEN,
    }
    for setting_name, setting_value in required_settings.items():
        if not setting_value:
            missing_settings.append(setting_name)
    return missing_settings


def initialize_upload_form_state() -> None:
    """Seed upload form session state once so fields remain editable."""
    upload_form_defaults = {
        UPLOAD_COURSE_CATEGORY_KEY: "",
        UPLOAD_COURSE_NUMBER_KEY: "",
        UPLOAD_QUARTER_KEY: QUARTER_OPTIONS[0],
        UPLOAD_YEAR_KEY: 2026,
        UPLOAD_WORK_TYPE_KEY: WORK_TYPE_OPTIONS[0],
        UPLOAD_WORK_NUMBER_KEY: "",
        UPLOAD_CUSTOM_WORK_TYPE_KEY: "",
        UPLOAD_PROFESSOR_LAST_NAME_KEY: "",
        UPLOAD_SUBMITTER_NAME_KEY: "",
        UPLOAD_SUBMISSION_NOTE_KEY: "",
        UPLOAD_FILE_SIGNATURE_KEY: "",
    }
    for state_key, default_value in upload_form_defaults.items():
        st.session_state.setdefault(state_key, default_value)


def build_uploaded_file_signature(uploaded_file: ValidatedUploadedFile) -> str:
    """Return stable signature for upload auto-fill tracking."""
    return f"{uploaded_file.file_name}:{len(uploaded_file.file_bytes)}"


def apply_upload_form_defaults(upload_form_defaults: UploadFormDefaults) -> None:
    """Write parsed upload defaults into editable form state."""
    st.session_state[UPLOAD_COURSE_CATEGORY_KEY] = upload_form_defaults.course_category
    st.session_state[UPLOAD_COURSE_NUMBER_KEY] = upload_form_defaults.course_number
    st.session_state[UPLOAD_QUARTER_KEY] = upload_form_defaults.quarter
    st.session_state[UPLOAD_YEAR_KEY] = upload_form_defaults.year
    st.session_state[UPLOAD_WORK_TYPE_KEY] = upload_form_defaults.work_type
    st.session_state[UPLOAD_WORK_NUMBER_KEY] = upload_form_defaults.work_number
    st.session_state[UPLOAD_CUSTOM_WORK_TYPE_KEY] = (
        upload_form_defaults.custom_work_type
    )
    st.session_state[UPLOAD_PROFESSOR_LAST_NAME_KEY] = (
        upload_form_defaults.professor_last_name
    )


def validate_chat_runtime_state() -> list[str]:
    """Check for deployment issues before users start querying the app."""
    errors: list[str] = []

    missing_settings = get_missing_chat_configuration()
    if missing_settings:
        errors.append(
            "Missing configuration: " + ", ".join(missing_settings)
        )

    if not os.path.isdir(CHROMA_DB_PATH):
        errors.append(
            f"ChromaDB path not found: {CHROMA_DB_PATH}. Build the index locally and commit the read-only snapshot before deploying."
        )
        return errors

    try:
        collection = init_collection(CHROMA_DB_PATH, CHROMA_COLLECTION_NAME)
        if collection.count() == 0:
            errors.append(
                "ChromaDB collection is empty. Run the ingest pipeline locally before deploying."
            )
    except Exception as error:
        errors.append(f"Could not open ChromaDB collection: {error}")

    return errors


def run_pipeline(query: str, use_reranker: bool, rerank_top_k: int) -> dict:
    """Run the full RAG pipeline and return results with timing."""
    timings = {}

    retrieval_start_time = time.time()
    retrieval_result = retrieve(
        query,
        rerank_top_k=rerank_top_k,
        use_reranker=use_reranker,
    )
    timings["retrieval"] = time.time() - retrieval_start_time

    generation_start_time = time.time()
    answer = generate(query, retrieval_result)
    timings["generation"] = time.time() - generation_start_time

    timings["total"] = timings["retrieval"] + timings["generation"]

    return {"answer": answer, "retrieval": retrieval_result, "timings": timings}


def build_sidebar_wiki_graph_payload(retrieval_result) -> dict[str, list[dict[str, object]]] | None:
    """Build a compact sidebar graph payload from retrieved wiki page hits."""
    if load_wiki_graph_neighborhood is None:
        return None

    matched_page_slugs = [
        wiki_page_hit.slug
        for wiki_page_hit in retrieval_result.wiki_page_hits
        if wiki_page_hit.slug
    ]
    graph_nodes, graph_edges = load_wiki_graph_neighborhood(
        matched_page_slugs,
        database_path=WIKI_DB_PATH,
    )
    if not graph_nodes:
        return None

    return {
        "nodes": [
            {
                "slug": graph_node.slug,
                "title": graph_node.title,
                "page_type": graph_node.page_type,
                "is_seed": graph_node.is_seed,
            }
            for graph_node in graph_nodes
        ],
        "edges": [
            {
                "from_slug": graph_edge.from_slug,
                "to_slug": graph_edge.to_slug,
                "relation": graph_edge.relation,
            }
            for graph_edge in graph_edges
        ],
    }


def render_sidebar_wiki_graph(wiki_database_available: bool) -> None:
    """Render a small retrieval-driven wiki graph panel inside the sidebar."""
    with st.container(border=True):
        st.markdown("**Local Wiki Graph**")

        if not wiki_database_available:
            st.caption("Wiki graph unavailable.")
            return

        sidebar_wiki_graph_payload = st.session_state.get(
            SIDEBAR_WIKI_GRAPH_STATE_KEY
        )
        if not sidebar_wiki_graph_payload:
            st.caption("No wiki graph for this query yet.")
            return

        if not all([agraph, Node, Edge, Config]):
            st.caption("Wiki graph dependency missing.")
            return

        graph_nodes = []
        for graph_node_payload in sidebar_wiki_graph_payload["nodes"]:
            node_color = (
                SIDEBAR_WIKI_GRAPH_SEED_COLOR
                if graph_node_payload["is_seed"]
                else SIDEBAR_WIKI_GRAPH_RELATED_COLOR
            )
            graph_nodes.append(
                Node(
                    id=graph_node_payload["slug"],
                    label="",
                    title=(
                        f"{graph_node_payload['title']} "
                        f"[{graph_node_payload['page_type']}]"
                    ),
                    color=node_color,
                    size=20 if graph_node_payload["is_seed"] else 14,
                    shape="dot",
                )
            )

        graph_edges = []
        for graph_edge_payload in sidebar_wiki_graph_payload["edges"]:
            graph_edges.append(
                Edge(
                    source=graph_edge_payload["from_slug"],
                    target=graph_edge_payload["to_slug"],
                    color=SIDEBAR_WIKI_GRAPH_EDGE_COLOR,
                )
            )

        graph_config = Config(
            width="100%",
            height=SIDEBAR_WIKI_GRAPH_HEIGHT,
            directed=False,
            hierarchical=False,
            collapsible=False,
            staticGraph=False,
            nodeHighlightBehavior=True,
            highlightColor=SIDEBAR_WIKI_GRAPH_HIGHLIGHT_COLOR,
            labelProperty="title",
            physics={
                "enabled": True,
                "solver": "forceAtlas2Based",
                "forceAtlas2Based": {
                    "gravitationalConstant": -80,
                    "centralGravity": 0.01,
                    "springLength": SIDEBAR_WIKI_GRAPH_SPRING_LENGTH,
                    "springConstant": SIDEBAR_WIKI_GRAPH_SPRING_STRENGTH,
                    "avoidOverlap": 1.2,
                },
                "minVelocity": 0.75,
                "timestep": 0.35,
            },
            interaction={
                "hover": True,
                "tooltipDelay": 100,
            },
            layout={
                "improvedLayout": True,
            },
        )
        selected_node_slug = agraph(
            nodes=graph_nodes,
            edges=graph_edges,
            config=graph_config,
        )
        if selected_node_slug:
            st.session_state[SIDEBAR_WIKI_GRAPH_SELECTION_KEY] = selected_node_slug


def render_sidebar() -> tuple[bool, int]:
    """Render chat controls shared across the app."""
    with st.sidebar:
        st.header("Pipeline Settings")
        use_reranker = st.toggle("Enable reranker", value=True)
        rerank_top_k = st.slider("Chunks to keep after reranking", 3, 15, 5)
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pop(SIDEBAR_WIKI_GRAPH_STATE_KEY, None)
            st.session_state.pop(SIDEBAR_WIKI_GRAPH_SELECTION_KEY, None)
            st.rerun()
        st.divider()
        st.markdown("**Stack:** Embedding → ChromaDB → BGE Reranker → LLM")
        st.caption(
            "Uploads create GitHub pull requests. "
            "Merged files still need manual `ingest`, `build-wiki`, and artifact commits before search can use them."
        )
        wiki_database_available = wiki_database_exists(WIKI_DB_PATH)
        wiki_status = "available" if wiki_database_available else "missing"
        st.caption(f"Wiki sidecar: {wiki_status}")
        render_sidebar_wiki_graph(wiki_database_available)

    return use_reranker, rerank_top_k


def render_retrieval_debug(retrieval_result) -> None:
    """Render chunk hits, wiki page hits, and related topics for debugging."""
    with st.expander(f"Retrieved chunks ({len(retrieval_result.chunk_hits)})"):
        for index, chunk_hit in enumerate(retrieval_result.chunk_hits, 1):
            st.text(f"--- Chunk {index} ---")
            st.text(chunk_hit.format_for_prompt()[:700] + ("..." if len(chunk_hit.text) > 700 else ""))

    with st.expander(f"Matched wiki pages ({len(retrieval_result.wiki_page_hits)})"):
        for index, wiki_page_hit in enumerate(retrieval_result.wiki_page_hits, 1):
            st.markdown(
                f"**{index}. {wiki_page_hit.title}**  \n"
                f"`{wiki_page_hit.slug}` · `{wiki_page_hit.page_type}` · "
                f"`{wiki_page_hit.source_path}`"
            )
            st.text(wiki_page_hit.summary[:500] + ("..." if len(wiki_page_hit.summary) > 500 else ""))

    with st.expander(f"Related topics ({len(retrieval_result.related_topics)})"):
        if retrieval_result.related_topics:
            for related_topic in retrieval_result.related_topics:
                st.markdown(f"- `{related_topic.slug}` — {related_topic.title}")
        else:
            st.caption("No related topics found.")


def render_chat_tab(use_reranker: bool, rerank_top_k: int) -> None:
    """Render the existing chat interface."""
    query = st.chat_input("Ask a PSET question...")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_assistant_message_content(message["content"])
            else:
                st.markdown(message["content"])
            if "retrieval" in message:
                render_retrieval_debug(message["retrieval"])
            if "timings" in message:
                columns = st.columns(3)
                columns[0].metric("Retrieval", f"{message['timings']['retrieval']:.1f}s")
                columns[1].metric("Generation", f"{message['timings']['generation']:.1f}s")
                columns[2].metric("Total", f"{message['timings']['total']:.1f}s")

    if not query:
        return

    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Retrieving and generating..."):
                result = run_pipeline(query, use_reranker, rerank_top_k)
        except Exception as error:
            st.error(
                "The hosted app could not complete this request. "
                "Check deployment secrets, model connectivity, and the bundled Chroma index."
            )
            st.exception(error)
            st.stop()

        st.session_state[SIDEBAR_WIKI_GRAPH_STATE_KEY] = (
            build_sidebar_wiki_graph_payload(result["retrieval"])
        )
        assistant_message = {
            "role": "assistant",
            "content": result["answer"],
            "retrieval": result["retrieval"],
            "timings": result["timings"],
        }
        st.session_state.messages.append(assistant_message)
        st.rerun()


def render_upload_tab() -> None:
    """Render the GitHub-backed upload form."""
    st.subheader("Upload Study Material")
    st.caption(
        "Upload one `.md`, `.tex`, or `.pdf` file. "
        "The app will open a GitHub pull request into the repo."
    )
    st.info(
        "Markdown uploads are ingest-ready. PDF and LaTeX uploads route into matched "
        "or unmatched raw-source folders based on whether canonical Markdown already "
        "exists on the base branch. Raw uploads may still need maintainer conversion "
        "into `data/md` before running `uv run ingest`."
    )

    missing_upload_settings = get_missing_upload_configuration()
    if missing_upload_settings:
        st.warning(
            "Upload feature is disabled until these secrets are configured: "
            + ", ".join(missing_upload_settings)
        )
        return

    initialize_upload_form_state()

    uploaded_file = st.file_uploader(
        "File",
        type=["md", "tex", "pdf"],
        help="Accepted types: .md, .tex, .pdf",
        key=UPLOAD_FILE_KEY,
    )

    validated_upload: ValidatedUploadedFile | None = None
    validation_errors: list[str] = []
    if uploaded_file is not None:
        try:
            validated_upload = validate_uploaded_file(
                file_name=uploaded_file.name,
                file_bytes=uploaded_file.getvalue(),
            )
            uploaded_file_signature = build_uploaded_file_signature(validated_upload)
            if st.session_state[UPLOAD_FILE_SIGNATURE_KEY] != uploaded_file_signature:
                upload_form_defaults = derive_upload_form_defaults_from_file_name(
                    validated_upload.file_name
                )
                if upload_form_defaults is not None:
                    apply_upload_form_defaults(upload_form_defaults)
                st.session_state[UPLOAD_FILE_SIGNATURE_KEY] = uploaded_file_signature
        except UploadValidationError as error:
            validation_errors.append(str(error))
    else:
        st.session_state[UPLOAD_FILE_SIGNATURE_KEY] = ""

    metadata_column_left, metadata_column_right = st.columns(2)
    with metadata_column_left:
        course_category = st.text_input(
            "Course category",
            placeholder="CMSC",
            key=UPLOAD_COURSE_CATEGORY_KEY,
        )
        course_number = st.text_input(
            "Course number",
            placeholder="27100",
            key=UPLOAD_COURSE_NUMBER_KEY,
        )
        quarter = st.selectbox(
            "Quarter",
            options=QUARTER_OPTIONS,
            key=UPLOAD_QUARTER_KEY,
        )
        year = st.number_input(
            "Year",
            min_value=2000,
            max_value=2100,
            value=2026,
            step=1,
            key=UPLOAD_YEAR_KEY,
        )
        work_type = st.selectbox(
            "Work type",
            options=WORK_TYPE_OPTIONS,
            key=UPLOAD_WORK_TYPE_KEY,
        )
        work_number = ""
        custom_work_type = ""
        if work_type == "custom":
            custom_work_type = st.text_input(
                "Custom work type",
                placeholder="take home exam",
                key=UPLOAD_CUSTOM_WORK_TYPE_KEY,
            )
        else:
            work_number = st.text_input(
                "Work number",
                placeholder="1",
                key=UPLOAD_WORK_NUMBER_KEY,
            )

    with metadata_column_right:
        professor_last_name = st.text_input(
            "Professor last name",
            placeholder="Ng",
            key=UPLOAD_PROFESSOR_LAST_NAME_KEY,
        )
        submitter_name = st.text_input(
            "Submitter name",
            placeholder="Jane Doe",
            key=UPLOAD_SUBMITTER_NAME_KEY,
        )
        submission_note = st.text_area(
            "Submission note",
            placeholder="Optional context for reviewer",
            key=UPLOAD_SUBMISSION_NOTE_KEY,
        )

    upload_metadata: UploadMetadata | None = None

    form_has_started = any(
        [
            uploaded_file is not None,
            course_category,
            course_number,
            professor_last_name,
            submitter_name,
            submission_note,
            custom_work_type,
            work_number,
        ]
    )

    try:
        upload_metadata = normalize_upload_metadata(
            course_category=course_category,
            course_number=course_number,
            quarter=quarter,
            year=year,
            work_type=work_type,
            work_number=work_number,
            custom_work_type=custom_work_type,
            professor_last_name=professor_last_name,
            submitter_name=submitter_name,
            submission_note=submission_note,
        )
    except UploadValidationError as error:
        if form_has_started:
            validation_errors.append(str(error))

    if validation_errors:
        for validation_error in validation_errors:
            st.error(validation_error)

    target_path = ""
    if validated_upload is not None and upload_metadata is not None:
        filename_stem = build_filename_stem(upload_metadata)
        st.markdown("**Filename Preview**")
        st.code(f"{filename_stem}{validated_upload.extension}")
        if validated_upload.extension == ".md":
            target_path = build_target_path(upload_metadata, validated_upload.extension)
            st.markdown("**Target Path Preview**")
            st.code(target_path)
        else:
            matching_markdown_path = build_markdown_upload_target_path(upload_metadata)
            matched_target_path = build_raw_upload_target_path(
                upload_metadata=upload_metadata,
                extension=validated_upload.extension,
                matching_markdown_exists=True,
            )
            unmatched_target_path = build_raw_upload_target_path(
                upload_metadata=upload_metadata,
                extension=validated_upload.extension,
                matching_markdown_exists=False,
            )
            st.markdown("**Target Path Preview**")
            st.code(
                "matching markdown exists -> "
                f"{matched_target_path}\n"
                "matching markdown missing -> "
                f"{unmatched_target_path}"
            )
            st.caption(
                f"Canonical Markdown path checked on `{GITHUB_BASE_BRANCH}`: "
                f"`{matching_markdown_path}`"
            )
    elif form_has_started:
        st.info("Complete all required fields to preview the final path.")

    if st.button(
        "Create Upload Pull Request",
        disabled=validated_upload is None or upload_metadata is None,
        use_container_width=True,
    ):
        create_upload_pull_request(
            upload_metadata=upload_metadata,
            validated_upload=validated_upload,
            target_path=target_path,
        )


def create_upload_pull_request(
    upload_metadata: UploadMetadata | None,
    validated_upload: ValidatedUploadedFile | None,
    target_path: str,
) -> None:
    """Submit a validated upload into GitHub as a pull request."""
    if upload_metadata is None or validated_upload is None:
        st.error("Upload is not ready to submit.")
        return

    github_client = GitHubUploadClient(
        repository=str(GITHUB_REPOSITORY),
        token=str(GITHUB_UPLOAD_TOKEN),
        base_branch=str(GITHUB_BASE_BRANCH),
        api_base_url=str(GITHUB_API_BASE_URL),
    )

    with st.spinner("Creating GitHub pull request..."):
        try:
            target_path = resolve_upload_target_path(
                github_client=github_client,
                upload_metadata=upload_metadata,
                extension=validated_upload.extension,
            )

            if github_client.path_exists_on_base_branch(target_path):
                st.error(
                    "A file already exists at this path on the base branch:\n"
                    f"`{target_path}`"
                )
                return

            branch_name = build_upload_branch_name(upload_metadata)
            file_name = f"{build_filename_stem(upload_metadata)}{validated_upload.extension}"
            pull_request_title = f"Add {file_name}"
            commit_message = f"Add {file_name}"
            pull_request_body = build_pull_request_body(
                upload_metadata=upload_metadata,
                target_path=target_path,
                original_file_name=validated_upload.file_name,
            )
            pull_request_result = github_client.create_upload_pull_request(
                repo_path=target_path,
                file_bytes=validated_upload.file_bytes,
                branch_name=branch_name,
                pull_request_title=pull_request_title,
                pull_request_body=pull_request_body,
                commit_message=commit_message,
            )
        except GitHubUploadError as error:
            st.error(str(error))
            return

    st.success(
        f"Pull request #{pull_request_result.number} created for `{target_path}`."
    )
    st.markdown(f"[Open pull request]({pull_request_result.html_url})")
    st.info(
        "After merge, raw `.pdf` or `.tex` uploads may land in matched or unmatched "
        "raw-source folders depending on whether canonical Markdown already existed. "
        "Maintainers may still need to convert raw uploads into `data/md` first. "
        "Search updates still require re-running `ingest`, re-running `build-wiki`, "
        "and committing `data/chroma_db`, `data/wiki.sqlite3`, and "
        "`data/wiki_report.md`."
    )


def resolve_upload_target_path(
    github_client: GitHubUploadClient,
    upload_metadata: UploadMetadata,
    extension: str,
) -> str:
    """Resolve final repo path for an upload using base-branch Markdown presence."""
    normalized_extension = extension.strip().lower()
    if normalized_extension == ".md":
        return build_markdown_upload_target_path(upload_metadata)

    matching_markdown_path = build_markdown_upload_target_path(upload_metadata)
    matching_markdown_exists = github_client.path_exists_on_base_branch(
        matching_markdown_path
    )
    return build_raw_upload_target_path(
        upload_metadata=upload_metadata,
        extension=normalized_extension,
        matching_markdown_exists=matching_markdown_exists,
    )


def build_pull_request_body(
    upload_metadata: UploadMetadata,
    target_path: str,
    original_file_name: str,
) -> str:
    """Return a structured pull request body for upload reviews."""
    course_folder = (
        f"{upload_metadata.course_category}_{upload_metadata.course_number}"
    )
    pull_request_lines = [
        "## Upload Submission",
        "",
        f"- Submitter name: {upload_metadata.submitter_name}",
        f"- Original file name: {original_file_name}",
        f"- Target path: `{target_path}`",
        f"- Course folder: `{course_folder}`",
        f"- Quarter: `{upload_metadata.quarter}`",
        f"- Year: `{upload_metadata.year}`",
        f"- Work segment: `{upload_metadata.work_segment}`",
        f"- Professor last name: `{upload_metadata.professor_last_name}`",
    ]

    if upload_metadata.submission_note:
        pull_request_lines.extend(
            [
                "",
                "## Submission Note",
                "",
                upload_metadata.submission_note,
            ]
        )

    pull_request_lines.extend(
        [
            "",
            "## Follow-Up",
            "",
            "- Merge this pull request.",
            "- If the uploaded file is `.pdf` or `.tex`, convert it into a reviewed Markdown file under `data/md` before ingest.",
            "- Re-run `uv run ingest` locally.",
            "- Re-run `uv run build-wiki` locally.",
            "- Review `data/wiki_report.md`.",
            "- Commit the updated `data/chroma_db`, `data/wiki.sqlite3`, and `data/wiki_report.md` snapshots.",
        ]
    )

    return "\n".join(pull_request_lines)


def validate_work_type_configuration() -> None:
    """Guard against drift between UI options and normalization rules."""
    if set(WORK_TYPE_OPTIONS) != PRESET_WORK_TYPES:
        raise RuntimeError("Work type options do not match upload normalization rules.")


def render_application() -> None:
    """Render the full Streamlit application."""
    validate_work_type_configuration()
    st.set_page_config(page_title="JenRAG", page_icon="📝", layout="wide")
    st.title("JenRAG")
    st.caption(
        "Ask about homework, exam problems, solutions, and notes. "
        "Each signed-in user keeps a separate chat session."
    )

    use_reranker, rerank_top_k = render_sidebar()
    chat_runtime_errors = validate_chat_runtime_state()
    if chat_runtime_errors:
        st.error("JenRAG is not configured correctly for this deployment.")
        for chat_runtime_error in chat_runtime_errors:
            st.code(chat_runtime_error)
        st.stop()

    chat_tab, upload_tab = st.tabs(["Chat", "Upload"])
    with chat_tab:
        render_chat_tab(use_reranker, rerank_top_k)

    with upload_tab:
        render_upload_tab()


if os.getenv(STREAMLIT_BOOTSTRAP_SKIP_ENV_VAR) != "1":
    render_application()
