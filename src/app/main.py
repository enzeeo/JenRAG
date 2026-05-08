from dataclasses import dataclass, field
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
SIDEBAR_WIKI_GRAPH_SEED_COLOR = "#b8c4ff"
SIDEBAR_WIKI_GRAPH_RELATED_COLOR = "#4C566A"
SIDEBAR_WIKI_GRAPH_PRIMARY_NODE_COLOR = "#FFFFFF"
MISSING_CONFIGURATION_SENTINELS = {"", "none", "null"}
SIDEBAR_WIKI_GRAPH_EDGE_COLOR = "#8A93A2"
SIDEBAR_WIKI_GRAPH_HIGHLIGHT_COLOR = "#F2CC8F"
SIDEBAR_WIKI_GRAPH_NODE_SPACING = 220
SIDEBAR_WIKI_GRAPH_SPRING_LENGTH = 180
SIDEBAR_WIKI_GRAPH_SPRING_STRENGTH = 0.04
SIDEBAR_WIKI_GRAPH_MAX_HOVER_WORDS = 4
SIDEBAR_WIKI_GRAPH_MAX_HOVER_CHARACTERS = 36
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
PRIMARY_BLUE_COLOR = "#b8c4ff"
SIDEBAR_TEXT_COLOR = "#b8c4ff"
DARK_BLUE_ACCENT_COLOR = "#b8c4ff"
SIDEBAR_BACKGROUND_COLOR = "#1c2638"
APP_BACKGROUND_COLOR = "#0e1629"
MONOSPACE_FONT_FAMILY = (
    "'SFMono-Regular', 'SF Mono', 'Menlo', 'Consolas', 'Liberation Mono', monospace"
)
CHAT_COMPOSER_BOTTOM_OFFSET = "max(1rem, env(safe-area-inset-bottom))"
CHAT_COMPOSER_MIN_HEIGHT = "3.5rem"
CHAT_COMPOSER_CONTENT_PADDING = "6rem"
CHAT_COMPOSER_VIEWPORT_MARGIN = "1rem"
CONVERSATION_MEMORY_STATE_KEY = "conversation_memory"
APPROX_MAX_CONTEXT_TOKENS = 200000
APPROX_CONTEXT_COMPACTION_TOKENS = 140000
COMPACTION_RECENT_TURN_COUNT = 4
MAX_TRACKED_CONVERSATION_ENTITIES = 16
MAX_ACTIVE_REFERENCES = 4
MAX_ENTITY_EXCERPT_CHARACTERS = 420
REFERENTIAL_QUERY_PATTERNS = (
    "that",
    "this",
    "it",
    "those",
    "these",
    "the last one",
    "last one",
    "previous one",
    "follow up",
    "follow-up",
    "what does this relate to",
    "what does that relate to",
    "what topic is this from",
    "what concept is behind that",
    "explain that",
    "explain this",
    "explain that part",
    "i don't understand",
    "i dont understand",
    "why is that true",
    "solve it",
    "provide a solution",
    "check my answer",
    "where did that come from",
    "where was that in the notes",
    "is that from lecture or homework",
    "why is that a trap",
)


@dataclass(frozen=True)
class ConversationTurn:
    role: str
    content: str
    turn_index: int


@dataclass(frozen=True)
class ConversationEntity:
    entity_id: str
    entity_type: str
    label: str
    canonical_text: str
    source_turn_index: int
    related_hints: list[str] = field(default_factory=list)
    status: str = "active"


@dataclass(frozen=True)
class ConversationReferenceState:
    entity_id: str
    entity_type: str
    label: str
    source_turn_index: int
    reason: str


@dataclass(frozen=True)
class QueryResolution:
    resolved_query_text: str
    resolved_reference_entities: list[ConversationEntity]
    resolution_confidence: str
    is_follow_up: bool
    unresolved_reason: str = ""


@dataclass
class ConversationMemoryState:
    compacted_summary: dict[str, list[str] | str] = field(default_factory=dict)
    recent_turns: list[ConversationTurn] = field(default_factory=list)
    conversation_entities: list[ConversationEntity] = field(default_factory=list)
    active_references: list[ConversationReferenceState] = field(default_factory=list)
    compaction_metadata: dict[str, int | str | None] = field(default_factory=dict)


def build_empty_conversation_summary() -> dict[str, list[str] | str]:
    """Return the default compacted-summary structure."""
    return {
        "user_goals": [],
        "explained_concepts": [],
        "notes_topics": [],
        "exam_traps": [],
        "generated_problems": [],
        "solution_strategies": [],
        "source_sections": [],
        "unresolved_questions": [],
        "last_compacted_user_message": "",
    }


def build_initial_conversation_memory_state() -> ConversationMemoryState:
    """Create the default session-scoped memory state."""
    return ConversationMemoryState(
        compacted_summary=build_empty_conversation_summary(),
        recent_turns=[],
        conversation_entities=[],
        active_references=[],
        compaction_metadata={
            "estimated_tokens": 0,
            "compaction_count": 0,
            "last_compacted_turn": None,
            "last_turn_index": 0,
            "latest_unresolved_follow_up": "",
        },
    )


def get_conversation_memory_state() -> ConversationMemoryState:
    """Return the conversation memory state from Streamlit session state."""
    if CONVERSATION_MEMORY_STATE_KEY not in st.session_state:
        st.session_state[CONVERSATION_MEMORY_STATE_KEY] = (
            build_initial_conversation_memory_state()
        )
    return st.session_state[CONVERSATION_MEMORY_STATE_KEY]


