"""Full-text search using SQLite FTS5.

This module provides fast full-text search across:
- Legislation (title, summary, full_text)
- Court Cases (case_name, holding, majority_opinion)
- Law Sections (title, content)

FTS5 supports:
- Boolean queries: "water AND conservation"
- Phrase queries: "climate change"
- Prefix queries: "environ*"
- Column filters: "title:water"
- Proximity: NEAR(word1 word2, 10)
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import CourtCase, LawSection, Legislation


def search_legislation(
    session: Session,
    query: str,
    jurisdiction: str | None = None,
    session_filter: str | None = None,
    enacted_only: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> list[Legislation]:
    """Search legislation using FTS5.

    Args:
        session: Database session
        query: FTS5 query string (supports boolean operators, phrases, etc.)
        jurisdiction: Filter by jurisdiction (e.g., "federal", "california")
        session_filter: Filter by legislative session (e.g., "118", "2023-2024")
        enacted_only: Only return enacted legislation
        limit: Maximum results to return
        offset: Number of results to skip

    Returns:
        List of matching Legislation objects, ordered by relevance

    Example queries:
        - "water conservation" (phrase)
        - "climate OR environment" (boolean OR)
        - "healthcare AND reform" (boolean AND)
        - "title:education" (column filter)
        - "hous*" (prefix match for "housing", "house", etc.)
    """
    # Build the FTS query
    sql = """
        SELECT l.id, bm25(legislation_fts) as score
        FROM legislation l
        JOIN legislation_fts fts ON l.id = fts.rowid
        WHERE legislation_fts MATCH :query
    """
    params = {"query": query, "limit": limit, "offset": offset}

    if jurisdiction:
        sql += " AND l.jurisdiction = :jurisdiction"
        params["jurisdiction"] = jurisdiction

    if session_filter:
        sql += " AND l.session = :session_filter"
        params["session_filter"] = session_filter

    if enacted_only:
        sql += " AND l.is_enacted = 1"

    sql += " ORDER BY score LIMIT :limit OFFSET :offset"

    result = session.execute(text(sql), params)
    ids = [row.id for row in result]

    if not ids:
        return []

    # Fetch full objects in the same order
    legislation = session.query(Legislation).filter(Legislation.id.in_(ids)).all()

    # Sort by original order (FTS ranking)
    id_order = {id_: idx for idx, id_ in enumerate(ids)}
    return sorted(legislation, key=lambda x: id_order.get(x.id, 999))


def search_court_cases(
    session: Session,
    query: str,
    court: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[CourtCase]:
    """Search court cases using FTS5.

    Args:
        session: Database session
        query: FTS5 query string
        court: Filter by court (e.g., "Supreme Court")
        limit: Maximum results to return
        offset: Number of results to skip

    Returns:
        List of matching CourtCase objects, ordered by relevance
    """
    sql = """
        SELECT c.id, bm25(court_cases_fts) as score
        FROM court_cases c
        JOIN court_cases_fts fts ON c.id = fts.rowid
        WHERE court_cases_fts MATCH :query
    """
    params = {"query": query, "limit": limit, "offset": offset}

    if court:
        sql += " AND c.court = :court"
        params["court"] = court

    sql += " ORDER BY score LIMIT :limit OFFSET :offset"

    result = session.execute(text(sql), params)
    ids = [row.id for row in result]

    if not ids:
        return []

    cases = session.query(CourtCase).filter(CourtCase.id.in_(ids)).all()
    id_order = {id_: idx for idx, id_ in enumerate(ids)}
    return sorted(cases, key=lambda x: id_order.get(x.id, 999))


def search_law_sections(
    session: Session,
    query: str,
    jurisdiction: str | None = None,
    code: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[LawSection]:
    """Search law sections using FTS5.

    Args:
        session: Database session
        query: FTS5 query string
        jurisdiction: Filter by jurisdiction
        code: Filter by law code (e.g., "GOV", "PRC")
        limit: Maximum results to return
        offset: Number of results to skip

    Returns:
        List of matching LawSection objects, ordered by relevance
    """
    sql = """
        SELECT ls.id, bm25(law_sections_fts) as score
        FROM law_sections ls
        JOIN law_sections_fts fts ON ls.id = fts.rowid
        JOIN law_codes lc ON ls.law_code_id = lc.id
        WHERE law_sections_fts MATCH :query
    """
    params = {"query": query, "limit": limit, "offset": offset}

    if jurisdiction:
        sql += " AND lc.jurisdiction = :jurisdiction"
        params["jurisdiction"] = jurisdiction

    if code:
        sql += " AND lc.code = :code"
        params["code"] = code

    sql += " ORDER BY score LIMIT :limit OFFSET :offset"

    result = session.execute(text(sql), params)
    ids = [row.id for row in result]

    if not ids:
        return []

    sections = session.query(LawSection).filter(LawSection.id.in_(ids)).all()
    id_order = {id_: idx for idx, id_ in enumerate(ids)}
    return sorted(sections, key=lambda x: id_order.get(x.id, 999))


def search_all(
    session: Session,
    query: str,
    limit: int = 10,
) -> dict:
    """Search across all content types.

    Args:
        session: Database session
        query: FTS5 query string
        limit: Maximum results per type

    Returns:
        Dictionary with keys: legislation, court_cases, law_sections
    """
    return {
        "legislation": search_legislation(session, query, limit=limit),
        "court_cases": search_court_cases(session, query, limit=limit),
        "law_sections": search_law_sections(session, query, limit=limit),
    }


def count_search_results(
    session: Session,
    query: str,
    table: str = "legislation",
) -> int:
    """Count total results for a search query.

    Args:
        session: Database session
        query: FTS5 query string
        table: Which table to search (legislation, court_cases, law_sections)

    Returns:
        Total count of matching documents
    """
    fts_table = f"{table}_fts"
    sql = f"SELECT COUNT(*) FROM {fts_table} WHERE {fts_table} MATCH :query"
    result = session.execute(text(sql), {"query": query})
    return result.scalar() or 0


def suggest_completions(
    session: Session,
    prefix: str,
    table: str = "legislation",
    limit: int = 10,
) -> list[str]:
    """Suggest search completions based on prefix.

    Uses FTS5 prefix queries to find matching terms.

    Args:
        session: Database session
        prefix: Prefix to complete (e.g., "environ" -> "environment", "environmental")
        table: Which table to search
        limit: Maximum suggestions

    Returns:
        List of suggested search terms
    """
    # FTS5 prefix query
    query = f"{prefix}*"
    fts_table = f"{table}_fts"

    if table == "legislation":
        sql = f"""
            SELECT DISTINCT title FROM {fts_table}
            WHERE {fts_table} MATCH :query
            LIMIT :limit
        """
    elif table == "court_cases":
        sql = f"""
            SELECT DISTINCT case_name FROM {fts_table}
            WHERE {fts_table} MATCH :query
            LIMIT :limit
        """
    else:
        sql = f"""
            SELECT DISTINCT title FROM {fts_table}
            WHERE {fts_table} MATCH :query
            LIMIT :limit
        """

    try:
        result = session.execute(text(sql), {"query": query, "limit": limit})
        return [row[0] for row in result if row[0]]
    except Exception:
        return []
