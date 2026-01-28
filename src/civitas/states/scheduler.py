"""OpenStates smart scheduler for API-limited ingestion.

Keeps state-level cursors so daily runs stay within 500/day limit.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from civitas.db.models import Legislation, get_engine
from civitas.states.openstates import OpenStatesClient


@dataclass
class SchedulerConfig:
    db_url: str = "sqlite:///civitas.db"
    state_file: Path = Path("data/openstates_scheduler.json")
    limit_per_state: int = 50
    lookback_days: int = 7
    max_states: int = 8
    states: list[str] | None = None


DEFAULT_PRIORITY_STATES = [
    "ca",
    "ny",
    "tx",
    "fl",
    "pa",
    "il",
    "oh",
    "mi",
    "ga",
    "nc",
]


def _load_state(state_file: Path) -> dict:
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text())
    except json.JSONDecodeError:
        return {}


def _save_state(state_file: Path, payload: dict) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _parse_session(client: OpenStatesClient, state: str) -> str | None:
    sessions = client.get_sessions(state)
    if not sessions:
        return None
    return sessions[0].identifier


def run_scheduler(config: SchedulerConfig) -> dict:
    api_key = os.getenv("OPENSTATES_API_KEY")
    if not api_key:
        raise ValueError("OPENSTATES_API_KEY not set")

    engine = get_engine(config.db_url)
    state_cache = _load_state(config.state_file)

    states = config.states or DEFAULT_PRIORITY_STATES
    states = [s.lower() for s in states][: config.max_states]

    counts = {"states": 0, "bills_added": 0, "bills_skipped": 0}

    with OpenStatesClient(api_key=api_key) as client:
        for state in states:
            session_id = _parse_session(client, state)
            if not session_id:
                continue

            last_updated = state_cache.get(state)
            if last_updated:
                updated_since = datetime.fromisoformat(last_updated).date()
            else:
                updated_since = (datetime.now(UTC) - timedelta(days=config.lookback_days)).date()

            with Session(engine) as db_session:
                for bill in client.get_bills(
                    state=state,
                    session=session_id,
                    updated_since=updated_since,
                    limit=config.limit_per_state,
                ):
                    existing = (
                        db_session.query(Legislation)
                        .filter(
                            Legislation.jurisdiction == state.lower(),
                            Legislation.source_id == bill.id,
                        )
                        .first()
                    )
                    if existing:
                        counts["bills_skipped"] += 1
                        continue

                    chamber = "assembly" if bill.chamber == "lower" else "senate"
                    number = 0
                    for part in bill.identifier.split():
                        if part.isdigit():
                            number = int(part)
                            break

                    bill_type = "bill"
                    for cls in bill.classification:
                        if "resolution" in cls.lower():
                            bill_type = "resolution"
                            break

                    legislation = Legislation(
                        jurisdiction=state.lower(),
                        source_id=bill.id,
                        legislation_type=bill_type,
                        chamber=chamber,
                        number=number,
                        session=bill.session,
                        title=bill.title[:1000] if bill.title else None,
                        summary=bill.abstracts[0].get("abstract") if bill.abstracts else None,
                        introduced_date=bill.first_action_date,
                        last_action_date=bill.latest_action_date,
                        is_enacted="became-law" in str(bill.classification).lower(),
                        source_url=bill.sources[0].get("url") if bill.sources else None,
                    )
                    db_session.add(legislation)
                    db_session.commit()
                    counts["bills_added"] += 1

            state_cache[state] = datetime.now(UTC).isoformat()
            counts["states"] += 1

    _save_state(config.state_file, state_cache)
    return counts
