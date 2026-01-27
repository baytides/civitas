"""Search API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from civitas.api.schemas import SearchResponse, SearchResult
from civitas.db.models import CourtCase, ExecutiveOrder, Legislation, Project2025Policy

router = APIRouter()


def get_db(request: Request) -> Session:
    """Get database session."""
    return Session(request.app.state.engine)


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    types: str = Query(
        "all",
        description="Comma-separated types: objective,eo,case,bill,all",
    ),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Full-text search across all data types."""
    search_term = f"%{q}%"
    type_list = types.split(",") if types != "all" else ["objective", "eo", "case", "bill"]

    results: list[SearchResult] = []

    # Search P2025 objectives
    if "objective" in type_list or "all" in type_list:
        objectives = (
            db.query(Project2025Policy)
            .filter(
                or_(
                    Project2025Policy.proposal_text.ilike(search_term),
                    Project2025Policy.proposal_summary.ilike(search_term),
                    Project2025Policy.agency.ilike(search_term),
                )
            )
            .limit(limit // 4)
            .all()
        )

        for obj in objectives:
            snippet = obj.proposal_summary or obj.proposal_text[:200]
            results.append(
                SearchResult(
                    type="objective",
                    id=obj.id,
                    title=f"[{obj.agency}] {obj.proposal_summary[:50] if obj.proposal_summary else 'P2025 Objective'}...",
                    snippet=snippet,
                    score=1.0,  # TODO: Implement proper scoring
                )
            )

    # Search executive orders
    if "eo" in type_list or "all" in type_list:
        eos = (
            db.query(ExecutiveOrder)
            .filter(
                or_(
                    ExecutiveOrder.title.ilike(search_term),
                    ExecutiveOrder.abstract.ilike(search_term),
                )
            )
            .limit(limit // 4)
            .all()
        )

        for eo in eos:
            results.append(
                SearchResult(
                    type="eo",
                    id=eo.id,
                    title=eo.title,
                    snippet=eo.abstract[:200] if eo.abstract else "",
                    score=1.0,
                )
            )

    # Search court cases
    if "case" in type_list or "all" in type_list:
        cases = (
            db.query(CourtCase)
            .filter(
                or_(
                    CourtCase.case_name.ilike(search_term),
                    CourtCase.holding.ilike(search_term),
                    CourtCase.citation.ilike(search_term),
                )
            )
            .limit(limit // 4)
            .all()
        )

        for case in cases:
            results.append(
                SearchResult(
                    type="case",
                    id=case.id,
                    title=case.case_name,
                    snippet=case.holding[:200] if case.holding else case.citation,
                    score=1.0,
                )
            )

    # Search legislation/bills
    if "bill" in type_list or "all" in type_list:
        bills = (
            db.query(Legislation)
            .filter(
                or_(
                    Legislation.title.ilike(search_term),
                    Legislation.summary.ilike(search_term),
                )
            )
            .limit(limit // 4)
            .all()
        )

        for bill in bills:
            results.append(
                SearchResult(
                    type="bill",
                    id=bill.id,
                    title=bill.title or f"Bill {bill.number}",
                    snippet=bill.summary[:200] if bill.summary else "",
                    score=1.0,
                )
            )

    # Sort by score (TODO: implement real scoring)
    results.sort(key=lambda x: x.score, reverse=True)

    return SearchResponse(
        query=q,
        total=len(results),
        items=results[:limit],
    )
