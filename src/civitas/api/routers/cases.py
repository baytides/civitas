"""Court Cases API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from civitas.api.schemas import (
    CourtCaseBase,
    CourtCaseDetail,
    CourtCaseList,
    ObjectiveBase,
)
from civitas.db.models import CourtCase, LegalChallenge, Project2025Policy

router = APIRouter()


def get_db(request: Request) -> Session:
    """Get database session."""
    return Session(request.app.state.engine)


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

    linked_objectives = (
        db.query(Project2025Policy)
        .join(LegalChallenge, LegalChallenge.p2025_policy_id == Project2025Policy.id)
        .filter(LegalChallenge.court_case_id == case_id)
        .all()
    )

    return CourtCaseDetail(
        id=case.id,
        citation=case.citation,
        case_name=case.case_name,
        court_level=case.court_level,
        court=case.court,
        decision_date=case.decision_date,
        status=case.status,
        docket_number=case.docket_number,
        holding=case.holding,
        majority_author=case.majority_author,
        dissent_author=case.dissent_author,
        source_url=case.source_url,
        linked_objectives=[ObjectiveBase.model_validate(obj) for obj in linked_objectives],
    )
