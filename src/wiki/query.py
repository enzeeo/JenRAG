from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3

from src.pipeline.config import WIKI_DB_PATH, WIKI_TOP_K

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "use",
    "with",
}


@dataclass(frozen=True)
class WikiPageMatch:
    slug: str
    title: str
    page_type: str
    summary: str
    body: str
    course_key: str
    source_path: str
    source_title: str
    section: str
    aliases: list[str]
    score: int


@dataclass(frozen=True)
class RelatedTopicMatch:
    slug: str
    title: str
    relation: str


@dataclass(frozen=True)
class WikiGraphNode:
    slug: str
    title: str
    page_type: str
    is_seed: bool


@dataclass(frozen=True)
class WikiGraphEdge:
    from_slug: str
    to_slug: str
    relation: str


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in TOKEN_PATTERN.findall(text.lower())
        if len(token) > 2 and token not in STOP_WORDS
    }


def wiki_database_exists(database_path: str = WIKI_DB_PATH) -> bool:
    return Path(database_path).is_file()


def _load_page_aliases(connection: sqlite3.Connection) -> dict[str, list[str]]:
    page_aliases: dict[str, list[str]] = {}
    for page_slug, alias in connection.execute(
        "SELECT page_slug, alias FROM page_aliases ORDER BY page_slug, alias"
    ):
        page_aliases.setdefault(str(page_slug), []).append(str(alias))
    return page_aliases


def find_wiki_matches(
    query_text: str,
    chunk_source_paths: list[str],
    course_keys: list[str],
    database_path: str = WIKI_DB_PATH,
    top_k: int = WIKI_TOP_K,
) -> list[WikiPageMatch]:
    if not wiki_database_exists(database_path):
        return []

    query_tokens = tokenize(query_text)
    source_path_set = {path for path in chunk_source_paths if path}
    course_key_set = {course_key for course_key in course_keys if course_key}

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        aliases_by_slug = _load_page_aliases(connection)
        page_rows = connection.execute(
            """
            SELECT slug, title, page_type, summary, body, course_key, source_path, source_title, section
            FROM pages
            """
        ).fetchall()

    scored_matches: list[WikiPageMatch] = []
    for page_row in page_rows:
        aliases = aliases_by_slug.get(str(page_row["slug"]), [])
        searchable_text = " ".join(
            [
                str(page_row["title"]),
                str(page_row["summary"]),
                str(page_row["body"]),
                " ".join(aliases),
            ]
        )
        overlap_count = len(query_tokens & tokenize(searchable_text))

        score = 0
        if str(page_row["source_path"]) in source_path_set:
            score += 8
        if str(page_row["course_key"]) in course_key_set:
            score += 4
        score += overlap_count * 2

        if score <= 0:
            continue

        scored_matches.append(
            WikiPageMatch(
                slug=str(page_row["slug"]),
                title=str(page_row["title"]),
                page_type=str(page_row["page_type"]),
                summary=str(page_row["summary"]),
                body=str(page_row["body"]),
                course_key=str(page_row["course_key"]),
                source_path=str(page_row["source_path"]),
                source_title=str(page_row["source_title"]),
                section=str(page_row["section"]),
                aliases=aliases,
                score=score,
            )
        )

    scored_matches.sort(
        key=lambda match: (
            -match.score,
            match.page_type != "section",
            match.title.lower(),
        )
    )
    return scored_matches[:top_k]


def find_related_topics(
    page_slugs: list[str],
    database_path: str = WIKI_DB_PATH,
    top_k: int = WIKI_TOP_K,
) -> list[RelatedTopicMatch]:
    if not page_slugs or not wiki_database_exists(database_path):
        return []

    placeholder_list = ", ".join("?" for _ in page_slugs)
    with sqlite3.connect(database_path) as connection:
        related_rows = connection.execute(
            f"""
            SELECT DISTINCT pages.slug, pages.title, page_links.relation
            FROM page_links
            JOIN pages ON pages.slug = page_links.to_slug
            WHERE page_links.relation = 'related_topic'
              AND page_links.from_slug IN ({placeholder_list})
            ORDER BY pages.title
            """,
            page_slugs,
        ).fetchall()

    related_topics: list[RelatedTopicMatch] = []
    matched_page_slug_set = set(page_slugs)
    for slug, title, relation in related_rows:
        if str(slug) in matched_page_slug_set:
            continue
        related_topics.append(
            RelatedTopicMatch(
                slug=str(slug),
                title=str(title),
                relation=str(relation),
            )
        )
        if len(related_topics) >= top_k:
            break

    return related_topics


