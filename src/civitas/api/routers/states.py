"""States API endpoints."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from civitas.analysis.categories import CATEGORIES
from civitas.api.schemas import (
    StateBase,
    StateBillBase,
    StateDetail,
    StateLegislatorBase,
    StateList,
)
from civitas.db.models import Legislation, Legislator, StateResistanceAction

router = APIRouter()


def get_db(request: Request) -> Session:
    """Get database session."""
    return Session(request.app.state.engine)


# State name mapping (static, OpenStates-free)
STATE_NAMES = {
    "al": "Alabama",
    "ak": "Alaska",
    "az": "Arizona",
    "ar": "Arkansas",
    "ca": "California",
    "co": "Colorado",
    "ct": "Connecticut",
    "de": "Delaware",
    "fl": "Florida",
    "ga": "Georgia",
    "hi": "Hawaii",
    "id": "Idaho",
    "il": "Illinois",
    "in": "Indiana",
    "ia": "Iowa",
    "ks": "Kansas",
    "ky": "Kentucky",
    "la": "Louisiana",
    "me": "Maine",
    "md": "Maryland",
    "ma": "Massachusetts",
    "mi": "Michigan",
    "mn": "Minnesota",
    "ms": "Mississippi",
    "mo": "Missouri",
    "mt": "Montana",
    "ne": "Nebraska",
    "nv": "Nevada",
    "nh": "New Hampshire",
    "nj": "New Jersey",
    "nm": "New Mexico",
    "ny": "New York",
    "nc": "North Carolina",
    "nd": "North Dakota",
    "oh": "Ohio",
    "ok": "Oklahoma",
    "or": "Oregon",
    "pa": "Pennsylvania",
    "ri": "Rhode Island",
    "sc": "South Carolina",
    "sd": "South Dakota",
    "tn": "Tennessee",
    "tx": "Texas",
    "ut": "Utah",
    "vt": "Vermont",
    "va": "Virginia",
    "wa": "Washington",
    "wv": "West Virginia",
    "wi": "Wisconsin",
    "wy": "Wyoming",
    "dc": "District of Columbia",
}

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


P2025_CATEGORIES = [cat for cat in CATEGORIES if cat.p2025_related]


def classify_bill(text: str) -> tuple[str | None, str | None]:
    """Return (p2025_category, stance) using keyword heuristics."""
    text_lower = text.lower()
    best_category = None
    best_score = 0
    stance = None

    for category in P2025_CATEGORIES:
        score = sum(1 for kw in category.keywords if kw.lower() in text_lower)
        if score > best_score:
            best_score = score
            best_category = category.slug

        if category.threat_keywords and any(
            kw.lower() in text_lower for kw in category.threat_keywords
        ):
            stance = "support"
        if category.resistance_keywords and any(
            kw.lower() in text_lower for kw in category.resistance_keywords
        ):
            stance = "oppose"

    if best_score == 0:
        return None, None

    if stance is None:
        stance = "neutral"
    return best_category, stance


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
        .filter(Legislator.is_current.is_(True))
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
    legislator_count = (
        db.query(Legislator)
        .filter(Legislator.jurisdiction.in_(aliases), Legislator.is_current.is_(True))
        .count()
    )
    resistance_action_count = (
        db.query(StateResistanceAction).filter(StateResistanceAction.state_code == code).count()
    )

    # Get recent bills
    recent_bills_raw = (
        db.query(Legislation)
        .filter(Legislation.jurisdiction.in_(aliases))
        .order_by(Legislation.introduced_date.desc().nullslast())
        .limit(50)
        .all()
    )
    recent_bills = []
    for bill in recent_bills_raw:
        text = f"{bill.title or ''} {bill.summary or ''}".strip()
        category, stance = classify_bill(text)
        if category:
            recent_bills.append((bill, category, stance))
        if len(recent_bills) >= 10:
            break

    # Get legislators
    legislators = (
        db.query(Legislator)
        .filter(Legislator.jurisdiction.in_(aliases), Legislator.is_current.is_(True))
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
                id=bill.id,
                identifier=(
                    f"{bill.chamber.upper()[0]}B {bill.number}"
                    if bill.number
                    else bill.source_id or str(bill.id)
                ),
                title=bill.title,
                chamber=bill.chamber,
                session=bill.session or "",
                status=bill.status,
                introduced_date=bill.introduced_date,
                p2025_category=category,
                p2025_stance=stance,
            )
            for bill, category, stance in recent_bills
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

    bills_raw = (
        query.order_by(Legislation.introduced_date.desc().nullslast())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    bills = []
    for bill in bills_raw:
        text = f"{bill.title or ''} {bill.summary or ''}".strip()
        category, stance = classify_bill(text)
        if category:
            bills.append((bill, category, stance))

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page,
        "items": [
            StateBillBase(
                id=bill.id,
                identifier=(
                    f"{bill.chamber.upper()[0]}B {bill.number}"
                    if bill.number
                    else bill.source_id or str(bill.id)
                ),
                title=bill.title,
                chamber=bill.chamber,
                session=bill.session or "",
                status=bill.status,
                introduced_date=bill.introduced_date,
                p2025_category=category,
                p2025_stance=stance,
            ).model_dump()
            for bill, category, stance in bills
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
    query = db.query(Legislator).filter(
        Legislator.jurisdiction.in_(aliases), Legislator.is_current.is_(True)
    )

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
