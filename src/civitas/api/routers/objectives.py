"""P2025 Objectives API endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from civitas.api.schemas import (
    ObjectiveBase,
    ObjectiveDetail,
    ObjectiveList,
    ObjectiveMetadata,
    ObjectiveStats,
)
from civitas.db.models import Project2025Policy

router = APIRouter()


def get_db(request: Request) -> Session:
    """Get database session."""
    return Session(request.app.state.engine)


@router.get("/objectives", response_model=ObjectiveList)
async def list_objectives(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: str | None = Query(None),
    status: str | None = Query(None),
    agency: str | None = Query(None),
    priority: str | None = Query(None),
    timeline: str | None = Query(None),
    db: Session = Depends(get_db),
) -> ObjectiveList:
    """List P2025 objectives with filtering and pagination."""
    query = db.query(Project2025Policy)

    # Apply filters
    if category:
        query = query.filter(Project2025Policy.category == category)
    if status:
        query = query.filter(Project2025Policy.status == status)
    if agency:
        query = query.filter(Project2025Policy.agency.ilike(f"%{agency}%"))
    if priority:
        query = query.filter(Project2025Policy.priority == priority)
    if timeline:
        query = query.filter(Project2025Policy.implementation_timeline == timeline)

    # Get total count
    total = query.count()

    # Paginate
    offset = (page - 1) * per_page
    items = query.order_by(Project2025Policy.id).offset(offset).limit(per_page).all()

    return ObjectiveList(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=(total + per_page - 1) // per_page,
        items=[ObjectiveBase.model_validate(item) for item in items],
    )


@router.get("/objectives/stats", response_model=ObjectiveStats)
async def get_objective_stats(
    db: Session = Depends(get_db),
) -> ObjectiveStats:
    """Get aggregated statistics for objectives."""
    total = db.query(Project2025Policy).count()

    # By status
    status_counts = (
        db.query(Project2025Policy.status, func.count(Project2025Policy.id))
        .group_by(Project2025Policy.status)
        .all()
    )
    by_status = {status: count for status, count in status_counts}

    # By category
    category_counts = (
        db.query(Project2025Policy.category, func.count(Project2025Policy.id))
        .group_by(Project2025Policy.category)
        .all()
    )
    by_category = {cat: count for cat, count in category_counts}

    # By priority
    priority_counts = (
        db.query(Project2025Policy.priority, func.count(Project2025Policy.id))
        .group_by(Project2025Policy.priority)
        .all()
    )
    by_priority = {pri: count for pri, count in priority_counts}

    # By timeline
    timeline_counts = (
        db.query(Project2025Policy.implementation_timeline, func.count(Project2025Policy.id))
        .group_by(Project2025Policy.implementation_timeline)
        .all()
    )
    by_timeline = {tl: count for tl, count in timeline_counts}

    # Calculate completion percentage
    completed = by_status.get("completed", 0)
    in_progress = by_status.get("in_progress", 0)
    completion_percentage = ((completed + in_progress * 0.5) / total * 100) if total > 0 else 0

    return ObjectiveStats(
        total=total,
        by_status=by_status,
        by_category=by_category,
        by_priority=by_priority,
        by_timeline=by_timeline,
        completion_percentage=round(completion_percentage, 1),
    )


@router.get("/objectives/metadata", response_model=ObjectiveMetadata)
async def get_objective_metadata(
    db: Session = Depends(get_db),
) -> ObjectiveMetadata:
    """Get distinct metadata values for objective filters."""
    categories = (
        db.query(Project2025Policy.category)
        .distinct()
        .order_by(Project2025Policy.category)
        .all()
    )
    statuses = (
        db.query(Project2025Policy.status)
        .distinct()
        .order_by(Project2025Policy.status)
        .all()
    )
    priorities = (
        db.query(Project2025Policy.priority)
        .distinct()
        .order_by(Project2025Policy.priority)
        .all()
    )
    timelines = (
        db.query(Project2025Policy.implementation_timeline)
        .distinct()
        .order_by(Project2025Policy.implementation_timeline)
        .all()
    )

    return ObjectiveMetadata(
        categories=[c[0] for c in categories if c[0]],
        statuses=[s[0] for s in statuses if s[0]],
        priorities=[p[0] for p in priorities if p[0]],
        timelines=[t[0] for t in timelines if t[0]],
    )


@router.get("/objectives/{objective_id}", response_model=ObjectiveDetail)
async def get_objective(
    objective_id: int,
    db: Session = Depends(get_db),
) -> ObjectiveDetail:
    """Get a single objective with full details."""
    obj = db.query(Project2025Policy).filter(Project2025Policy.id == objective_id).first()

    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")

    # Parse JSON fields
    keywords = json.loads(obj.keywords) if obj.keywords else []
    constitutional_concerns = (
        json.loads(obj.constitutional_concerns) if obj.constitutional_concerns else []
    )
    matching_eo_ids = json.loads(obj.matching_eo_ids) if obj.matching_eo_ids else []
    matching_legislation_ids = (
        json.loads(obj.matching_legislation_ids) if obj.matching_legislation_ids else []
    )

    return ObjectiveDetail(
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
        keywords=keywords,
        constitutional_concerns=constitutional_concerns,
        matching_eo_ids=matching_eo_ids,
        matching_legislation_ids=matching_legislation_ids,
        implementation_notes=obj.implementation_notes,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )
