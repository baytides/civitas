"""Court Cases API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from civitas.api.deps import get_db
from civitas.api.schemas import CourtCaseBase, CourtCaseDetail, CourtCaseList
from civitas.api.utils import get_content_insight, objective_to_base
from civitas.db.models import (
    CourtCase,
    LegalChallenge,
    P2025Implementation,
    Project2025Policy,
)

router = APIRouter()


@router.get("/cases", response_model=CourtCaseList)
async def list_cases(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    court_level: str | None = Query(None, description="scotus, circuit, or district"),
    court: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
) -> CourtCaseList:
    """List court cases with filtering and pagination."""
    query = db.query(CourtCase)

    # Apply filters
    if court_level:
        query = query.filter(CourtCase.court_level == court_level)
    if court:
        query = query.filter(CourtCase.court.ilike(f"%{court}%"))
    if status:
        query = query.filter(CourtCase.status == status)

    # Get total count
    total = query.count()

    # Paginate
    offset = (page - 1) * per_page
    items = (
        query.order_by(CourtCase.decision_date.desc().nullslast())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return CourtCaseList(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=(total + per_page - 1) // per_page,
        items=[CourtCaseBase.model_validate(item) for item in items],
    )


@router.get("/cases/{case_id}", response_model=CourtCaseDetail)
async def get_case(
    case_id: int,
    db: Session = Depends(get_db),
) -> CourtCaseDetail:
    """Get a single court case with full details."""
    case = db.query(CourtCase).filter(CourtCase.id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Court case not found")

    policy_id_rows = (
        db.query(LegalChallenge.p2025_policy_id)
        .filter(
            LegalChallenge.court_case_id == case_id,
            LegalChallenge.p2025_policy_id.isnot(None),
        )
        .all()
    )
    policy_ids = {row[0] for row in policy_id_rows if row[0]}

    implementation_rows = (
        db.query(LegalChallenge.implementation_id)
        .filter(
            LegalChallenge.court_case_id == case_id,
            LegalChallenge.implementation_id.isnot(None),
        )
        .all()
    )
    implementation_ids = [row[0] for row in implementation_rows if row[0]]
    if implementation_ids:
        linked_policy_rows = (
            db.query(P2025Implementation.policy_id)
            .filter(P2025Implementation.id.in_(implementation_ids))
            .all()
        )
        policy_ids.update({row[0] for row in linked_policy_rows if row[0]})

    linked_objectives = (
        db.query(Project2025Policy).filter(Project2025Policy.id.in_(policy_ids)).all()
        if policy_ids
        else []
    )

    base = CourtCaseBase.model_validate(case)
    insight = get_content_insight(db, "case", case.id)

    return CourtCaseDetail(
        **base.model_dump(),
        docket_number=case.docket_number,
        holding=case.holding,
        majority_author=case.majority_author,
        source_url=case.source_url,
        linked_objectives=[objective_to_base(obj) for obj in linked_objectives],
        **insight,
    )
