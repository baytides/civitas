"""Resistance API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from civitas.api.schemas import (
    BlockedPolicy,
    ProgressSummary,
    ResistanceAnalysis,
    ResistanceRecommendation,
)
from civitas.db.models import Project2025Policy
from civitas.resistance import ImplementationTracker, ResistanceAnalyzer, ResistanceRecommender

router = APIRouter()


def get_db(request: Request) -> Session:
    """Get database session."""
    return Session(request.app.state.engine)


@router.get("/resistance/progress", response_model=ProgressSummary)
async def get_progress(
    db: Session = Depends(get_db),
) -> ProgressSummary:
    """Get overall P2025 implementation progress."""
    tracker = ImplementationTracker(db)
    summary = tracker.get_progress_summary()

    return ProgressSummary(
        total_objectives=summary.get("total_objectives", 0),
        by_status=summary.get("by_status", {}),
        completion_percentage=summary.get("completion_percentage", 0.0),
        recent_activity=summary.get("recent_activity", []),
        blocked_count=summary.get("by_status", {}).get("blocked", 0),
    )


@router.get("/resistance/blocked", response_model=list[BlockedPolicy])
async def get_blocked_policies(
    db: Session = Depends(get_db),
) -> list[BlockedPolicy]:
    """Get policies that have been blocked."""
    tracker = ImplementationTracker(db)
    blocked = tracker.get_blocked_policies()

    return [
        BlockedPolicy(
            objective_id=p["id"],
            agency=p["agency"],
            proposal_summary=p.get("proposal", "")[:200],
            blocked_by=p.get("blocked_by", "unknown"),
            case_or_action=(
                p.get("challenges", [{}])[0].get("case", "") if p.get("challenges") else ""
            ),
            blocked_date=None,
        )
        for p in blocked
    ]


@router.get(
    "/resistance/recommendations/{objective_id}",
    response_model=list[ResistanceRecommendation],
)
async def get_recommendations(
    objective_id: int,
    db: Session = Depends(get_db),
) -> list[ResistanceRecommendation]:
    """Get resistance recommendations for an objective."""
    # Verify objective exists
    obj = db.query(Project2025Policy).filter(Project2025Policy.id == objective_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")

    recommender = ResistanceRecommender(db)
    results = recommender.generate_recommendations(objective_id)

    if results.get("error"):
        raise HTTPException(status_code=500, detail=results["error"])

    recommendations = []
    for tier, recs in results.get("recommendations", {}).items():
        for rec in recs:
            if rec.get("error"):
                continue
            recommendations.append(
                ResistanceRecommendation(
                    tier=tier,
                    action_type=rec.get("action_type", "unknown"),
                    title=rec.get("title", "Untitled"),
                    description=rec.get("description", ""),
                    legal_basis=rec.get("legal_basis"),
                    likelihood=rec.get("likelihood", "medium"),
                    prerequisites=rec.get("prerequisites", []),
                )
            )

    return recommendations


@router.get("/resistance/analysis/{objective_id}", response_model=ResistanceAnalysis)
async def get_analysis(
    objective_id: int,
    db: Session = Depends(get_db),
) -> ResistanceAnalysis:
    """Get AI analysis of an objective's legal vulnerabilities."""
    # Verify objective exists
    obj = db.query(Project2025Policy).filter(Project2025Policy.id == objective_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")

    analyzer = ResistanceAnalyzer(db)
    analysis = analyzer.analyze_policy(objective_id)

    if analysis.get("error"):
        raise HTTPException(status_code=500, detail=analysis["error"])

    return ResistanceAnalysis(
        objective_id=objective_id,
        constitutional_issues=analysis.get("constitutional_issues", []),
        challenge_strategies=analysis.get("challenge_strategies", []),
        state_resistance_options=analysis.get("state_resistance_options", []),
        overall_vulnerability_score=analysis.get("overall_vulnerability_score", 0),
    )
