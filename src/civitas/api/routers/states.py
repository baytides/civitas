"""States API endpoints."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from civitas.api.schemas import (
    StateBase,
    StateBillBase,
    StateDetail,
    StateLegislatorBase,
    StateList,
)
from civitas.db.models import Legislation, Legislator, StateResistanceAction
from civitas.states import OpenStatesClient

router = APIRouter()


def get_db(request: Request) -> Session:
    """Get database session."""
    return Session(request.app.state.engine)


# State name mapping
STATE_NAMES = OpenStatesClient.STATES

STATE_NAME_ALIASES: dict[str, str] = {}
for code, name in STATE_NAMES.items():
    lowered = name.lower()
    STATE_NAME_ALIASES[lowered] = code
    STATE_NAME_ALIASES[lowered.replace(" ", "_")] = code
    STATE_NAME_ALIASES[lowered.replace(" ", "-")] = code


def normalize_jurisdiction(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in STATE_NAMES:
        return normalized
    return STATE_NAME_ALIASES.get(normalized)


def jurisdiction_aliases(code: str) -> list[str]:
    aliases = {code}
    name = STATE_NAMES.get(code)
    if name:
        lowered = name.lower()
        aliases.add(lowered)
        aliases.add(lowered.replace(" ", "_"))
        aliases.add(lowered.replace(" ", "-"))
    return list(aliases)


@router.get("/states", response_model=StateList)
async def list_states(
    db: Session = Depends(get_db),
) -> StateList:
    """List all states with action counts."""
    # Get bill counts by state
    bill_counts = (
        db.query(Legislation.jurisdiction, func.count(Legislation.id))
        .group_by(Legislation.jurisdiction)
        .all()
    )
    bill_count_map: dict[str, int] = defaultdict(int)
    for jurisdiction, count in bill_counts:
        code = normalize_jurisdiction(jurisdiction)
        if code:
            bill_count_map[code] += count

    # Get legislator counts by state
    legislator_counts = (
        db.query(Legislator.jurisdiction, func.count(Legislator.id))
        .group_by(Legislator.jurisdiction)
        .all()
    )
    legislator_count_map: dict[str, int] = defaultdict(int)
    for jurisdiction, count in legislator_counts:
        code = normalize_jurisdiction(jurisdiction)
        if code:
            legislator_count_map[code] += count

    # Get resistance action counts by state
    resistance_counts = (
        db.query(StateResistanceAction.state_code, func.count(StateResistanceAction.id))
        .group_by(StateResistanceAction.state_code)
        .all()
    )
    resistance_count_map: dict[str, int] = defaultdict(int)
    for code, count in resistance_counts:
        if not code:
            continue
        resistance_count_map[code.lower()] += count

    # Build state list
    items = []
    for code, name in STATE_NAMES.items():
        items.append(
            StateBase(
                code=code,
                name=name,
                bill_count=bill_count_map.get(code, 0),
                legislator_count=legislator_count_map.get(code, 0),
                resistance_action_count=resistance_count_map.get(code, 0),
            )
        )

    # Sort by name
    items.sort(key=lambda x: x.name)

    return StateList(items=items)


@router.get("/states/{state_code}", response_model=StateDetail)
async def get_state(
    state_code: str,
    db: Session = Depends(get_db),
) -> StateDetail:
    """Get detailed state info with recent bills and legislators."""
    code = state_code.lower()

    if code not in STATE_NAMES:
        raise HTTPException(status_code=404, detail="State not found")

    # Get counts
    aliases = jurisdiction_aliases(code)
    bill_count = db.query(Legislation).filter(Legislation.jurisdiction.in_(aliases)).count()
    legislator_count = db.query(Legislator).filter(Legislator.jurisdiction.in_(aliases)).count()
    resistance_action_count = (
        db.query(StateResistanceAction).filter(StateResistanceAction.state_code == code).count()
    )

    # Get recent bills
    recent_bills = (
        db.query(Legislation)
        .filter(Legislation.jurisdiction.in_(aliases))
        .order_by(Legislation.introduced_date.desc().nullslast())
        .limit(10)
        .all()
    )

    # Get legislators
    legislators = (
        db.query(Legislator)
        .filter(Legislator.jurisdiction.in_(aliases))
        .order_by(Legislator.full_name)
        .limit(100)
        .all()
    )

    return StateDetail(
        code=code,
        name=STATE_NAMES[code],
        bill_count=bill_count,
        legislator_count=legislator_count,
        resistance_action_count=resistance_action_count,
        recent_bills=[
            StateBillBase(
                id=b.id,
                identifier=(
                    f"{b.chamber.upper()[0]}B {b.number}" if b.number else b.source_id or str(b.id)
                ),
                title=b.title,
                chamber=b.chamber,
                session=b.session or "",
                status=b.status,
                introduced_date=b.introduced_date,
            )
            for b in recent_bills
        ],
        legislators=[
            StateLegislatorBase(
                id=legislator.id,
                full_name=legislator.full_name,
                chamber=legislator.chamber or "unknown",
                district=legislator.district,
                party=legislator.party or "Unknown",
                state=legislator.state or code.upper(),
            )
            for legislator in legislators
        ],
    )


@router.get("/states/{state_code}/bills")
async def get_state_bills(
    state_code: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: str | None = Query(None),
    chamber: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    """Get bills for a specific state."""
    code = state_code.lower()

    if code not in STATE_NAMES:
        raise HTTPException(status_code=404, detail="State not found")

    aliases = jurisdiction_aliases(code)
    query = db.query(Legislation).filter(Legislation.jurisdiction.in_(aliases))

    if session:
        query = query.filter(Legislation.session == session)
    if chamber:
        query = query.filter(Legislation.chamber == chamber)

    total = query.count()
    offset = (page - 1) * per_page

    bills = (
        query.order_by(Legislation.introduced_date.desc().nullslast())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page,
        "items": [
            StateBillBase(
                id=b.id,
                identifier=(
                    f"{b.chamber.upper()[0]}B {b.number}" if b.number else b.source_id or str(b.id)
                ),
                title=b.title,
                chamber=b.chamber,
                session=b.session or "",
                status=b.status,
                introduced_date=b.introduced_date,
            ).model_dump()
            for b in bills
        ],
    }


@router.get("/states/{state_code}/legislators")
async def get_state_legislators(
    state_code: str,
    chamber: str | None = Query(None),
    party: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    """Get legislators for a specific state."""
    code = state_code.lower()

    if code not in STATE_NAMES:
        raise HTTPException(status_code=404, detail="State not found")

    aliases = jurisdiction_aliases(code)
    query = db.query(Legislator).filter(Legislator.jurisdiction.in_(aliases))

    if chamber:
        query = query.filter(Legislator.chamber == chamber)
    if party:
        query = query.filter(Legislator.party == party)

    legislators = query.order_by(Legislator.full_name).all()

    return {
        "total": len(legislators),
        "items": [
            StateLegislatorBase(
                id=legislator.id,
                full_name=legislator.full_name,
                chamber=legislator.chamber or "unknown",
                district=legislator.district,
                party=legislator.party or "Unknown",
                state=legislator.state or code.upper(),
            ).model_dump()
            for legislator in legislators
        ],
    }