def estimate_token_count_from_text(text: str) -> int:
    """Approximate token count conservatively from text length."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def shorten_text_excerpt(text: str, maximum_characters: int = MAX_ENTITY_EXCERPT_CHARACTERS) -> str:
    """Trim text for compact memory storage."""
    normalized_text = " ".join(text.split())
    if len(normalized_text) <= maximum_characters:
        return normalized_text
    return normalized_text[: maximum_characters - 3].rstrip() + "..."


def build_conversation_summary_text(
    compacted_summary: dict[str, list[str] | str],
) -> str:
    """Format compacted summary fields into prompt text."""
    lines = ["## Compacted Summary"]
    list_sections = [
        ("user_goals", "User goals"),
        ("explained_concepts", "Explained concepts"),
        ("notes_topics", "Notes topics"),
        ("exam_traps", "Exam traps"),
        ("generated_problems", "Generated problems"),
        ("solution_strategies", "Solution strategies"),
        ("source_sections", "Source sections"),
        ("unresolved_questions", "Unresolved questions"),
    ]

    for field_name, label in list_sections:
        values = compacted_summary.get(field_name, [])
        if values:
            lines.append(f"{label}: " + " | ".join(str(value) for value in values))
        else:
            lines.append(f"{label}: none")

    last_compacted_user_message = str(
        compacted_summary.get("last_compacted_user_message", "")
    ).strip()
    if last_compacted_user_message:
        lines.append(f"Last compacted user message: {last_compacted_user_message}")

    return "\n".join(lines)


def serialize_conversation_entity(entity: ConversationEntity) -> str:
    """Return a compact prompt line for one tracked conversation entity."""
    related_hint_text = ", ".join(entity.related_hints) if entity.related_hints else "none"
    return (
        f"- [{entity.entity_type}] {entity.label} "
        f"(turn {entity.source_turn_index}, status={entity.status}, hints={related_hint_text}) "
        f"{entity.canonical_text}"
    )


def build_conversation_memory_prompt_context(
    memory_state: ConversationMemoryState,
    resolution: QueryResolution,
) -> str:
    """Build the prompt block that carries conversation memory into generation."""
    lines = [build_conversation_summary_text(memory_state.compacted_summary), ""]

    lines.append("## Recent Raw Turns")
    if memory_state.recent_turns:
        for recent_turn in memory_state.recent_turns:
            lines.append(
                f"- Turn {recent_turn.turn_index} [{recent_turn.role}]: "
                f"{shorten_text_excerpt(recent_turn.content, 280)}"
            )
    else:
        lines.append("- none")

    lines.append("")
    lines.append("## Active References")
    if memory_state.active_references:
        for active_reference in memory_state.active_references:
            lines.append(
                f"- [{active_reference.entity_type}] {active_reference.label} "
                f"(turn {active_reference.source_turn_index}; reason={active_reference.reason})"
            )
    else:
        lines.append("- none")

    lines.append("")
    lines.append("## Tracked Entities")
    if memory_state.conversation_entities:
        for entity in memory_state.conversation_entities[-MAX_ACTIVE_REFERENCES:]:
            lines.append(serialize_conversation_entity(entity))
    else:
        lines.append("- none")

    lines.append("")
    lines.append("## Follow-Up Resolution")
    lines.append(
        f"- Follow-up detected: {'yes' if resolution.is_follow_up else 'no'}"
    )
    lines.append(f"- Resolution confidence: {resolution.resolution_confidence}")
    if resolution.resolved_reference_entities:
        for resolved_entity in resolution.resolved_reference_entities:
            lines.append(
                f"- Resolved target: [{resolved_entity.entity_type}] {resolved_entity.label}"
            )
    elif resolution.unresolved_reason:
        lines.append(f"- Unresolved: {resolution.unresolved_reason}")
    else:
        lines.append("- Resolved target: none")

    return "\n".join(lines)


def estimate_conversation_memory_tokens(memory_state: ConversationMemoryState) -> int:
    """Estimate the memory payload size using the same conservative approximation."""
    serialized_parts = [build_conversation_summary_text(memory_state.compacted_summary)]
    serialized_parts.extend(turn.content for turn in memory_state.recent_turns)
    serialized_parts.extend(
        serialize_conversation_entity(entity)
        for entity in memory_state.conversation_entities
    )
    serialized_parts.extend(
        f"{reference.entity_type}:{reference.label}:{reference.reason}"
        for reference in memory_state.active_references
    )
    return estimate_token_count_from_text("\n".join(serialized_parts))


def infer_query_topic_label(query: str) -> str:
    """Return a short topic label from the user query."""
    normalized_query = " ".join(query.strip().split())
    normalized_query = re.sub(
        r"^(explain|summarize|describe|solve|give|provide|what is|what are|why is|why does)\s+",
        "",
        normalized_query,
        flags=re.IGNORECASE,
    )
    return shorten_text_excerpt(normalized_query or query.strip(), 90)


def build_entity_identifier(entity_type: str, source_turn_index: int, label: str) -> str:
    """Create a stable session-local identifier for a conversation entity."""
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    if not slug:
        slug = "item"
    return f"{entity_type}-{source_turn_index}-{slug[:32]}"


def build_conversation_entity(
    entity_type: str,
    label: str,
    canonical_text: str,
    source_turn_index: int,
    related_hints: list[str] | None = None,
    status: str = "active",
) -> ConversationEntity:
    """Create one tracked conversation entity."""
    return ConversationEntity(
        entity_id=build_entity_identifier(entity_type, source_turn_index, label),
        entity_type=entity_type,
        label=shorten_text_excerpt(label, 90),
        canonical_text=shorten_text_excerpt(canonical_text),
        source_turn_index=source_turn_index,
        related_hints=related_hints or [],
        status=status,
    )


def get_next_conversation_turn_index(memory_state: ConversationMemoryState) -> int:
    """Return the next session-local turn index."""
    last_turn_index = int(memory_state.compaction_metadata.get("last_turn_index", 0) or 0)
    return last_turn_index + 1


def store_conversation_turn(
    memory_state: ConversationMemoryState,
    role: str,
    content: str,
) -> ConversationTurn:
    """Append a raw turn into the memory state."""
    turn = ConversationTurn(
        role=role,
        content=content,
        turn_index=get_next_conversation_turn_index(memory_state),
    )
    memory_state.recent_turns.append(turn)
    memory_state.compaction_metadata["last_turn_index"] = turn.turn_index
    return turn


def query_mentions_notes(query: str) -> bool:
    """Return whether the query is explicitly note- or lecture-oriented."""
    normalized_query = query.casefold()
    return any(
        keyword in normalized_query
        for keyword in ("notes", "lecture", "lectures", "homework", "midterm", "final", "exam")
    )


def query_mentions_exam_trap(query: str, answer: str = "") -> bool:
    """Return whether the exchange is discussing a trap or pitfall."""
    combined_text = f"{query}\n{answer}".casefold()
    return any(
        keyword in combined_text
        for keyword in ("trap", "pitfall", "mistake", "common error", "watch out")
    )


def query_mentions_solution_strategy(query: str, answer: str = "") -> bool:
    """Return whether the exchange is solution- or strategy-oriented."""
    combined_text = f"{query}\n{answer}".casefold()
    return any(
        keyword in combined_text
        for keyword in ("solve", "solution", "strategy", "approach", "proof", "argument")
    )


def has_referential_language(query: str) -> bool:
    """Return whether the query appears to depend on prior conversational context."""
    normalized_query = query.casefold()
    return any(pattern in normalized_query for pattern in REFERENTIAL_QUERY_PATTERNS)


def infer_preferred_entity_types(query: str) -> list[str]:
    """Map a follow-up query to the most likely entity types it references."""
    normalized_query = query.casefold()
    if any(keyword in normalized_query for keyword in ("solve", "solution", "check my answer")):
        return ["generated_problem", "solution_strategy", "source_section"]
    if any(keyword in normalized_query for keyword in ("trap", "pitfall", "remember")):
        return ["exam_trap", "explained_concept", "solution_strategy"]
    if any(keyword in normalized_query for keyword in ("relate", "topic", "concept", "behind that")):
        return ["explained_concept", "exam_trap", "notes_topic", "source_section"]
    if any(keyword in normalized_query for keyword in ("notes", "lecture", "homework", "where did that come from")):
        return ["source_section", "notes_topic", "generated_problem"]
    if any(keyword in normalized_query for keyword in ("explain", "understand", "why is that true", "that part")):
        return ["explained_concept", "solution_strategy", "source_section", "generated_problem"]
    return ["explained_concept", "notes_topic", "generated_problem", "exam_trap", "source_section"]


def deduplicate_conversation_entities(
    entities: list[ConversationEntity],
) -> list[ConversationEntity]:
    """Keep only the newest version of each entity id while preserving order."""
    newest_entities_by_id: dict[str, ConversationEntity] = {}
    for entity in entities:
        newest_entities_by_id[entity.entity_id] = entity

    deduplicated_entities: list[ConversationEntity] = []
    seen_entity_ids: set[str] = set()
    for entity in entities:
        newest_entity = newest_entities_by_id[entity.entity_id]
        if newest_entity.entity_id in seen_entity_ids:
            continue
        deduplicated_entities.append(newest_entity)
        seen_entity_ids.add(newest_entity.entity_id)

    return deduplicated_entities[-MAX_TRACKED_CONVERSATION_ENTITIES:]


def deduplicate_summary_values(values: list[str]) -> list[str]:
    """Return unique summary values in insertion order."""
    ordered_values: list[str] = []
    seen_values: set[str] = set()
    for value in values:
        normalized_value = value.strip()
        if not normalized_value or normalized_value in seen_values:
            continue
        ordered_values.append(normalized_value)
        seen_values.add(normalized_value)
    return ordered_values


def build_active_references_from_entities(
    entities: list[ConversationEntity],
) -> list[ConversationReferenceState]:
    """Project the newest tracked entities into the active-reference list."""
    active_references: list[ConversationReferenceState] = []
    seen_entity_types: set[str] = set()
    for entity in reversed(entities):
        if entity.entity_type in seen_entity_types:
            continue
        active_references.append(
            ConversationReferenceState(
                entity_id=entity.entity_id,
                entity_type=entity.entity_type,
                label=entity.label,
                source_turn_index=entity.source_turn_index,
                reason="recent entity",
            )
        )
        seen_entity_types.add(entity.entity_type)
        if len(active_references) >= MAX_ACTIVE_REFERENCES:
            break
    return active_references


def merge_compacted_summary_with_entities(
    compacted_summary: dict[str, list[str] | str],
    entities: list[ConversationEntity],
    archived_turns: list[ConversationTurn],
) -> dict[str, list[str] | str]:
    """Merge archived turns and entities into the structured compacted summary."""
    merged_summary = build_empty_conversation_summary()
    for field_name, field_value in compacted_summary.items():
        if isinstance(field_value, list):
            merged_summary[field_name] = list(field_value)
        else:
            merged_summary[field_name] = field_value

    entity_type_to_summary_field = {
        "explained_concept": "explained_concepts",
        "notes_topic": "notes_topics",
        "exam_trap": "exam_traps",
        "generated_problem": "generated_problems",
        "solution_strategy": "solution_strategies",
        "source_section": "source_sections",
    }

    for entity in entities:
        summary_field = entity_type_to_summary_field.get(entity.entity_type)
        if summary_field is None:
            continue
        summary_values = list(merged_summary.get(summary_field, []))
        summary_values.append(entity.label)
        if entity.entity_type == "generated_problem":
            summary_values[-1] = f"{entity.label} [{entity.status}]"
        merged_summary[summary_field] = deduplicate_summary_values(summary_values)

    archived_user_turns = [turn for turn in archived_turns if turn.role == "user"]
    if archived_user_turns:
        user_goal_values = list(merged_summary.get("user_goals", []))
        user_goal_values.extend(
            infer_query_topic_label(turn.content) for turn in archived_user_turns[-3:]
        )
        merged_summary["user_goals"] = deduplicate_summary_values(user_goal_values)
        merged_summary["last_compacted_user_message"] = shorten_text_excerpt(
            archived_user_turns[-1].content,
            160,
        )

    return merged_summary


def compact_conversation_memory(
    memory_state: ConversationMemoryState,
    maximum_token_budget: int = APPROX_CONTEXT_COMPACTION_TOKENS,
) -> None:
    """Compact older raw turns into structured summary state when memory grows too large."""
    estimated_tokens = estimate_conversation_memory_tokens(memory_state)
    memory_state.compaction_metadata["estimated_tokens"] = estimated_tokens
    if estimated_tokens < maximum_token_budget:
        return

    if len(memory_state.recent_turns) <= COMPACTION_RECENT_TURN_COUNT:
        return

    archived_turns = memory_state.recent_turns[:-COMPACTION_RECENT_TURN_COUNT]
    archived_turn_indexes = {turn.turn_index for turn in archived_turns}
    keep_turns = memory_state.recent_turns[-COMPACTION_RECENT_TURN_COUNT:]

    archived_entities = [
        entity
        for entity in memory_state.conversation_entities
        if entity.source_turn_index in archived_turn_indexes
    ]
    retained_entities = [
        entity
        for entity in memory_state.conversation_entities
        if entity.source_turn_index not in archived_turn_indexes
    ]

    memory_state.compacted_summary = merge_compacted_summary_with_entities(
        memory_state.compacted_summary,
        archived_entities,
        archived_turns,
    )
    memory_state.recent_turns = keep_turns
    memory_state.conversation_entities = deduplicate_conversation_entities(retained_entities)
    memory_state.active_references = build_active_references_from_entities(
        memory_state.conversation_entities
    )
    memory_state.compaction_metadata["compaction_count"] = int(
        memory_state.compaction_metadata.get("compaction_count", 0) or 0
    ) + 1
    memory_state.compaction_metadata["last_compacted_turn"] = archived_turns[-1].turn_index
    memory_state.compaction_metadata["estimated_tokens"] = (
        estimate_conversation_memory_tokens(memory_state)
    )


def extract_entities_from_exchange(
    query: str,
    answer: str,
    retrieval_result,
    assistant_turn_index: int,
) -> list[ConversationEntity]:
    """Infer tracked conversational entities from one assistant response."""
    extracted_entities: list[ConversationEntity] = []
    related_hints: list[str] = []

    for wiki_page_hit in retrieval_result.wiki_page_hits[:2]:
        related_hints.append(wiki_page_hit.title)
        extracted_entities.append(
            build_conversation_entity(
                entity_type="notes_topic" if query_mentions_notes(query) else "explained_concept",
                label=wiki_page_hit.title,
                canonical_text=wiki_page_hit.summary or wiki_page_hit.body,
                source_turn_index=assistant_turn_index,
                related_hints=[wiki_page_hit.source_path, wiki_page_hit.section],
            )
        )

    for chunk_hit in retrieval_result.chunk_hits[:2]:
        if not chunk_hit.section and not chunk_hit.title:
            continue
        label = chunk_hit.section or chunk_hit.title
        extracted_entities.append(
            build_conversation_entity(
                entity_type="source_section",
                label=label,
                canonical_text=chunk_hit.text,
                source_turn_index=assistant_turn_index,
                related_hints=[chunk_hit.title, chunk_hit.source_path],
            )
        )

    topic_label = infer_query_topic_label(query)
    if not retrieval_result.wiki_page_hits and any(
        keyword in query.casefold()
        for keyword in ("explain", "concept", "notes", "summary", "summarize", "trap")
    ):
        extracted_entities.append(
            build_conversation_entity(
                entity_type="notes_topic" if query_mentions_notes(query) else "explained_concept",
                label=topic_label,
                canonical_text=answer,
                source_turn_index=assistant_turn_index,
                related_hints=related_hints,
            )
        )

    if query_mentions_exam_trap(query, answer):
        extracted_entities.append(
            build_conversation_entity(
                entity_type="exam_trap",
                label=f"Exam trap: {topic_label}",
                canonical_text=answer,
                source_turn_index=assistant_turn_index,
                related_hints=related_hints,
            )
        )

    if query_mentions_solution_strategy(query, answer):
        extracted_entities.append(
            build_conversation_entity(
                entity_type="solution_strategy",
                label=f"Strategy: {topic_label}",
                canonical_text=answer,
                source_turn_index=assistant_turn_index,
                related_hints=related_hints,
            )
        )

    if "question" in query.casefold() and "practice" in query.casefold():
        extracted_entities.append(
            build_conversation_entity(
                entity_type="generated_problem",
                label=f"Generated problem: {topic_label}",
                canonical_text=answer,
                source_turn_index=assistant_turn_index,
                related_hints=related_hints,
                status="solution_pending",
            )
        )

    return deduplicate_conversation_entities(extracted_entities)


def resolve_follow_up_query(
    query: str,
    memory_state: ConversationMemoryState,
) -> QueryResolution:
    """Resolve ambiguous follow-up queries against stored conversation memory."""
    if not has_referential_language(query):
        return QueryResolution(
            resolved_query_text=query,
            resolved_reference_entities=[],
            resolution_confidence="high",
            is_follow_up=False,
        )

    preferred_entity_types = infer_preferred_entity_types(query)
    active_entity_ids = {reference.entity_id for reference in memory_state.active_references}
    candidate_entities = [
        entity
        for entity in reversed(memory_state.conversation_entities)
        if entity.entity_id in active_entity_ids or not active_entity_ids
    ]
    if not candidate_entities:
        candidate_entities = list(reversed(memory_state.conversation_entities))

    for preferred_entity_type in preferred_entity_types:
        for candidate_entity in candidate_entities:
            if candidate_entity.entity_type != preferred_entity_type:
                continue
            resolved_query_text = (
                f"{query}\n\nConversation target:\n"
                f"- Type: {candidate_entity.entity_type}\n"
                f"- Label: {candidate_entity.label}\n"
                f"- Context: {candidate_entity.canonical_text}"
            )
            return QueryResolution(
                resolved_query_text=resolved_query_text,
                resolved_reference_entities=[candidate_entity],
                resolution_confidence="high",
                is_follow_up=True,
            )

    unresolved_reason = "Follow-up target is unclear from current session memory."
    return QueryResolution(
        resolved_query_text=query,
        resolved_reference_entities=[],
        resolution_confidence="low",
        is_follow_up=True,
        unresolved_reason=unresolved_reason,
    )


def update_memory_after_exchange(
    memory_state: ConversationMemoryState,
    query: str,
    answer: str,
    retrieval_result,
    resolution: QueryResolution,
) -> None:
    """Record a successful user/assistant exchange into session memory."""
    store_conversation_turn(memory_state, "user", query)
    assistant_turn = store_conversation_turn(memory_state, "assistant", answer)
    new_entities = extract_entities_from_exchange(
        query,
        answer,
        retrieval_result,
        assistant_turn.turn_index,
    )
    memory_state.conversation_entities = deduplicate_conversation_entities(
        memory_state.conversation_entities + new_entities
    )
    memory_state.active_references = build_active_references_from_entities(
        memory_state.conversation_entities
    )
    if resolution.unresolved_reason:
        memory_state.compaction_metadata["latest_unresolved_follow_up"] = (
            resolution.unresolved_reason
        )
    else:
        memory_state.compaction_metadata["latest_unresolved_follow_up"] = ""
    memory_state.compaction_metadata["estimated_tokens"] = (
        estimate_conversation_memory_tokens(memory_state)
    )
    compact_conversation_memory(memory_state)


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


def humanize_course_folder_name(course_folder_name: str) -> str:
    """Convert `cmsc_27100` into `CMSC 27100` for small UI labels."""
    folder_segments = course_folder_name.split("_", maxsplit=1)
    if len(folder_segments) != 2:
        return course_folder_name.replace("_", " ").upper()

    course_category, course_number = folder_segments
    return f"{course_category.upper()} {course_number}"


def list_markdown_course_folder_names() -> list[str]:
    """Return sorted display names for top-level course folders under `data/md`."""
    markdown_root_path = REPOSITORY_ROOT / MARKDOWN_UPLOAD_DIRECTORY
    if not markdown_root_path.is_dir():
        return []

    display_names: list[str] = []
    for course_folder_path in sorted(markdown_root_path.iterdir()):
        if not course_folder_path.is_dir():
            continue
        display_names.append(humanize_course_folder_name(course_folder_path.name))
    return display_names


def render_html_fragment(html_fragment: str) -> None:
    """Render raw HTML without Markdown code-block indentation issues."""
    if hasattr(st, "html"):
        st.html(html_fragment)
        return
    st.markdown(html_fragment, unsafe_allow_html=True)


def inject_application_theme() -> None:
    """Apply the requested monospace blue theme to the Streamlit app."""
    render_html_fragment(
        f"""<style>
