"""P2025 Objectives API endpoints."""

from __future__ import annotations

import json
import re
from time import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from civitas.api.schemas import (
    ObjectiveDetail,
    ObjectiveList,
    ObjectiveMetadata,
    ObjectiveStats,
)
from civitas.api.utils import get_content_insight, objective_to_base
from civitas.db.models import Project2025Policy

router = APIRouter()
_METADATA_CACHE: tuple[float, ObjectiveMetadata] | None = None
_METADATA_TTL_SECONDS = 60.0


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
    eo_id: int | None = Query(None, description="Filter by matched executive order ID"),
    legislation_id: int | None = Query(None, description="Filter by matched legislation ID"),
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
    if eo_id:
        query = query.filter(Project2025Policy.matching_eo_ids.contains(f'"{eo_id}"'))
    if legislation_id:
        query = query.filter(
            Project2025Policy.matching_legislation_ids.contains(f'"{legislation_id}"')
        )

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
        items=[objective_to_base(item) for item in items],
    )


@router.get("/objectives/stats", response_model=ObjectiveStats)
async def get_objective_stats(
    db: Session = Depends(get_db),
) -> ObjectiveStats:
    """Get aggregated statistics for objectives."""

    def normalize_status(value: str | None) -> str:
        if not value:
            return "unknown"
        normalized = re.sub(r"[\s\-]+", "_", value.strip().lower())
        status_map = {
            "active": "in_progress",
            "inprogress": "in_progress",
            "in_progress": "in_progress",
            "inprogressing": "in_progress",
            "in_progressing": "in_progress",
            "completed": "completed",
            "complete": "completed",
            "enacted": "completed",
            "implemented": "completed",
            "blocked": "blocked",
            "reversed": "reversed",
            "proposed": "proposed",
            "draft": "proposed",
            "planned": "proposed",
            "pending": "proposed",
        }
        return status_map.get(normalized, normalized)

    total = db.query(Project2025Policy).count()

    # By status
    status_counts = (
        db.query(Project2025Policy.status, func.count(Project2025Policy.id))
        .group_by(Project2025Policy.status)
        .all()
    )
    by_status: dict[str, int] = {}
    for status, count in status_counts:
        normalized = normalize_status(status)
        by_status[normalized] = by_status.get(normalized, 0) + count

    if "completed" in by_status and "enacted" not in by_status:
        by_status["enacted"] = by_status["completed"]
    if "enacted" in by_status and "completed" not in by_status:
        by_status["completed"] = by_status["enacted"]

    # By category
    category_counts = (
        db.query(Project2025Policy.category, func.count(Project2025Policy.id))
        .group_by(Project2025Policy.category)
        .all()
    )
    by_category = {cat: count for cat, count in category_counts}

    # By category and status
    category_status_counts = (
        db.query(
            Project2025Policy.category,
            Project2025Policy.status,
            func.count(Project2025Policy.id),
        )
        .group_by(Project2025Policy.category, Project2025Policy.status)
        .all()
    )
    by_category_status: dict[str, dict[str, int]] = {}
    for category, status, count in category_status_counts:
        normalized = normalize_status(status)
        category_key = category or "unknown"
        if category_key not in by_category_status:
            by_category_status[category_key] = {}
        by_category_status[category_key][normalized] = (
            by_category_status[category_key].get(normalized, 0) + count
        )

    for category_key, status_counts in by_category_status.items():
        if "completed" in status_counts and "enacted" not in status_counts:
            status_counts["enacted"] = status_counts["completed"]
        if "enacted" in status_counts and "completed" not in status_counts:
            status_counts["completed"] = status_counts["enacted"]

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
    enacted = by_status.get("enacted", 0)
    in_progress = by_status.get("in_progress", 0)
    completion_percentage = (
        ((completed + enacted + in_progress * 0.5) / total * 100) if total > 0 else 0
    )

    return ObjectiveStats(
        total=total,
        by_status=by_status,
        by_category=by_category,
        by_category_status=by_category_status,
        by_priority=by_priority,
        by_timeline=by_timeline,
        completion_percentage=round(completion_percentage, 1),
    )


@router.get("/objectives/metadata", response_model=ObjectiveMetadata)
async def get_objective_metadata(
    db: Session = Depends(get_db),
) -> ObjectiveMetadata:
    """Get distinct metadata values for objective filters."""
    global _METADATA_CACHE
    now = time()
    if _METADATA_CACHE and now - _METADATA_CACHE[0] < _METADATA_TTL_SECONDS:
        return _METADATA_CACHE[1]

    categories = (
        db.query(Project2025Policy.category).distinct().order_by(Project2025Policy.category).all()
    )
    statuses = (
        db.query(Project2025Policy.status).distinct().order_by(Project2025Policy.status).all()
    )
    priorities = (
        db.query(Project2025Policy.priority).distinct().order_by(Project2025Policy.priority).all()
    )
    timelines = (
        db.query(Project2025Policy.implementation_timeline)
        .distinct()
        .order_by(Project2025Policy.implementation_timeline)
        .all()
    )

    metadata = ObjectiveMetadata(
        categories=[c[0] for c in categories if c[0]],
        statuses=[s[0] for s in statuses if s[0]],
        priorities=[p[0] for p in priorities if p[0]],
        timelines=[t[0] for t in timelines if t[0]],
    )
    _METADATA_CACHE = (now, metadata)
    return metadata


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

    base = objective_to_base(obj)
    insight = get_content_insight(db, "objective", obj.id)

    return ObjectiveDetail(
        **base.model_dump(),
        keywords=keywords,
        constitutional_concerns=constitutional_concerns,
        matching_eo_ids=matching_eo_ids,
        matching_legislation_ids=matching_legislation_ids,
        implementation_notes=obj.implementation_notes,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        **insight,
    )
