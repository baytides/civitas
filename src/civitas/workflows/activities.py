"""Temporal activities for Civitas workflows.

Activities are the building blocks of workflows - they perform the actual work
and can be retried independently on failure.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity

# Activity timeout configurations
DEFAULT_TIMEOUT = timedelta(minutes=30)
AI_TIMEOUT = timedelta(minutes=10)  # Per-item AI generation
INGESTION_TIMEOUT = timedelta(hours=2)  # Large data pulls


@dataclass
class IngestionResult:
    """Result of a data ingestion activity."""

    source: str
    records_processed: int
    records_created: int
    records_updated: int
    errors: list[str]
    duration_seconds: float


@dataclass
class GenerationResult:
    """Result of an AI content generation activity."""

    content_type: str
    items_processed: int
    items_generated: int
    items_failed: int
    errors: list[str]
    duration_seconds: float


# =============================================================================
# Data Ingestion Activities
# =============================================================================


@activity.defn
async def ingest_federal_congress(
    congress: int,
    laws_only: bool = True,
) -> IngestionResult:
    """Ingest federal legislation from Congress.gov API.

    Args:
        congress: Congress number (e.g., 118, 119)
        laws_only: If True, only fetch enacted laws

    Returns:
        IngestionResult with counts and any errors
    """
    import time

    from sqlalchemy.orm import Session

    from civitas.congress.client import CongressClient
    from civitas.db import DataIngester, get_engine

    start = time.time()
    errors = []
    records_created = 0
    records_updated = 0

    activity.heartbeat(f"Starting federal ingestion for Congress {congress}")

    try:
        engine = get_engine()
        client = CongressClient(api_key=os.getenv("CONGRESS_API_KEY"))
        ingester = DataIngester()

        with Session(engine) as session:
            # Fetch and ingest bills
            activity.heartbeat(f"Fetching bills for Congress {congress}")

            def progress_callback(current: int, total: int, message: str = ""):
                activity.heartbeat(f"Progress: {current}/{total} - {message}")

            result = ingester.ingest_federal_congress(
                session=session,
                client=client,
                congress=congress,
                laws_only=laws_only,
                progress_callback=progress_callback,
            )
            records_created = result.get("created", 0)
            records_updated = result.get("updated", 0)

    except Exception as e:
        errors.append(f"Federal ingestion error: {e!s}")
        activity.heartbeat(f"Error: {e!s}")

    duration = time.time() - start
    return IngestionResult(
        source=f"congress-{congress}",
        records_processed=records_created + records_updated,
        records_created=records_created,
        records_updated=records_updated,
        errors=errors,
        duration_seconds=duration,
    )


@activity.defn
async def ingest_california(session_year: int) -> IngestionResult:
    """Ingest California legislature data.

    Args:
        session_year: Session year (e.g., 2023, 2024)

    Returns:
        IngestionResult with counts and any errors
    """
    import time

    from sqlalchemy.orm import Session

    from civitas.california.client import CaliforniaLegislatureClient
    from civitas.db import DataIngester, get_engine

    start = time.time()
    errors = []
    records_created = 0

    activity.heartbeat(f"Starting California ingestion for {session_year}")

    try:
        engine = get_engine()
        client = CaliforniaLegislatureClient()
        ingester = DataIngester()

        with Session(engine) as session:
            def progress_callback(current: int, total: int, message: str = ""):
                activity.heartbeat(f"CA {session_year}: {current}/{total} - {message}")

            result = ingester.ingest_california_session(
                session=session,
                client=client,
                session_year=session_year,
                progress_callback=progress_callback,
            )
            records_created = result.get("created", 0)

    except Exception as e:
        errors.append(f"California ingestion error: {e!s}")

    duration = time.time() - start
    return IngestionResult(
        source=f"california-{session_year}",
        records_processed=records_created,
        records_created=records_created,
        records_updated=0,
        errors=errors,
        duration_seconds=duration,
    )


@activity.defn
async def ingest_executive_orders(year: int) -> IngestionResult:
    """Ingest executive orders from Federal Register.

    Args:
        year: Year to ingest (e.g., 2024, 2025)

    Returns:
        IngestionResult with counts and any errors
    """
    import time

    from sqlalchemy.orm import Session

    from civitas.db import get_engine
    from civitas.db.models import ExecutiveOrder
    from civitas.executive.client import FederalRegisterClient

    start = time.time()
    errors = []
    records_created = 0

    activity.heartbeat(f"Starting EO ingestion for {year}")

    try:
        engine = get_engine()
        client = FederalRegisterClient()

        with Session(engine) as session:
            eos = client.fetch_executive_orders(year=year)
            activity.heartbeat(f"Fetched {len(eos)} executive orders for {year}")

            for eo_data in eos:
                # Check if exists
                existing = session.query(ExecutiveOrder).filter_by(
                    document_number=eo_data.get("document_number")
                ).first()

                if not existing:
                    eo = ExecutiveOrder(**eo_data)
                    session.add(eo)
                    records_created += 1

            session.commit()

    except Exception as e:
        errors.append(f"EO ingestion error: {e!s}")

    duration = time.time() - start
    return IngestionResult(
        source=f"executive-orders-{year}",
        records_processed=records_created,
        records_created=records_created,
        records_updated=0,
        errors=errors,
        duration_seconds=duration,
    )


@activity.defn
async def ingest_scotus_opinions(
    term: str | None = None,
    all_terms: bool = False,
) -> IngestionResult:
    """Ingest Supreme Court opinions.

    Args:
        term: Specific term (e.g., "24" for 2024 term)
        all_terms: If True, ingest all available terms

    Returns:
        IngestionResult with counts and any errors
    """
    import time

    from sqlalchemy.orm import Session

    from civitas.db import get_engine
    from civitas.scotus.client import SCOTUSClient

    start = time.time()
    errors = []
    records_created = 0

    activity.heartbeat("Starting SCOTUS opinions ingestion")

    try:
        engine = get_engine()
        client = SCOTUSClient()

        with Session(engine) as session:
            if all_terms:
                terms = ["18", "19", "20", "21", "22", "23", "24", "25"]
            elif term:
                terms = [term]
            else:
                terms = ["24", "25"]  # Recent terms by default

            for t in terms:
                activity.heartbeat(f"Ingesting SCOTUS term {t}")
                result = client.ingest_term(session, t)
                records_created += result.get("created", 0)

            session.commit()

    except Exception as e:
        errors.append(f"SCOTUS ingestion error: {e!s}")

    duration = time.time() - start
    return IngestionResult(
        source="scotus-opinions",
        records_processed=records_created,
        records_created=records_created,
        records_updated=0,
        errors=errors,
        duration_seconds=duration,
    )


@activity.defn
async def ingest_state_bills(
    state: str,
    session: str | None = None,
) -> IngestionResult:
    """Ingest state legislature bills via OpenStates API.

    Args:
        state: State abbreviation (e.g., "CA", "TX")
        session: Legislative session identifier

    Returns:
        IngestionResult with counts and any errors
    """
    import time

    from sqlalchemy.orm import Session as DBSession

    from civitas.db import get_engine
    from civitas.states.openstates import OpenStatesClient

    start = time.time()
    errors = []
    records_created = 0

    activity.heartbeat(f"Starting {state} bills ingestion")

    try:
        engine = get_engine()
        client = OpenStatesClient(api_key=os.getenv("OPENSTATES_API_KEY"))

        with DBSession(engine) as db_session:
            result = client.ingest_state_bills(
                session=db_session,
                state=state,
                legislative_session=session,
                progress_callback=lambda c, t, m: activity.heartbeat(f"{state}: {c}/{t}"),
            )
            records_created = result.get("created", 0)

    except Exception as e:
        errors.append(f"State {state} ingestion error: {e!s}")

    duration = time.time() - start
    return IngestionResult(
        source=f"openstates-{state}",
        records_processed=records_created,
        records_created=records_created,
        records_updated=0,
        errors=errors,
        duration_seconds=duration,
    )


# =============================================================================
# AI Content Generation Activities
# =============================================================================


@activity.defn
async def generate_justice_profiles(
    limit: int | None = None,
    force: bool = False,
) -> GenerationResult:
    """Generate AI-powered justice profiles.

    Args:
        limit: Maximum number of profiles to generate
        force: If True, regenerate existing profiles

    Returns:
        GenerationResult with counts and any errors
    """
    import time

    from sqlalchemy.orm import Session

    from civitas.db import get_engine
    from civitas.scotus.profiles import JusticeProfileGenerator

    start = time.time()
    errors = []
    items_generated = 0
    items_failed = 0

    activity.heartbeat("Starting justice profile generation")

    try:
        engine = get_engine()
        generator = JusticeProfileGenerator()

        with Session(engine) as session:
            justices = generator.get_justices_needing_profiles(
                session, force=force, limit=limit
            )
            total = len(justices)
            activity.heartbeat(f"Found {total} justices needing profiles")

            for i, justice in enumerate(justices):
                try:
                    activity.heartbeat(f"Generating profile {i + 1}/{total}: {justice.name}")
                    generator.generate_profile(session, justice)
                    items_generated += 1
                except Exception as e:
                    errors.append(f"Failed for {justice.name}: {e!s}")
                    items_failed += 1

            session.commit()

    except Exception as e:
        errors.append(f"Profile generation error: {e!s}")

    duration = time.time() - start
    return GenerationResult(
        content_type="justice-profiles",
        items_processed=items_generated + items_failed,
        items_generated=items_generated,
        items_failed=items_failed,
        errors=errors,
        duration_seconds=duration,
    )


@activity.defn
async def generate_resistance_analyses(
    limit: int = 25,
    refresh_days: int = 30,
) -> GenerationResult:
    """Generate resistance analyses for Project 2025 policies.

    Args:
        limit: Maximum number of analyses to generate per batch
        refresh_days: Regenerate analyses older than this many days

    Returns:
        GenerationResult with counts and any errors
    """
    import time

    from sqlalchemy.orm import Session

    from civitas.db import get_engine
    from civitas.resistance.analyzer import ResistanceAnalyzer

    start = time.time()
    errors = []
    items_generated = 0
    items_failed = 0

    activity.heartbeat(f"Starting resistance analysis generation (limit={limit})")

    try:
        engine = get_engine()
        analyzer = ResistanceAnalyzer()

        with Session(engine) as session:
            policies = analyzer.get_policies_needing_analysis(
                session, limit=limit, refresh_days=refresh_days
            )
            total = len(policies)
            activity.heartbeat(f"Found {total} policies needing analysis")

            for i, policy in enumerate(policies):
                try:
                    activity.heartbeat(f"Analyzing {i + 1}/{total}: Policy {policy.id}")
                    analyzer.analyze_policy(session, policy)
                    items_generated += 1
                    session.commit()  # Commit after each to preserve progress
                except Exception as e:
                    errors.append(f"Failed for policy {policy.id}: {e!s}")
                    items_failed += 1
                    session.rollback()

    except Exception as e:
        errors.append(f"Analysis generation error: {e!s}")

    duration = time.time() - start
    return GenerationResult(
        content_type="resistance-analyses",
        items_processed=items_generated + items_failed,
        items_generated=items_generated,
        items_failed=items_failed,
        errors=errors,
        duration_seconds=duration,
    )


@activity.defn
async def generate_resistance_recommendations(
    limit: int = 25,
    tier: str | None = None,
    force: bool = False,
) -> GenerationResult:
    """Generate resistance recommendations for analyzed policies.

    Args:
        limit: Maximum number of recommendations to generate per batch
        tier: Specific tier to generate ("immediate", "congressional", "presidential")
        force: If True, regenerate existing recommendations

    Returns:
        GenerationResult with counts and any errors
    """
    import time

    from sqlalchemy.orm import Session

    from civitas.db import get_engine
    from civitas.resistance.recommender import ResistanceRecommender

    start = time.time()
    errors = []
    items_generated = 0
    items_failed = 0

    activity.heartbeat(f"Starting recommendation generation (limit={limit}, tier={tier})")

    try:
        engine = get_engine()
        recommender = ResistanceRecommender()

        with Session(engine) as session:
            policies = recommender.get_policies_needing_recommendations(
                session, limit=limit, tier=tier, force=force
            )
            total = len(policies)
            activity.heartbeat(f"Found {total} policies needing recommendations")

            for i, policy in enumerate(policies):
                try:
                    activity.heartbeat(f"Recommending {i + 1}/{total}: Policy {policy.id}")
                    recommender.generate_recommendations(session, policy, tier=tier)
                    items_generated += 1
                    session.commit()
                except Exception as e:
                    errors.append(f"Failed for policy {policy.id}: {e!s}")
                    items_failed += 1
                    session.rollback()

    except Exception as e:
        errors.append(f"Recommendation generation error: {e!s}")

    duration = time.time() - start
    return GenerationResult(
        content_type="resistance-recommendations",
        items_processed=items_generated + items_failed,
        items_generated=items_generated,
        items_failed=items_failed,
        errors=errors,
        duration_seconds=duration,
    )


@activity.defn
async def generate_insights(
    content_type: str,
    limit: int = 50,
    force: bool = False,
    ids: list[int] | None = None,
) -> GenerationResult:
    """Generate plain-language insights for content.

    Args:
        content_type: Type of content ("objective", "eo", "case", "legislation")
        limit: Maximum number of insights to generate
        force: If True, regenerate existing insights
        ids: Specific IDs to generate insights for

    Returns:
        GenerationResult with counts and any errors
    """
    import time

    from sqlalchemy.orm import Session

    from civitas.db import get_engine
    from civitas.insights.generator import InsightGenerator

    start = time.time()
    errors = []
    items_generated = 0
    items_failed = 0

    activity.heartbeat(f"Starting insights generation for {content_type}")

    try:
        engine = get_engine()
        generator = InsightGenerator()

        with Session(engine) as session:
            items = generator.get_items_needing_insights(
                session,
                content_type=content_type,
                limit=limit,
                force=force,
                ids=ids,
            )
            total = len(items)
            activity.heartbeat(f"Found {total} items needing insights")

            for i, item in enumerate(items):
                try:
                    activity.heartbeat(f"Generating {i + 1}/{total}: {content_type} {item.id}")
                    generator.generate_insight(session, item, content_type)
                    items_generated += 1
                    session.commit()
                except Exception as e:
                    errors.append(f"Failed for {content_type} {item.id}: {e!s}")
                    items_failed += 1
                    session.rollback()

    except Exception as e:
        errors.append(f"Insight generation error: {e!s}")

    duration = time.time() - start
    return GenerationResult(
        content_type=f"insights-{content_type}",
        items_processed=items_generated + items_failed,
        items_generated=items_generated,
        items_failed=items_failed,
        errors=errors,
        duration_seconds=duration,
    )