html, body, [class*="css"], [data-testid="stAppViewContainer"], [data-testid="stMarkdownContainer"], [data-testid="stChatMessageContent"], input, textarea, button, select {{
    font-family: {MONOSPACE_FONT_FAMILY};
}}

[data-testid="stAppViewContainer"] {{
    color: {PRIMARY_BLUE_COLOR};
    background: {APP_BACKGROUND_COLOR};
}}

[data-testid="stAppViewContainer"] h1,
[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3,
[data-testid="stAppViewContainer"] label,
[data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"],
[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] span {{
    color: {DARK_BLUE_ACCENT_COLOR};
}}

[data-testid="stSidebar"] {{
    background: {SIDEBAR_BACKGROUND_COLOR};
}}

[data-testid="stSidebar"] * {{
    color: {SIDEBAR_TEXT_COLOR};
}}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] code,
[data-testid="stSidebar"] code,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {{
    color: {SIDEBAR_TEXT_COLOR};
}}

[data-testid="stSidebar"] button,
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div,
[data-testid="stSidebar"] [data-baseweb="textarea"] {{
    border-color: {SIDEBAR_TEXT_COLOR};
}}

.jenrag-caption-ticker {{
    position: relative;
    overflow: hidden;
    width: min(100%, 48rem);
    margin-top: -0.5rem;
    margin-bottom: 1rem;
    font-size: 0.7rem;
    letter-spacing: 0.04em;
    color: {PRIMARY_BLUE_COLOR};
    white-space: nowrap;
}}

.jenrag-caption-ticker::before,
.jenrag-caption-ticker::after {{
    content: "";
    position: absolute;
    top: 0;
    width: 3rem;
    height: 100%;
    z-index: 1;
}}

.jenrag-caption-ticker::before {{
    left: 0;
    background: linear-gradient(to right, {APP_BACKGROUND_COLOR} 20%, transparent);
}}

.jenrag-caption-ticker::after {{
    right: 0;
    background: linear-gradient(to left, {APP_BACKGROUND_COLOR} 20%, transparent);
}}

.jenrag-caption-track {{
    display: inline-flex;
    min-width: max-content;
    gap: 1.5rem;
    animation: jenrag-scroll-left 18s linear infinite;
}}

@keyframes jenrag-scroll-left {{
    from {{
        transform: translateX(0);
    }}
    to {{
        transform: translateX(-50%);
    }}
}}

/* Chat composer: reserve room so newest message stays visible above pinned input. */
[data-testid="stAppViewBlockContainer"] {{
    padding-bottom: {CHAT_COMPOSER_CONTENT_PADDING};
}}

[data-testid="stChatInput"] {{
    position: fixed !important;
    left: var(--jenrag-chat-composer-left, {CHAT_COMPOSER_VIEWPORT_MARGIN});
    bottom: 0;
    transform: none;
    width: var(--jenrag-chat-composer-width, calc(100vw - ({CHAT_COMPOSER_VIEWPORT_MARGIN} * 2)));
    max-width: calc(100vw - ({CHAT_COMPOSER_VIEWPORT_MARGIN} * 2));
    z-index: 30;
    padding-top: 0.25rem;
    padding-bottom: {CHAT_COMPOSER_BOTTOM_OFFSET};
    background: linear-gradient(
        to top,
        rgba(14, 22, 41, 0.98) 0%,
        rgba(14, 22, 41, 0.92) 72%,
        rgba(14, 22, 41, 0) 100%
    );
}}

[data-testid="stChatInput"] > div {{
    background: {APP_BACKGROUND_COLOR};
    border: 1px solid {PRIMARY_BLUE_COLOR};
    border-radius: 0.75rem;
    box-shadow: 0 0 0 1px rgba(184, 196, 255, 0.12);
    min-height: {CHAT_COMPOSER_MIN_HEIGHT};
}}

[data-testid="stChatInput"] textarea {{
    min-height: 1.5rem;
    padding-top: 0.65rem;
    padding-bottom: 0.65rem;
}}
</style>
<script>
(() => {{
    const viewportMarginPixels = 16;
    const rootElement = document.documentElement;
    const layoutPollIntervalMilliseconds = 150;
    const contentSelectors = [
        '[data-testid="stMain"]',
        '[data-testid="stMainBlockContainer"]',
        'section[data-testid="stMain"]',
        '[data-testid="stAppViewBlockContainer"]',
    ];
    const sidebarSelectors = [
        '[data-testid="stSidebar"]',
        'section[data-testid="stSidebar"]',
        '[data-testid="stSidebarContent"]',
        '[aria-expanded="true"][data-testid*="Sidebar"]',
        '[data-testid*="sidebar"]',
    ];

    function findContentElement() {{
        for (const selector of contentSelectors) {{
            const matchedElement = document.querySelector(selector);
            if (matchedElement) {{
                return matchedElement;
            }}
        }}

        return null;
    }}

    function getSidebarSafeLeft() {{
        let furthestSidebarRight = viewportMarginPixels;

        for (const selector of sidebarSelectors) {{
            const sidebarElements = document.querySelectorAll(selector);
            for (const sidebarElement of sidebarElements) {{
                const sidebarRect = sidebarElement.getBoundingClientRect();
                const sidebarVisibleWidth = Math.max(
                    0,
                    sidebarRect.right - sidebarRect.left,
                );
                const sidebarVisibleHeight = Math.max(
                    0,
                    sidebarRect.bottom - sidebarRect.top,
                );
                const sidebarLooksVisible =
                    sidebarVisibleWidth > 48 &&
                    sidebarVisibleHeight > 120 &&
                    sidebarRect.left < window.innerWidth * 0.4;

                if (!sidebarLooksVisible) {{
                    continue;
                }}

                furthestSidebarRight = Math.max(
                    furthestSidebarRight,
                    sidebarRect.right + viewportMarginPixels,
                );
            }}
        }}

        return furthestSidebarRight;
    }}

    function updateChatComposerLayout() {{
        const contentElement = findContentElement();
        if (!contentElement) {{
            return;
        }}

        const contentRect = contentElement.getBoundingClientRect();
        const sidebarSafeLeft = getSidebarSafeLeft();

        const safeLeft = Math.max(
            viewportMarginPixels,
            contentRect.left,
            sidebarSafeLeft,
        );
        const safeRight = Math.min(
            window.innerWidth - viewportMarginPixels,
            contentRect.right,
        );
        const safeWidth = Math.max(0, safeRight - safeLeft);

        rootElement.style.setProperty(
            "--jenrag-chat-composer-left",
            `${{safeLeft}}px`,
        );
        rootElement.style.setProperty(
            "--jenrag-chat-composer-width",
            `${{safeWidth}}px`,
        );
    }}

    window.__jenragChatComposerCleanup?.();

    const resizeObserver = new ResizeObserver(() => {{
        updateChatComposerLayout();
    }});

    const mutationObserver = new MutationObserver(() => {{
        updateChatComposerLayout();
    }});

    resizeObserver.observe(document.body);
    for (const selector of sidebarSelectors) {{
        const sidebarElements = document.querySelectorAll(selector);
        for (const sidebarElement of sidebarElements) {{
            resizeObserver.observe(sidebarElement);
        }}
    }}
    mutationObserver.observe(document.body, {{
        attributes: true,
        childList: true,
        subtree: true,
    }});
    window.addEventListener("resize", updateChatComposerLayout);
    const layoutPollIntervalId = window.setInterval(
        updateChatComposerLayout,
        layoutPollIntervalMilliseconds,
    );
    updateChatComposerLayout();

    window.__jenragChatComposerCleanup = () => {{
        resizeObserver.disconnect();
        mutationObserver.disconnect();
        window.removeEventListener("resize", updateChatComposerLayout);
        window.clearInterval(layoutPollIntervalId);
    }};
}})();
</script>"""
    )


def render_application_header() -> None:
    """Render title plus small horizontal-scrolling course caption."""
    st.title("JenRAG")

    markdown_course_folder_names = list_markdown_course_folder_names()
    if not markdown_course_folder_names:
        return

    scrolling_caption = "  •  ".join(markdown_course_folder_names)
    repeated_scrolling_caption = "  •  ".join(
        [scrolling_caption, scrolling_caption]
    )
    render_html_fragment(
        '<div class="jenrag-caption-ticker" aria-label="Available course folders">'
        f'<div class="jenrag-caption-track">{repeated_scrolling_caption}</div>'
        "</div>"
    )


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
        if configuration_value_is_missing(setting_value):
            missing_settings.append(setting_name)
    return missing_settings


def configuration_value_is_missing(setting_value: object) -> bool:
    """Return True when a config value is empty or placeholder-like."""
    if setting_value is None:
        return True

    normalized_value = str(setting_value).strip().lower()
    return normalized_value in MISSING_CONFIGURATION_SENTINELS


def build_github_upload_client() -> GitHubUploadClient:
    """Return a validated GitHub upload client or raise a clear config error."""
    missing_settings = get_missing_upload_configuration()
    if missing_settings:
        raise GitHubUploadError(
            "Upload feature is disabled until these secrets are configured: "
            + ", ".join(missing_settings)
        )

    return GitHubUploadClient(
        repository=str(GITHUB_REPOSITORY).strip(),
        token=str(GITHUB_UPLOAD_TOKEN).strip(),
        base_branch=str(GITHUB_BASE_BRANCH),
        api_base_url=str(GITHUB_API_BASE_URL),
    )


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


def run_pipeline(
    query: str,
    conversation_memory_state: ConversationMemoryState | None,
    use_reranker: bool,
    rerank_top_k: int,
) -> dict:
    """Run the full RAG pipeline and return results with timing."""
    timings = {}
    if conversation_memory_state is None:
        conversation_memory_state = get_conversation_memory_state()
    query_resolution = resolve_follow_up_query(query, conversation_memory_state)

    retrieval_start_time = time.time()
    retrieval_result = retrieve(
        query_resolution.resolved_query_text,
        rerank_top_k=rerank_top_k,
        use_reranker=use_reranker,
    )
    timings["retrieval"] = time.time() - retrieval_start_time

    generation_start_time = time.time()
    conversation_memory_prompt_context = build_conversation_memory_prompt_context(
        conversation_memory_state,
        query_resolution,
    )
    try:
        answer = generate(
            query,
            retrieval_result,
            conversation_memory_context=conversation_memory_prompt_context,
        )
    except TypeError as error:
        if "conversation_memory_context" not in str(error):
            raise
        answer = generate(query, retrieval_result)
    timings["generation"] = time.time() - generation_start_time

    timings["total"] = timings["retrieval"] + timings["generation"]

    return {
        "answer": answer,
        "retrieval": retrieval_result,
        "timings": timings,
        "resolution": query_resolution,
    }


def render_conversation_memory_panel(
    memory_state: ConversationMemoryState,
) -> None:
    """Render a compact diagnostic summary of conversation memory state."""
    compaction_count = int(memory_state.compaction_metadata.get("compaction_count", 0) or 0)
    active_reference_label = (
        memory_state.active_references[0].label
        if memory_state.active_references
        else "none"
    )
    latest_unresolved_follow_up = str(
        memory_state.compaction_metadata.get("latest_unresolved_follow_up", "")
    ).strip() or "none"
    estimated_tokens = int(memory_state.compaction_metadata.get("estimated_tokens", 0) or 0)

    st.markdown("**Conversation Memory**")
    st.caption(
        "Active: "
        + ("yes" if memory_state.recent_turns or memory_state.conversation_entities else "no")
    )
    st.caption(f"Compactions: {compaction_count}")
    st.caption(f"Active reference: {active_reference_label}")
    st.caption(f"Tracked entities: {len(memory_state.conversation_entities)}")
    st.caption(f"Approx tokens: {estimated_tokens}/{APPROX_MAX_CONTEXT_TOKENS}")
    st.caption(f"Unresolved follow-up: {latest_unresolved_follow_up}")


def build_sidebar_wiki_graph_hover_title(title: str, page_type: str) -> str:
    """Return a short hover title that better matches node content."""
    normalized_title = " ".join(title.split())
    if not normalized_title:
        return ""

    title_segments = [
        segment.strip()
        for segment in re.split(r"\s+[—:-]\s+", normalized_title)
        if segment.strip()
    ]
    generic_segment_pattern = re.compile(
        r"^(section|chapter|part|problem|question|lecture|notes?|document)"
        r"(\s+[a-z0-9ivx.-]+)?$",
        re.IGNORECASE,
    )

    candidate_title = normalized_title
    for title_segment in reversed(title_segments):
        if generic_segment_pattern.fullmatch(title_segment):
            continue
        candidate_title = title_segment
        break
    else:
        if title_segments:
            candidate_title = title_segments[0]

    if len(candidate_title) <= SIDEBAR_WIKI_GRAPH_MAX_HOVER_CHARACTERS:
        return candidate_title

    shortened_title = " ".join(
        candidate_title.split()[:SIDEBAR_WIKI_GRAPH_MAX_HOVER_WORDS]
    ).strip()
    if len(shortened_title) > SIDEBAR_WIKI_GRAPH_MAX_HOVER_CHARACTERS:
        shortened_title = shortened_title[
            :SIDEBAR_WIKI_GRAPH_MAX_HOVER_CHARACTERS
        ].rstrip()

    if shortened_title and len(shortened_title) < len(candidate_title):
        return shortened_title + "..."

    if page_type.strip():
        return candidate_title[:SIDEBAR_WIKI_GRAPH_MAX_HOVER_CHARACTERS].rstrip() + "..."
    return candidate_title


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

    primary_match_slug = ""
    for wiki_page_hit in retrieval_result.wiki_page_hits:
        if wiki_page_hit.slug:
            primary_match_slug = wiki_page_hit.slug
            break

    return {
        "nodes": [
            {
                "slug": graph_node.slug,
                "title": graph_node.title,
                "hover_title": build_sidebar_wiki_graph_hover_title(
                    graph_node.title,
                    graph_node.page_type,
                ),
                "page_type": graph_node.page_type,
                "is_seed": graph_node.is_seed,
                "is_primary_match": graph_node.slug == primary_match_slug,
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
        st.caption(
            "Wiki sidecar: available" if wiki_database_available else "Wiki sidecar: unavailable"
        )
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
            if graph_node_payload.get("is_primary_match"):
                node_color = SIDEBAR_WIKI_GRAPH_PRIMARY_NODE_COLOR
            elif graph_node_payload["is_seed"]:
                node_color = SIDEBAR_WIKI_GRAPH_SEED_COLOR
            else:
                node_color = SIDEBAR_WIKI_GRAPH_RELATED_COLOR
            graph_nodes.append(
                Node(
                    id=graph_node_payload["slug"],
                    label="",
                    title=str(
                        graph_node_payload.get(
                            "hover_title",
                            build_sidebar_wiki_graph_hover_title(
                                str(graph_node_payload["title"]),
                                str(graph_node_payload["page_type"]),
                            ),
                        )
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
    conversation_memory_state = get_conversation_memory_state()
    with st.sidebar:
        st.header("Pipeline Settings")
        use_reranker = st.toggle("Enable reranker", value=True)
        rerank_top_k = st.slider("Chunks to keep after reranking", 3, 15, 5)
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state[CONVERSATION_MEMORY_STATE_KEY] = (
                build_initial_conversation_memory_state()
            )
            st.session_state.pop(SIDEBAR_WIKI_GRAPH_STATE_KEY, None)
            st.session_state.pop(SIDEBAR_WIKI_GRAPH_SELECTION_KEY, None)
            st.rerun()
        st.divider()
        render_conversation_memory_panel(conversation_memory_state)
        st.divider()
        wiki_database_available = wiki_database_exists(WIKI_DB_PATH)
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
    conversation_memory_state = get_conversation_memory_state()

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

    query = st.chat_input("Ask about homework, exam problems, solutions, notes, and concepts...")
    if not query:
        return

    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Retrieving and generating..."):
                result = run_pipeline(
                    query,
                    conversation_memory_state,
                    use_reranker,
                    rerank_top_k,
                )
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
        update_memory_after_exchange(
            conversation_memory_state,
            query,
            result["answer"],
            result["retrieval"],
            result.get(
                "resolution",
                QueryResolution(
                    resolved_query_text=query,
                    resolved_reference_entities=[],
                    resolution_confidence="high",
                    is_follow_up=False,
                ),
            ),
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

    try:
        github_client = build_github_upload_client()
    except GitHubUploadError as error:
        st.error(str(error))
        return

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
    inject_application_theme()
    render_application_header()

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
