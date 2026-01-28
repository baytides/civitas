"""Legislation API endpoints."""

from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from civitas.api.schemas import (
    LegislationActionBase,
    LegislationBase,
    LegislationDetail,
    LegislationList,
)
from civitas.db.models import Legislation, LegislationAction, Project2025Policy

router = APIRouter()


def get_db(request: Request) -> Session:
    """Get database session."""
    return Session(request.app.state.engine)


@router.get("/legislation", response_model=LegislationList)
async def list_legislation(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    jurisdiction: str | None = Query(None),
    enacted: bool | None = Query(None),
    since: date | None = Query(None, description="Filter by action date on/after"),
    matched_only: bool = Query(False, description="Only legislation matched to Project 2025"),
    ids: str | None = Query(None, description="Comma-separated legislation IDs"),
    db: Session = Depends(get_db),
) -> LegislationList:
    """List legislation with filtering and pagination."""
    query = db.query(Legislation)

    if jurisdiction:
        query = query.filter(Legislation.jurisdiction == jurisdiction.lower())
    if enacted is not None:
        query = query.filter(Legislation.is_enacted.is_(enacted))
    if since:
        query = query.filter(
            or_(
                Legislation.last_action_date >= since,
                Legislation.introduced_date >= since,
                Legislation.enacted_date >= since,
            )
        )

    if matched_only:
        matched_ids: set[int] = set()
        for row in db.query(Project2025Policy.matching_legislation_ids).all():
            raw = row[0]
            if not raw:
                continue
            try:
                matched_ids.update(json.loads(raw))
            except json.JSONDecodeError:
                continue
        if matched_ids:
            query = query.filter(Legislation.id.in_(matched_ids))
        else:
            query = query.filter(Legislation.id == -1)

    if ids:
        try:
            id_list = [int(item.strip()) for item in ids.split(",") if item.strip()]
        except ValueError:
            id_list = []
        if id_list:
            query = query.filter(Legislation.id.in_(id_list))
        else:
            query = query.filter(Legislation.id == -1)

    total = query.count()
    offset = (page - 1) * per_page
    items = (
        query.order_by(Legislation.last_action_date.desc().nullslast())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return LegislationList(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=(total + per_page - 1) // per_page,
        items=[LegislationBase.model_validate(item) for item in items],
    )


@router.get("/legislation/{legislation_id}", response_model=LegislationDetail)
async def get_legislation(
    legislation_id: int,
    db: Session = Depends(get_db),
) -> LegislationDetail:
    """Get a single piece of legislation with actions."""
    leg = db.query(Legislation).filter(Legislation.id == legislation_id).first()
    if not leg:
        raise HTTPException(status_code=404, detail="Legislation not found")

    actions = (
        db.query(LegislationAction)
        .filter(LegislationAction.legislation_id == legislation_id)
        .order_by(LegislationAction.action_date.desc())
        .all()
    )

    subjects: list[str] = []
    if leg.subjects:
        try:
            subjects = json.loads(leg.subjects)
        except json.JSONDecodeError:
            subjects = []

    return LegislationDetail(
        **LegislationBase.model_validate(leg).model_dump(),
        summary=leg.summary,
        full_text=leg.full_text,
        policy_area=leg.policy_area,
        subjects=subjects,
        actions=[
            LegislationActionBase(
                action_date=action.action_date,
                action_text=action.action_text,
                action_code=action.action_code,
            )
            for action in actions
        ],
    )
