"""Status endpoint for site generation tasks."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from civitas.api.deps import get_db
from civitas.api.schemas import SiteGenerationStatus
from civitas.db.models import (
    ContentInsight,
    CourtCase,
    ExecutiveOrder,
    Justice,
    JusticeProfile,
    Legislation,
    Project2025Policy,
    ResistanceAnalysis,
)

router = APIRouter()


@router.get("/status", response_model=SiteGenerationStatus)
def site_generation_status(db: Session = Depends(get_db)) -> SiteGenerationStatus:
    """Return site generation progress and last-run timestamps."""
    objectives_total = db.query(func.count(Project2025Policy.id)).scalar() or 0
    objectives_titled = (
        db.query(func.count(Project2025Policy.id))
        .filter(Project2025Policy.short_title.isnot(None))
        .filter(Project2025Policy.short_title != "")
        .scalar()
        or 0
    )
    objectives_with_insights = (
        db.query(func.count(ContentInsight.id))
        .filter(ContentInsight.content_type == "objective")
        .scalar()
        or 0
    )
    expert_analyses = db.query(func.count(ResistanceAnalysis.id)).scalar() or 0

    justices_total = db.query(func.count(Justice.id)).scalar() or 0
    justices_active = (
        db.query(func.count(Justice.id)).filter(Justice.is_active.is_(True)).scalar() or 0
    )
    justice_profiles = db.query(func.count(JusticeProfile.id)).scalar() or 0

    executive_orders_total = db.query(func.count(ExecutiveOrder.id)).scalar() or 0
    cases_total = db.query(func.count(CourtCase.id)).scalar() or 0
    legislation_total = db.query(func.count(Legislation.id)).scalar() or 0

    insights_last_generated_at = db.query(func.max(ContentInsight.generated_at)).scalar()
    expert_last_generated_at = db.query(func.max(ResistanceAnalysis.generated_at)).scalar()
    justice_profiles_last_generated_at = db.query(func.max(JusticeProfile.generated_at)).scalar()

    def pct(part: int, total: int) -> float:
        return round((part / total) * 100, 2) if total else 0.0

    return SiteGenerationStatus(
        generated_at=datetime.now(UTC),
        objectives_total=objectives_total,
        objectives_titled=objectives_titled,
        objectives_title_pct=pct(objectives_titled, objectives_total),
        objectives_with_insights=objectives_with_insights,
        objectives_insight_pct=pct(objectives_with_insights, objectives_total),
        expert_analyses=expert_analyses,
        expert_analyses_pct=pct(expert_analyses, objectives_total),
        expert_last_generated_at=expert_last_generated_at,
        insights_last_generated_at=insights_last_generated_at,
        justices_total=justices_total,
        justices_active=justices_active,
        justice_profiles=justice_profiles,
        justice_profiles_pct=pct(justice_profiles, justices_active),
        justice_profiles_last_generated_at=justice_profiles_last_generated_at,
        executive_orders_total=executive_orders_total,
        cases_total=cases_total,
        legislation_total=legislation_total,
    )
