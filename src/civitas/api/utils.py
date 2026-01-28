"""API utility helpers."""

from __future__ import annotations

from civitas.api.schemas import ObjectiveBase
from civitas.db.models import Project2025Policy


def _normalize_objective_text(text: str | None) -> str:
    """Normalize proposal text to a single-line string."""
    if not text:
        return ""
    return " ".join(text.split())


def _select_objective_base(obj: Project2025Policy) -> str:
    """Pick the most useful objective text (summary if meaningful, else full text)."""
    summary = _normalize_objective_text(obj.proposal_summary)
    text = _normalize_objective_text(obj.proposal_text)
    if summary and len(summary) >= 24:
        return summary
    if text:
        return text
    return f"{obj.agency}: {obj.action_type}".strip()


def build_objective_title(obj: Project2025Policy, max_len: int = 140) -> str:
    """Return a short, readable title for a P2025 objective."""
    base = _select_objective_base(obj)

    if len(base) <= max_len:
        return base
    return f"{base[: max_len - 1].rstrip()}…"


def build_objective_full_title(obj: Project2025Policy) -> str:
    """Return the full, un-truncated objective title."""
    return _select_objective_base(obj)


def objective_to_base(obj: Project2025Policy) -> ObjectiveBase:
    """Build ObjectiveBase with computed title."""
    short_title = build_objective_title(obj)
    full_title = build_objective_full_title(obj)
    return ObjectiveBase(
        id=obj.id,
        section=obj.section,
        chapter=obj.chapter,
        agency=obj.agency,
        proposal_text=obj.proposal_text,
        proposal_summary=obj.proposal_summary,
        page_number=obj.page_number,
        category=obj.category,
        action_type=obj.action_type,
        priority=obj.priority,
        implementation_timeline=obj.implementation_timeline,
        status=obj.status,
        confidence=obj.confidence,
        title=short_title,
        title_short=short_title,
        title_full=full_title,
        updated_at=obj.updated_at,
    )
