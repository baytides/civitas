"""API utility helpers."""

from __future__ import annotations

from civitas.api.schemas import ObjectiveBase
from civitas.db.models import Project2025Policy


def build_objective_title(obj: Project2025Policy, max_len: int = 140) -> str:
    """Return a short, readable title for a P2025 objective."""
    base = obj.proposal_summary or obj.proposal_text or ""
    base = " ".join(base.split())
    if not base:
        base = f"{obj.agency}: {obj.action_type}".strip()

    if len(base) <= max_len:
        return base
    return f"{base[: max_len - 1].rstrip()}…"


def objective_to_base(obj: Project2025Policy) -> ObjectiveBase:
    """Build ObjectiveBase with computed title."""
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
        title=build_objective_title(obj),
    )
