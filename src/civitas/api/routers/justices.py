"""Supreme Court justices API endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from civitas.api.schemas import JusticeBase, JusticeDetail, JusticeList
from civitas.db.models import Justice, JusticeOpinion, JusticeProfile

router = APIRouter()


def get_db(request: Request) -> Session:
    """Get database session."""
    return Session(request.app.state.engine)


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _parse_json_object(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


@router.get("/justices", response_model=JusticeList)
async def list_justices(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
) -> JusticeList:
    """List Supreme Court justices."""
    query = db.query(Justice)
    if active_only:
        query = query.filter(Justice.is_active.is_(True))

    total = query.count()
    offset = (page - 1) * per_page
    items = (
        query.order_by(Justice.is_active.desc(), Justice.last_name.asc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return JusticeList(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=(total + per_page - 1) // per_page,
        items=[JusticeBase.model_validate(item) for item in items],
    )


@router.get("/justices/{slug}", response_model=JusticeDetail)
async def get_justice(
    slug: str,
    db: Session = Depends(get_db),
) -> JusticeDetail:
    """Get a justice by slug with profile data."""
    justice = db.query(Justice).filter(Justice.slug == slug).first()
    if not justice:
        raise HTTPException(status_code=404, detail="Justice not found")

    profile = (
        db.query(JusticeProfile)
        .filter(JusticeProfile.justice_id == justice.id)
        .first()
    )

    counts = {
        "majority": db.query(JusticeOpinion)
        .filter(
            JusticeOpinion.justice_id == justice.id,
            JusticeOpinion.opinion_type == "majority",
        )
        .count(),
        "dissent": db.query(JusticeOpinion)
        .filter(
            JusticeOpinion.justice_id == justice.id,
            JusticeOpinion.opinion_type == "dissent",
        )
        .count(),
        "concurrence": db.query(JusticeOpinion)
        .filter(
            JusticeOpinion.justice_id == justice.id,
            JusticeOpinion.opinion_type == "concurrence",
        )
        .count(),
    }
    counts["total"] = counts["majority"] + counts["dissent"] + counts["concurrence"]

    base = JusticeBase.model_validate(justice)

    return JusticeDetail(
        **base.model_dump(),
        appointed_by=justice.appointed_by,
        official_bio_url=justice.official_bio_url,
        wikipedia_url=justice.wikipedia_url,
        opinion_counts=counts,
        profile_summary=profile.profile_summary if profile else None,
        judicial_philosophy=profile.judicial_philosophy if profile else None,
        voting_tendencies=_parse_json_list(profile.voting_tendencies) if profile else [],
        notable_opinions=_parse_json_list(profile.notable_opinions) if profile else [],
        statistical_profile=_parse_json_object(profile.statistical_profile) if profile else {},
        methodology=profile.methodology if profile else None,
        disclaimer=profile.disclaimer if profile else None,
        generated_at=profile.generated_at if profile else None,
    )