def load_wiki_graph_neighborhood(
    page_slugs: list[str],
    database_path: str = WIKI_DB_PATH,
    max_related_nodes_per_seed: int = 6,
) -> tuple[list[WikiGraphNode], list[WikiGraphEdge]]:
    if not page_slugs or not wiki_database_exists(database_path):
        return [], []

    ordered_seed_slugs: list[str] = []
    seen_seed_slugs: set[str] = set()
    for page_slug in page_slugs:
        normalized_slug = page_slug.strip()
        if not normalized_slug or normalized_slug in seen_seed_slugs:
            continue
        seen_seed_slugs.add(normalized_slug)
        ordered_seed_slugs.append(normalized_slug)

    if not ordered_seed_slugs:
        return [], []

    seed_placeholder_list = ", ".join("?" for _ in ordered_seed_slugs)
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row

        seed_page_rows = connection.execute(
            f"""
            SELECT slug, title, page_type
            FROM pages
            WHERE slug IN ({seed_placeholder_list})
            """,
            ordered_seed_slugs,
        ).fetchall()

        related_rows = connection.execute(
            f"""
            SELECT
                page_links.from_slug,
                page_links.to_slug,
                page_links.relation,
                pages.title,
                pages.page_type
            FROM page_links
            JOIN pages ON pages.slug = page_links.to_slug
            WHERE page_links.relation = 'related_topic'
              AND page_links.from_slug IN ({seed_placeholder_list})
            ORDER BY page_links.from_slug, pages.title
            """,
            ordered_seed_slugs,
        ).fetchall()

    ordered_node_slugs: list[str] = []
    page_rows_by_slug: dict[str, sqlite3.Row] = {}
    for seed_page_row in seed_page_rows:
        slug = str(seed_page_row["slug"])
        if slug in page_rows_by_slug:
            continue
        page_rows_by_slug[slug] = seed_page_row
        ordered_node_slugs.append(slug)

    graph_edges: list[WikiGraphEdge] = []
    seen_edge_keys: set[tuple[str, str, str]] = set()
    related_node_counts_by_seed: dict[str, int] = {
        seed_slug: 0 for seed_slug in ordered_seed_slugs
    }

    for related_row in related_rows:
        from_slug = str(related_row["from_slug"])
        to_slug = str(related_row["to_slug"])
        relation = str(related_row["relation"])

        if from_slug == to_slug:
            continue
        if related_node_counts_by_seed.get(from_slug, 0) >= max_related_nodes_per_seed:
            continue

        edge_key = (from_slug, to_slug, relation)
        if edge_key in seen_edge_keys:
            continue

        if to_slug not in page_rows_by_slug:
            page_rows_by_slug[to_slug] = related_row
            ordered_node_slugs.append(to_slug)

        graph_edges.append(
            WikiGraphEdge(
                from_slug=from_slug,
                to_slug=to_slug,
                relation=relation,
            )
        )
        seen_edge_keys.add(edge_key)
        related_node_counts_by_seed[from_slug] = (
            related_node_counts_by_seed.get(from_slug, 0) + 1
        )

    if ordered_node_slugs:
        node_placeholder_list = ", ".join("?" for _ in ordered_node_slugs)
        with sqlite3.connect(database_path) as connection:
            structural_rows = connection.execute(
                f"""
                SELECT from_slug, to_slug, relation
                FROM page_links
                WHERE relation != 'related_topic'
                  AND from_slug IN ({node_placeholder_list})
                  AND to_slug IN ({node_placeholder_list})
                ORDER BY from_slug, to_slug, relation
                """,
                ordered_node_slugs + ordered_node_slugs,
            ).fetchall()

        for from_slug, to_slug, relation in structural_rows:
            normalized_from_slug = str(from_slug)
            normalized_to_slug = str(to_slug)
            normalized_relation = str(relation)
            if normalized_from_slug == normalized_to_slug:
                continue

            edge_key = (
                normalized_from_slug,
                normalized_to_slug,
                normalized_relation,
            )
            if edge_key in seen_edge_keys:
                continue

            graph_edges.append(
                WikiGraphEdge(
                    from_slug=normalized_from_slug,
                    to_slug=normalized_to_slug,
                    relation=normalized_relation,
                )
            )
            seen_edge_keys.add(edge_key)

    graph_nodes: list[WikiGraphNode] = []
    seed_slug_set = set(ordered_seed_slugs)
    for node_slug in ordered_node_slugs:
        page_row = page_rows_by_slug[node_slug]
        graph_nodes.append(
            WikiGraphNode(
                slug=node_slug,
                title=str(page_row["title"]),
                page_type=str(page_row["page_type"]),
                is_seed=node_slug in seed_slug_set,
            )
        )

    return graph_nodes, graph_edges
