"""Executive Orders API endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from civitas.api.schemas import (
    ExecutiveOrderBase,
    ExecutiveOrderDetail,
    ExecutiveOrderList,
    ObjectiveBase,
)
from civitas.db.models import ExecutiveOrder, Project2025Policy

router = APIRouter()


def get_db(request: Request) -> Session:
    """Get database session."""
    return Session(request.app.state.engine)


@router.get("/executive-orders", response_model=ExecutiveOrderList)
async def list_executive_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    president: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
) -> ExecutiveOrderList:
    """List executive orders with filtering and pagination."""
    query = db.query(ExecutiveOrder)

    # Apply filters
    if president:
        query = query.filter(ExecutiveOrder.president.ilike(f"%{president}%"))
    if year:
        query = query.filter(
            ExecutiveOrder.signing_date >= f"{year}-01-01",
            ExecutiveOrder.signing_date <= f"{year}-12-31",
        )

    # Get total count
    total = query.count()

    # Paginate
    offset = (page - 1) * per_page
    items = (
        query.order_by(ExecutiveOrder.signing_date.desc().nullslast())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return ExecutiveOrderList(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=(total + per_page - 1) // per_page,
        items=[ExecutiveOrderBase.model_validate(item) for item in items],
    )


@router.get("/executive-orders/{eo_id}", response_model=ExecutiveOrderDetail)
async def get_executive_order(
    eo_id: int,
    db: Session = Depends(get_db),
) -> ExecutiveOrderDetail:
    """Get a single executive order with matched objectives."""
    eo = db.query(ExecutiveOrder).filter(ExecutiveOrder.id == eo_id).first()

    if not eo:
        raise HTTPException(status_code=404, detail="Executive order not found")

    # Find matched objectives
    matched_objectives = []
    objectives = db.query(Project2025Policy).filter(
        Project2025Policy.matching_eo_ids.contains(f'"{eo_id}"')
    ).all()

    for obj in objectives:
        matched_objectives.append(ObjectiveBase.model_validate(obj))

    return ExecutiveOrderDetail(
        id=eo.id,
        document_number=eo.document_number,
        executive_order_number=eo.executive_order_number,
        title=eo.title,
        signing_date=eo.signing_date,
        publication_date=eo.publication_date,
        president=eo.president,
        abstract=eo.abstract,
        pdf_url=eo.pdf_url,
        html_url=eo.html_url,
        matched_objectives=matched_objectives,
    )
