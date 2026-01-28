"""Resistance API endpoints."""

from __future__ import annotations

from time import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from civitas.api.schemas import (
    BlockedPolicy,
    ProgressSummary,
    ResistanceAnalysis,
    ResistanceMeta,
    ResistanceRecommendation,
)
from civitas.db.models import (
    Project2025Policy,
)
from civitas.db.models import (
    ResistanceRecommendation as DBResistanceRecommendation,
)
from civitas.resistance import ImplementationTracker, ResistanceAnalyzer, ResistanceRecommender
from civitas.resistance.content import RESISTANCE_ORG_SECTIONS, RESISTANCE_TIERS

router = APIRouter()
_ANALYSIS_CACHE: dict[int, tuple[float, dict]] = {}
_ANALYSIS_TTL_SECONDS = 60 * 60
_ANALYSIS_DB_MAX_AGE_DAYS = 30


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


@router.get("/resistance/meta", response_model=ResistanceMeta)
async def get_resistance_meta() -> ResistanceMeta:
    """Get metadata for resistance UI rendering."""
    return ResistanceMeta(
        tiers=RESISTANCE_TIERS,
        organization_sections=RESISTANCE_ORG_SECTIONS,
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

    existing = (
        db.query(DBResistanceRecommendation)
        .filter(DBResistanceRecommendation.p2025_policy_id == objective_id)
        .order_by(DBResistanceRecommendation.tier, DBResistanceRecommendation.created_at)
        .all()
    )

    recommendations: list[ResistanceRecommendation] = []
    if existing:
        import json

        for rec in existing:
            prerequisites = json.loads(rec.prerequisites) if rec.prerequisites else []
            recommendations.append(
                ResistanceRecommendation(
                    tier=rec.tier,
                    action_type=rec.action_type,
                    title=rec.title,
                    description=rec.description,
                    legal_basis=rec.legal_basis,
                    likelihood=rec.likelihood_of_success,
                    prerequisites=prerequisites,
                )
            )
        return recommendations

    recommender = ResistanceRecommender(db)
    results = recommender.generate_recommendations(objective_id)

    if results.get("error"):
        raise HTTPException(status_code=500, detail=results["error"])

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
                    likelihood=rec.get("likelihood_of_success", rec.get("likelihood", "medium")),
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

    now = time()
    cached = _ANALYSIS_CACHE.get(objective_id)
    if cached and now - cached[0] < _ANALYSIS_TTL_SECONDS:
        analysis = cached[1]
    else:
        analyzer = ResistanceAnalyzer(db)
        analysis = analyzer.analyze_or_load(
            objective_id,
            max_age_days=_ANALYSIS_DB_MAX_AGE_DAYS,
        )
        _ANALYSIS_CACHE[objective_id] = (now, analysis)

    if analysis.get("error"):
        raise HTTPException(status_code=500, detail=analysis["error"])

    constitutional_issues = []
    for item in analysis.get("constitutional_issues", []):
        if not isinstance(item, dict):
            continue
        constitutional_issues.append(
            {
                "issue": item.get("issue") or item.get("provision") or item.get("problem"),
                "amendment": item.get("amendment") or item.get("provision"),
                "precedent": item.get("precedent") or item.get("case") or item.get("citation"),
                "strength": item.get("strength") or item.get("severity"),
            }
        )

    challenge_strategies = []
    for item in analysis.get("challenge_strategies", []):
        if not isinstance(item, dict):
            continue
        challenge_strategies.append(
            {
                "strategy": item.get("strategy") or item.get("type") or item.get("basis"),
                "description": item.get("description") or item.get("explanation"),
                "likelihood": item.get("likelihood") or item.get("likelihood_of_success"),
                "timeframe": item.get("timeframe") or item.get("time_sensitivity"),
            }
        )

    state_resistance_options = []
    for item in analysis.get("state_resistance_options", []):
        if not isinstance(item, dict):
            continue
        state_resistance_options.append(
            {
                "option": item.get("option") or item.get("action"),
                "description": item.get("description") or item.get("explanation"),
                "states_likely": item.get("states_likely") or item.get("states"),
            }
        )

    return ResistanceAnalysis(
        objective_id=objective_id,
        constitutional_issues=constitutional_issues,
        challenge_strategies=challenge_strategies,
        state_resistance_options=state_resistance_options,
        overall_vulnerability_score=analysis.get("overall_vulnerability_score", 0),
        justice_outlook=analysis.get("justice_outlook", []) or [],
        justice_outlook_disclaimer=analysis.get("justice_outlook_disclaimer")
        or "Speculative only. Based on historical opinions and stated philosophies; not predictive.",
        case_outcome_meter=analysis.get("case_outcome_meter"),
        case_outcome_rationale=analysis.get("case_outcome_rationale"),
        persuasion_strategies=analysis.get("persuasion_strategies", []) or [],
        persuasion_disclaimer=analysis.get("persuasion_disclaimer")
        or "Speculative only. This is not legal advice or a prediction of outcomes.",
    )
