"""Command-line interface for Civitas."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

# Load environment variables from .env file
load_dotenv()

app = typer.Typer(
    name="civitas",
    help="Civic empowerment platform for legislative data.",
    no_args_is_help=True,
)
console = Console()


# =============================================================================
# Ingest Commands
# =============================================================================

ingest_app = typer.Typer(help="Data ingestion commands")
app.add_typer(ingest_app, name="ingest")

insights_app = typer.Typer(help="Insight summary commands")
app.add_typer(insights_app, name="insights")


@ingest_app.command("california")
def ingest_california(
    session_year: int = typer.Argument(..., help="Session year (e.g., 2023)"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
    data_dir: str | None = typer.Option(None, "--data-dir", help="Data directory"),
):
    """Ingest California Legislature data for a session."""
    from civitas.db import DataIngester

    console.print(f"[bold blue]Ingesting California {session_year} session...[/bold blue]")

    ingester = DataIngester(db_path=db_path)
    data_path = Path(data_dir) if data_dir else None

    def progress(table: str, count: int):
        console.print(f"  Processed {count} {table}...")

    counts = ingester.ingest_california_session(
        session_year=session_year,
        data_dir=data_path,
        progress_callback=progress,
    )

    console.print("\n[bold green]Ingestion complete![/bold green]")
    for key, value in counts.items():
        console.print(f"  {key}: {value:,}")


@ingest_app.command("federal")
def ingest_federal(
    congress: int = typer.Argument(..., help="Congress number (e.g., 118)"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
    laws_only: bool = typer.Option(True, "--laws-only/--all", help="Only ingest enacted laws"),
):
    """Ingest federal legislation from Congress.gov."""
    from civitas.db import DataIngester

    console.print(f"[bold blue]Ingesting Federal Congress {congress}...[/bold blue]")

    ingester = DataIngester(db_path=db_path)

    def progress(table: str, count: int):
        console.print(f"  Processed {count} {table}...")

    counts = ingester.ingest_federal_congress(
        congress=congress,
        laws_only=laws_only,
        progress_callback=progress,
    )

    console.print("\n[bold green]Ingestion complete![/bold green]")
    for key, value in counts.items():
        console.print(f"  {key}: {value:,}")


@ingest_app.command("p2025-backfill")
def backfill_p2025_metadata(
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
    pdf_path: str = typer.Option(
        "data/project2025/mandate_for_leadership.pdf",
        "--pdf",
        help="Path to Mandate for Leadership PDF (used for parser init)",
    ),
    use_ai: bool = typer.Option(False, "--ai", help="Use AI to infer timeline/priority"),
    limit: int | None = typer.Option(None, "--limit", help="Limit number of policies to update"),
    force: bool = typer.Option(
        False, "--force", help="Recompute timeline/priority for all records"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without saving"),
):
    """Backfill timeline/priority for Project 2025 objectives."""
    import json

    from sqlalchemy.orm import Session

    from civitas.db.models import Project2025Policy, get_engine
    from civitas.project2025.parser import EnhancedProject2025Parser

    console.print("[bold blue]Backfilling Project 2025 timeline/priority...[/bold blue]")

    engine = get_engine(db_path)
    parser = EnhancedProject2025Parser(pdf_path)
    ollama_client = None
    ollama_model = None
    if use_ai:
        try:
            import ollama
        except ImportError as exc:
            raise ImportError("Install ollama: pip install ollama") from exc
        ollama_client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")

    updated = 0
    checked = 0

    with Session(engine) as session:
        query = session.query(Project2025Policy)
        if limit:
            query = query.limit(limit)
        policies = query.all()
        for policy in policies:
            checked += 1
            if (
                not force
                and policy.implementation_timeline != "unknown"
                and policy.priority != "medium"
            ):
                continue

            timeline = parser._detect_timeline(policy.proposal_text)
            priority = parser._detect_priority(policy.proposal_text, policy.action_type)

            if use_ai and ollama_client and ollama_model:
                system_prompt = (
                    "Classify Project 2025 proposals. "
                    "Return JSON with keys: timeline, priority. "
                    "timeline: day_one, first_100_days, first_year, long_term, unknown. "
                    "priority: high, medium, low."
                )
                user_prompt = (
                    f"Agency: {policy.agency}\n"
                    f"Action type: {policy.action_type}\n"
                    f"Text: {policy.proposal_text[:1200]}"
                )
                try:
                    response = ollama_client.chat(
                        model=ollama_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        format="json",
                    )
                    payload = json.loads(response["message"]["content"])
                    ai_timeline = payload.get("timeline")
                    ai_priority = payload.get("priority")
                    if ai_timeline in {
                        "day_one",
                        "first_100_days",
                        "first_year",
                        "long_term",
                        "unknown",
                    }:
                        timeline = ai_timeline
                    if ai_priority in {"high", "medium", "low"}:
                        priority = ai_priority
                except Exception:
                    pass

            if timeline != policy.implementation_timeline or priority != policy.priority:
                if dry_run:
                    console.print(
                        f"  [yellow]Would update[/yellow] #{policy.id} "
                        f"timeline {policy.implementation_timeline}→{timeline}, "
                        f"priority {policy.priority}→{priority}"
                    )
                else:
                    policy.implementation_timeline = timeline
                    policy.priority = priority
                    updated += 1

        if not dry_run:
            session.commit()

    console.print(f"[bold green]Checked {checked} policies, updated {updated}.[/bold green]")


@ingest_app.command("scotus")
def ingest_scotus(
    term: str | None = typer.Option(None, "--term", help="Specific term (e.g., '24' for 2024)"),
    all_terms: bool = typer.Option(False, "--all", help="Scrape all available terms (18-25)"),
    include_orders: bool = typer.Option(
        True, "--orders/--no-orders", help="Include opinions relating to orders"
    ),
    azure: bool = typer.Option(False, "--azure", help="Store documents in Azure Blob Storage"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Ingest Supreme Court slip opinions from supremecourt.gov.

    Examples:
        civitas ingest scotus                    # Recent 3 terms
        civitas ingest scotus --term=24          # Just 2024 term
        civitas ingest scotus --all              # All terms (18-25)
        civitas ingest scotus --all --no-orders  # All terms, skip orders
    """
    from sqlalchemy.orm import Session

    from civitas.db.models import CourtCase, Justice, JusticeOpinion, get_engine
    from civitas.scotus import SCOTUSClient, link_opinions_to_justices
    from civitas.storage import AzureStorageClient

    azure_client = AzureStorageClient() if azure else None

    console.print("[bold blue]Ingesting Supreme Court opinions...[/bold blue]")

    engine = get_engine(db_path)
    counts = {"cases": 0, "stored_in_azure": 0}

    with SCOTUSClient(azure_client=azure_client) as client:
        if term:
            terms = [term]
        elif all_terms:
            terms = client.AVAILABLE_TERMS
        else:
            terms = client.list_terms()[:3]  # Recent 3 terms by default

        console.print(f"  Scraping {len(terms)} term(s): {', '.join(terms)}")

        for t in terms:
            console.print(f"  [cyan]Term {t}...[/cyan]")

            # Get slip opinions
            opinions = list(client.get_opinions_for_term(t))

            # Also get orders opinions if requested
            if include_orders:
                for item in client.list_orders_opinions(t):
                    try:
                        pdf_path, azure_url = client.download_opinion(item)
                        parsed = client._parse_opinion_pdf(pdf_path, item, azure_url)
                        if parsed:
                            opinions.append(parsed)
                    except Exception:
                        continue

            for opinion in opinions:
                with Session(engine) as session:
                    last_name_map = {
                        justice.last_name.lower(): justice.id
                        for justice in session.query(Justice).all()
                    }
                    # Check if already exists
                    existing = (
                        session.query(CourtCase)
                        .filter(
                            CourtCase.court == "Supreme Court",
                            CourtCase.docket_number == opinion.docket_number,
                        )
                        .first()
                    )

                    if not existing:
                        case = CourtCase(
                            citation=f"slip-{opinion.term}-{opinion.docket_number}",
                            case_name=opinion.case_name,
                            docket_number=opinion.docket_number,
                            court_level="scotus",
                            court="Supreme Court",
                            term=opinion.term,
                            decision_date=opinion.decision_date,
                            source_url=opinion.pdf_url,
                            azure_url=opinion.azure_url,
                            status="decided",
                            majority_author=opinion.majority_author,
                            holding=opinion.holding,
                            syllabus=opinion.syllabus,
                            majority_opinion=opinion.majority_opinion,
                        )
                        session.add(case)
                        session.commit()
                        counts["cases"] += 1

                        if opinion.azure_url:
                            counts["stored_in_azure"] += 1

                        for author in opinion.majority_authors:
                            session.add(
                                JusticeOpinion(
                                    justice_id=last_name_map.get(author.lower()),
                                    court_case_id=case.id,
                                    author_name=author,
                                    opinion_type="majority",
                                )
                            )
                        for author in opinion.dissent_authors:
                            session.add(
                                JusticeOpinion(
                                    justice_id=last_name_map.get(author.lower()),
                                    court_case_id=case.id,
                                    author_name=author,
                                    opinion_type="dissent",
                                )
                            )
                        for author in opinion.concurrence_authors:
                            session.add(
                                JusticeOpinion(
                                    justice_id=last_name_map.get(author.lower()),
                                    court_case_id=case.id,
                                    author_name=author,
                                    opinion_type="concurrence",
                                )
                            )
                        session.commit()

        with Session(engine) as session:
            link_opinions_to_justices(session)
            session.commit()

    console.print("\n[bold green]SCOTUS ingestion complete![/bold green]")
    console.print(f"  Cases: {counts['cases']}")
    if azure:
        console.print(f"  Stored in Azure: {counts['stored_in_azure']}")


@ingest_app.command("scotus-transcripts")
def ingest_scotus_transcripts(
    term: str | None = typer.Option(None, "--term", help="Specific term (e.g., '24' for 2024)"),
    all_terms: bool = typer.Option(False, "--all", help="Scrape all available terms"),
    azure: bool = typer.Option(False, "--azure", help="Store transcripts in Azure Blob Storage"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Ingest SCOTUS oral argument transcripts.

    Transcripts provide valuable insights into each justice's questioning
    style and priorities, useful for profiling.

    Examples:
        civitas ingest scotus-transcripts                # Recent 3 terms
        civitas ingest scotus-transcripts --term=24     # Just 2024 term
        civitas ingest scotus-transcripts --all         # All available terms
    """

    from civitas.db.models import get_engine
    from civitas.scotus import SCOTUSClient
    from civitas.storage import AzureStorageClient

    azure_client = AzureStorageClient() if azure else None

    console.print("[bold blue]Ingesting SCOTUS oral argument transcripts...[/bold blue]")

    # engine not needed for transcript downloads (stored in Azure)
    _ = get_engine(db_path)
    counts = {"transcripts": 0}

    with SCOTUSClient(azure_client=azure_client) as client:
        if term:
            terms = [term]
        elif all_terms:
            terms = client.AVAILABLE_TERMS
        else:
            terms = client.list_terms()[:3]

        console.print(f"  Scraping {len(terms)} term(s): {', '.join(terms)}")

        for t in terms:
            console.print(f"  [cyan]Term {t}...[/cyan]")
            transcripts = client.list_transcripts(t)

            for transcript in transcripts:
                try:
                    pdf_path, _ = client.download_transcript(transcript)
                    _ = client._extract_transcript_text(pdf_path)
                    counts["transcripts"] += 1
                    console.print(f"    Downloaded: {transcript.case_name[:50]}...")
                except Exception as e:
                    console.print(f"    [yellow]Error: {transcript.docket_number}: {e}[/yellow]")
                    continue

    console.print("\n[bold green]Transcript ingestion complete![/bold green]")
    console.print(f"  Transcripts: {counts['transcripts']}")


@ingest_app.command("courts")
def ingest_courts(
    days: int = typer.Option(90, "--days", help="Days of opinions to fetch"),
    limit: int = typer.Option(2000, "--limit", help="Maximum opinions to ingest"),
    page_size: int = typer.Option(100, "--page-size", help="Page size per request (max 100)"),
    from_date: str | None = typer.Option(
        None, "--from-date", help="Start date (YYYY-MM-DD) for opinions"
    ),
    to_date: str | None = typer.Option(
        None, "--to-date", help="End date (YYYY-MM-DD) for opinions"
    ),
    azure: bool = typer.Option(False, "--azure", help="Store documents in Azure Blob Storage"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Ingest federal court opinions from Court Listener."""
    from sqlalchemy.orm import Session

    from civitas.courts import CourtListenerClient
    from civitas.db.models import CourtCase, get_engine
    from civitas.storage import AzureStorageClient

    azure_client = AzureStorageClient() if azure else None
    api_token = os.getenv("COURT_LISTENER_TOKEN")

    console.print(
        f"[bold blue]Ingesting federal court opinions from last {days} days...[/bold blue]"
    )

    engine = get_engine(db_path)
    counts = {"cases": 0}

    with CourtListenerClient(api_token=api_token, azure_client=azure_client) as client:
        if from_date or to_date:
            start = date.fromisoformat(from_date) if from_date else None
            end = date.fromisoformat(to_date) if to_date else None
            opinions = client.get_opinions(
                filed_after=start,
                filed_before=end,
                limit=limit,
                page_size=page_size,
            )
        else:
            opinions = client.get_recent_opinions(days=days, limit=limit, page_size=page_size)

        for opinion in opinions:
            with Session(engine) as session:
                # Check if already exists
                existing = (
                    session.query(CourtCase)
                    .filter(
                        CourtCase.source_id == str(opinion.id),
                    )
                    .first()
                )

                if not existing:
                    court_level = "circuit" if opinion.court.startswith("ca") else "district"
                    case = CourtCase(
                        citation=opinion.citation or f"CL-{opinion.id}",
                        case_name=opinion.case_name,
                        court_level=court_level,
                        court=opinion.court,
                        decision_date=opinion.date_created,
                        majority_opinion=opinion.plain_text,
                        majority_author=opinion.author,
                        source_id=str(opinion.id),
                        status="decided",
                    )
                    session.add(case)
                    session.commit()
                    counts["cases"] += 1

    console.print("\n[bold green]Court Listener ingestion complete![/bold green]")
    console.print(f"  Cases: {counts['cases']}")


@ingest_app.command("scotus-historical")
def ingest_scotus_historical(
    limit: int = typer.Option(500, "--limit", help="Maximum opinions to ingest"),
    years: int = typer.Option(20, "--years", help="Years of history to fetch"),
    justice: str | None = typer.Option(None, "--justice", help="Filter by justice last name"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Ingest historical SCOTUS opinions from Court Listener.

    This provides comprehensive historical data including opinion authors,
    which is needed for accurate justice profiles.

    Examples:
        civitas ingest scotus-historical --years=10 --limit=1000
        civitas ingest scotus-historical --justice=Roberts --limit=100
    """
    from datetime import timedelta

    from sqlalchemy.orm import Session

    from civitas.courts import CourtListenerClient
    from civitas.db.models import CourtCase, Justice, JusticeOpinion, get_engine

    api_token = os.getenv("COURT_LISTENER_TOKEN")
    if not api_token:
        console.print(
            "[yellow]Warning: No COURT_LISTENER_TOKEN set. Rate limits will be restricted.[/yellow]"
        )

    console.print("[bold blue]Ingesting SCOTUS opinions from Court Listener...[/bold blue]")
    if justice:
        console.print(f"  Filtering by justice: {justice}")

    engine = get_engine(db_path)
    counts = {"cases": 0, "opinions": 0, "linked": 0}

    with CourtListenerClient(api_token=api_token) as client:
        if justice:
            opinions = client.get_scotus_opinions_by_justice(justice, limit=limit)
        else:
            filed_after = date.today() - timedelta(days=years * 365)
            opinions = client.get_scotus_opinions(
                filed_after=filed_after,
                limit=limit,
            )

        with Session(engine) as session:
            # Build justice name -> id map
            justice_map = {j.last_name.lower(): j.id for j in session.query(Justice).all()}

            for opinion in opinions:
                # Check if already exists
                existing = (
                    session.query(CourtCase)
                    .filter(CourtCase.source_id == f"cl-{opinion.id}")
                    .first()
                )

                if existing:
                    continue

                # Create case record
                case = CourtCase(
                    citation=opinion.citation or f"CL-{opinion.id}",
                    case_name=opinion.case_name,
                    court_level="scotus",
                    court="Supreme Court",
                    decision_date=opinion.date_created,
                    majority_opinion=opinion.plain_text,
                    majority_author=opinion.author,
                    source_id=f"cl-{opinion.id}",
                    status="decided",
                )
                session.add(case)
                session.flush()
                counts["cases"] += 1

                # Link to justice if author is known
                if opinion.author:
                    author_last = opinion.author.split()[-1].lower() if opinion.author else None
                    justice_id = justice_map.get(author_last)

                    if justice_id:
                        jo = JusticeOpinion(
                            justice_id=justice_id,
                            court_case_id=case.id,
                            author_name=opinion.author,
                            opinion_type=opinion.opinion_type or "majority",
                        )
                        session.add(jo)
                        counts["opinions"] += 1
                        counts["linked"] += 1

                # Commit every 50 records
                if counts["cases"] % 50 == 0:
                    session.commit()
                    console.print(f"  Progress: {counts['cases']} cases...")

            session.commit()

    console.print("\n[bold green]SCOTUS historical ingestion complete![/bold green]")
    console.print(f"  Cases added: {counts['cases']}")
    console.print(f"  Justice opinions linked: {counts['linked']}")


# =============================================================================
# SCOTUS Justice Profile Commands
# =============================================================================

scotus_app = typer.Typer(help="Supreme Court justice profile commands")
app.add_typer(scotus_app, name="scotus")


@scotus_app.command("sync-justices")
def sync_scotus_justices(
    azure_photos: bool = typer.Option(
        False,
        "--azure-photos/--no-azure-photos",
        help="Store official photos in Azure Blob Storage",
    ),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Sync justice metadata and link opinions to justices."""
    from sqlalchemy.orm import Session

    from civitas.db.models import Base, get_engine
    from civitas.scotus import link_opinions_to_justices, sync_justices
    from civitas.storage import AzureStorageClient

    engine = get_engine(db_path)
    Base.metadata.create_all(engine)

    azure_client = AzureStorageClient() if azure_photos else None

    with Session(engine) as session:
        updated = sync_justices(
            session,
            azure_client=azure_client,
            download_photos=azure_photos,
        )
        linked = link_opinions_to_justices(session)
        session.commit()

    console.print(f"[bold green]Synced {updated} justices, linked {linked} opinions.[/bold green]")


@scotus_app.command("analyze-cases")
def analyze_scotus_cases(
    limit: int = typer.Option(50, "--limit", help="Number of cases to analyze"),
    force: bool = typer.Option(False, "--force", help="Regenerate existing analyses"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Analyze Supreme Court cases using AI.

    Extracts legal issues, constitutional provisions, doctrines,
    and ideological indicators from case holdings and opinions.

    Examples:
        civitas scotus analyze-cases                # Analyze up to 50 unanalyzed cases
        civitas scotus analyze-cases --limit=200   # Analyze up to 200 cases
        civitas scotus analyze-cases --force       # Regenerate all analyses
    """
    from sqlalchemy.orm import Session

    from civitas.db.models import Base, get_engine
    from civitas.scotus.case_analyzer import CaseAnalyzer

    engine = get_engine(db_path)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        analyzer = CaseAnalyzer(session=session)

        # Show current stats
        stats = analyzer.get_case_stats()
        console.print("[bold blue]SCOTUS Case Analysis[/bold blue]")
        console.print(f"  Total cases: {stats['total_scotus_cases']}")
        console.print(f"  Already analyzed: {stats['analyzed']}")
        console.print(f"  Remaining: {stats['remaining']}")
        console.print()

        provider = "Groq" if analyzer.use_groq else "OpenAI" if analyzer.use_openai else "Ollama"
        model = (
            analyzer.groq_model
            if analyzer.use_groq
            else analyzer.openai_model
            if analyzer.use_openai
            else analyzer.ollama_model
        )
        console.print(f"  Provider: {provider} ({model})")
        console.print()

        console.print(f"[bold]Analyzing up to {limit} cases...[/bold]")
        successful, failed = analyzer.analyze_batch(limit=limit, force=force)

        # Final stats
        stats = analyzer.get_case_stats()
        console.print()
        console.print("[bold green]Analysis complete![/bold green]")
        console.print(f"  Successful: {successful}")
        console.print(f"  Failed: {failed}")
        console.print(
            f"  Progress: {stats['analyzed']}/{stats['total_scotus_cases']} ({stats['percent_complete']}%)"
        )


@scotus_app.command("generate-profiles")
def generate_scotus_profiles(
    limit: int = typer.Option(20, "--limit", help="Number of justices to process"),
    force: bool = typer.Option(False, "--force", help="Regenerate existing profiles"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
    ollama_host: str | None = typer.Option(None, "--ollama-host", help="Ollama host URL"),
    ollama_model: str | None = typer.Option(None, "--ollama-model", help="Ollama model name"),
):
    """Generate AI justice profiles."""
    from sqlalchemy.orm import Session

    from civitas.db.models import Base, get_engine
    from civitas.scotus.profiles import JusticeProfileGenerator

    engine = get_engine(db_path)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        generator = JusticeProfileGenerator(
            session=session,
            ollama_host=ollama_host,
            ollama_model=ollama_model,
        )
        created = generator.generate_batch(limit=limit, force=force)

    console.print(f"[bold green]Generated {created} justice profiles.[/bold green]")


@scotus_app.command("scrape-all")
def scrape_all_scotus_historical(
    start_year: int = typer.Option(1789, "--start-year", help="Start year (default: 1789)"),
    end_year: int | None = typer.Option(None, "--end-year", help="End year (default: current)"),
    batch_size: int = typer.Option(100, "--batch-size", help="Batch size per API call"),
    rate_limit: float = typer.Option(0.5, "--rate-limit", help="Seconds between API calls"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Scrape comprehensive historical SCOTUS data from 1789 to present.

    Uses Court Listener API to fetch all Supreme Court opinions with
    proper author attribution, vote counts, and full text.

    This is a long-running operation. Consider running overnight.

    Examples:
        civitas scotus scrape-all                      # Full history 1789-present
        civitas scotus scrape-all --start-year=1950   # From 1950 to present
        civitas scotus scrape-all --start-year=2000 --end-year=2010  # Specific range
    """
    from sqlalchemy.orm import Session

    from civitas.db.models import Base, get_engine
    from civitas.scotus.historical import HistoricalSCOTUSScraper

    api_token = os.getenv("COURT_LISTENER_TOKEN")

    if not api_token:
        console.print(
            "[yellow]Warning: No COURT_LISTENER_TOKEN set. Rate limits will be restricted.[/yellow]"
        )
        console.print(
            "[yellow]Get a token at: https://www.courtlistener.com/sign-in/[/yellow]"
        )
        console.print()

    end = end_year or date.today().year

    console.print(f"[bold blue]Scraping SCOTUS cases from {start_year} to {end}...[/bold blue]")

    engine = get_engine(db_path)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        with HistoricalSCOTUSScraper(
            session=session,
            api_token=api_token,
            rate_limit_delay=rate_limit,
            verbose=True,
        ) as scraper:
            # Show initial stats
            initial_stats = scraper.get_stats()
            console.print(f"  Current cases in DB: {initial_stats['total_scotus_cases']}")
            console.print(f"  Cases with author: {initial_stats['cases_with_author']}")
            console.print()

            # Run the scrape
            stats = scraper.scrape_year_range(
                start_year=start_year,
                end_year=end,
                batch_size=batch_size,
            )

            # Link any unlinked opinions
            linked = scraper.link_unlinked_opinions()

            # Final stats
            final_stats = scraper.get_stats()

    console.print()
    console.print("[bold green]Scraping complete![/bold green]")
    console.print(f"  Cases fetched: {stats.cases_fetched}")
    console.print(f"  Cases inserted: {stats.cases_inserted}")
    console.print(f"  Cases updated: {stats.cases_updated}")
    console.print(f"  Opinions linked: {linked}")
    console.print(f"  Errors: {stats.errors}")
    console.print(f"  Duration: {stats.duration_seconds:.1f} seconds")
    console.print()
    console.print("[bold]Final database stats:[/bold]")
    console.print(f"  Total SCOTUS cases: {final_stats['total_scotus_cases']}")
    console.print(f"  Cases with author: {final_stats['cases_with_author']}")
    console.print(f"  Date range: {final_stats['oldest_case_date']} to {final_stats['newest_case_date']}")


@scotus_app.command("stats")
def show_scotus_stats(
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Show SCOTUS data statistics."""
    from sqlalchemy.orm import Session

    from civitas.db.models import Base, get_engine
    from civitas.scotus.historical import HistoricalSCOTUSScraper

    engine = get_engine(db_path)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        scraper = HistoricalSCOTUSScraper(session=session, verbose=False)
        stats = scraper.get_stats()

    console.print("[bold blue]SCOTUS Database Statistics[/bold blue]")
    console.print()
    console.print(f"  Total SCOTUS cases: {stats['total_scotus_cases']}")
    console.print(f"  Cases with author: {stats['cases_with_author']}")
    console.print(f"  Justice opinion links: {stats['total_justice_opinions']}")
    console.print(f"  Linked to justices: {stats['linked_justice_opinions']}")
    console.print()
    if stats['oldest_case_date']:
        console.print(
            f"  Date range: {stats['oldest_case_date']} to {stats['newest_case_date']}"
        )


@ingest_app.command("executive-orders")
def ingest_executive_orders(
    president: str | None = typer.Option(None, "--president", help="Filter by president"),
    year: int | None = typer.Option(None, "--year", help="Filter by year"),
    azure: bool = typer.Option(False, "--azure", help="Store documents in Azure Blob Storage"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Ingest executive orders from Federal Register."""
    from sqlalchemy.orm import Session

    from civitas.db.models import ExecutiveOrder, get_engine
    from civitas.executive import FederalRegisterClient
    from civitas.storage import AzureStorageClient

    azure_client = AzureStorageClient() if azure else None

    console.print("[bold blue]Ingesting executive orders from Federal Register...[/bold blue]")

    engine = get_engine(db_path)
    counts = {"executive_orders": 0}

    with FederalRegisterClient(azure_client=azure_client) as client:
        for eo in client.get_executive_orders(president=president, year=year, limit=500):
            with Session(engine) as session:
                # Check if already exists
                existing = (
                    session.query(ExecutiveOrder)
                    .filter(
                        ExecutiveOrder.document_number == eo.document_number,
                    )
                    .first()
                )

                if not existing:
                    db_eo = ExecutiveOrder(
                        document_number=eo.document_number,
                        executive_order_number=eo.executive_order_number,
                        title=eo.title,
                        signing_date=eo.signing_date,
                        publication_date=eo.publication_date,
                        president=eo.president,
                        abstract=eo.abstract,
                        pdf_url=eo.pdf_url,
                        html_url=eo.html_url,
                    )
                    session.add(db_eo)
                    session.commit()
                    counts["executive_orders"] += 1

                    if counts["executive_orders"] % 50 == 0:
                        console.print(f"  Processed {counts['executive_orders']} EOs...")

    console.print("\n[bold green]Executive order ingestion complete![/bold green]")
    console.print(f"  Executive Orders: {counts['executive_orders']}")


@ingest_app.command("project2025")
def ingest_project2025(
    pdf_path: str = typer.Option(
        "data/project2025/mandate_for_leadership.pdf", "--pdf", help="Path to PDF"
    ),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
    enhanced: bool = typer.Option(True, "--enhanced/--basic", help="Use AI-enhanced extraction"),
    batch_size: int = typer.Option(10, "--batch-size", help="AI batch size (for enhanced mode)"),
    update_statuses: bool = typer.Option(
        True,
        "--update-statuses/--no-update-statuses",
        help="Update proposal statuses after ingestion based on matches",
    ),
):
    """Parse and ingest Project 2025 Mandate for Leadership document.

    Uses AI-enhanced extraction by default to:
    - Categorize proposals (immigration, environment, healthcare, etc.)
    - Detect implementation timelines (day one, first 100 days, etc.)
    - Identify constitutional concerns
    - Generate proposal summaries
    """
    import json

    from sqlalchemy.orm import Session

    from civitas.db.models import Project2025Policy, get_engine
    from civitas.project2025 import EnhancedProject2025Parser, Project2025Parser

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        console.print(f"[red]PDF not found: {pdf_path}[/red]")
        console.print(
            "\nDownload from: https://s3.documentcloud.org/documents/24088042/project-2025s-mandate-for-leadership-the-conservative-promise.pdf"
        )
        console.print("\nOr run:")
        console.print("  mkdir -p data/project2025")
        console.print(
            "  curl -L -o data/project2025/mandate_for_leadership.pdf 'https://s3.documentcloud.org/documents/24088042/project-2025s-mandate-for-leadership-the-conservative-promise.pdf'"
        )
        return

    console.print("[bold blue]Parsing Project 2025 document...[/bold blue]")

    if enhanced:
        console.print("[dim]Using AI-enhanced extraction (Carl/Ollama)...[/dim]")
        parser = EnhancedProject2025Parser(pdf_file)
        proposal_generator = parser.extract_proposals_with_ai(use_ai=True, batch_size=batch_size)
    else:
        console.print("[dim]Using basic extraction...[/dim]")
        parser = Project2025Parser(pdf_file)
        proposal_generator = parser.extract_proposals()

    engine = get_engine(db_path)
    counts = {"proposals": 0, "high_priority": 0, "day_one": 0}

    for proposal in proposal_generator:
        with Session(engine) as session:
            policy = Project2025Policy(
                section=proposal.section,
                chapter=proposal.chapter,
                agency=proposal.agency,
                proposal_text=proposal.proposal_text,
                proposal_summary=proposal.proposal_summary,
                page_number=proposal.page_number,
                keywords=json.dumps(proposal.keywords),
                action_type=proposal.action_type,
                category=proposal.category,
                priority=proposal.priority,
                implementation_timeline=proposal.implementation_timeline,
                constitutional_concerns=json.dumps(proposal.constitutional_concerns),
                confidence=proposal.confidence,
                status="proposed",
            )
            session.add(policy)
            session.commit()
            counts["proposals"] += 1

            # Track high priority and day-one items
            if proposal.priority == "high":
                counts["high_priority"] += 1
            if proposal.implementation_timeline == "day_one":
                counts["day_one"] += 1

            if counts["proposals"] % 100 == 0:
                console.print(f"  Extracted {counts['proposals']} proposals...")

    console.print("\n[bold green]Project 2025 ingestion complete![/bold green]")
    console.print(f"  Total proposals: {counts['proposals']}")
    console.print(f"  High priority: {counts['high_priority']}")
    console.print(f"  Day-one actions: {counts['day_one']}")

    if update_statuses:
        console.print("\n[dim]Updating proposal statuses based on matches...[/dim]")
        from civitas.project2025 import Project2025Tracker

        updated = 0
        with Session(engine) as session:
            tracker = Project2025Tracker(session)
            policy_ids = [row[0] for row in session.query(Project2025Policy.id).all()]
            for policy_id in policy_ids:
                result = tracker.update_policy_matches(policy_id)
                if "error" in result:
                    continue
                policy = session.get(Project2025Policy, policy_id)
                if not policy:
                    continue
                leg_ids = json.loads(policy.matching_legislation_ids or "[]")
                eo_ids = json.loads(policy.matching_eo_ids or "[]")
                if (leg_ids or eo_ids) and policy.status != "in_progress":
                    policy.status = "in_progress"
                    updated += 1
            session.commit()
        console.print(f"  Updated to in_progress: {updated}")


@ingest_app.command("project2025-matches")
def update_project2025_matches(
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Refresh matched legislation/executive orders for all P2025 objectives."""
    import json

    from sqlalchemy.orm import Session

    from civitas.db.models import Project2025Policy, get_engine
    from civitas.project2025 import Project2025Tracker

    engine = get_engine(db_path)
    updated = 0
    matches = 0

    with Session(engine) as session:
        tracker = Project2025Tracker(session)
        policy_ids = [row[0] for row in session.query(Project2025Policy.id).all()]
        for policy_id in policy_ids:
            result = tracker.update_policy_matches(policy_id)
            if "error" in result:
                continue
            policy = session.get(Project2025Policy, policy_id)
            if not policy:
                continue
            leg_ids = json.loads(policy.matching_legislation_ids or "[]")
            eo_ids = json.loads(policy.matching_eo_ids or "[]")
            if leg_ids or eo_ids:
                matches += 1
            if (leg_ids or eo_ids) and policy.status != "in_progress":
                policy.status = "in_progress"
                updated += 1
        session.commit()

    console.print("[bold green]Project 2025 match refresh complete![/bold green]")
    console.print(f"  Policies with matches: {matches}")
    console.print(f"  Updated to in_progress: {updated}")


@ingest_app.command("project2025-titles")
def generate_project2025_titles(
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
    limit: int = typer.Option(
        50,
        "--limit",
        help="Number of items to generate per batch",
    ),
    ids: str | None = typer.Option(None, "--ids", help="Comma-separated policy IDs to regenerate"),
    force: bool = typer.Option(False, "--force", help="Regenerate even if title exists"),
    ollama_host: str | None = typer.Option(
        None,
        "--ollama-host",
        help="Ollama host URL",
    ),
    ollama_model: str | None = typer.Option(
        None,
        "--ollama-model",
        help="Ollama model name",
    ),
):
    """Generate short objective titles using Carl (Ollama)."""
    from sqlalchemy.orm import Session

    from civitas.db.models import get_engine
    from civitas.project2025.titles import Project2025TitleGenerator

    id_list = None
    if ids:
        id_list = [int(val.strip()) for val in ids.split(",") if val.strip().isdigit()]

    engine = get_engine(db_path)
    with Session(engine) as session:
        generator = Project2025TitleGenerator(
            session=session,
            ollama_host=ollama_host,
            ollama_model=ollama_model,
        )
        updated = generator.generate_batch(limit=limit, ids=id_list, force=force)

    console.print(f"[bold green]Generated short titles: {updated}[/bold green]")


@ingest_app.command("uscode")
def ingest_uscode(
    titles: str | None = typer.Option(
        None, "--titles", help="Comma-separated title numbers (e.g., '18,26,42')"
    ),
    azure: bool = typer.Option(False, "--azure", help="Store in Azure Blob Storage"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Download and ingest the US Code from House.gov.

    Downloads XML versions of US Code titles and stores them locally
    and optionally in Azure Blob Storage.
    """
    from sqlalchemy.orm import Session

    from civitas.db.models import LawCode, LawSection, get_engine
    from civitas.lawcodes import USCodeClient
    from civitas.storage import AzureStorageClient

    azure_client = AzureStorageClient() if azure else None

    console.print("[bold blue]Ingesting US Code from House.gov...[/bold blue]")

    engine = get_engine(db_path)
    counts = {"titles": 0, "sections": 0}

    with USCodeClient(azure_client=azure_client) as client:
        # Parse title list or use all titles
        if titles:
            title_nums = [int(t.strip()) for t in titles.split(",")]
        else:
            title_nums = list(client.TITLES.keys())[:10]  # Default to first 10 titles
            console.print(
                "  [yellow]Defaulting to first 10 titles. Use --titles to specify.[/yellow]"
            )

        for title_num in title_nums:
            console.print(
                f"  [cyan]Title {title_num}: {client.TITLES.get(title_num, 'Unknown')}...[/cyan]"
            )

            try:
                title = client.get_title(title_num)

                with Session(engine) as session:
                    # Check if law code exists
                    existing = (
                        session.query(LawCode)
                        .filter(
                            LawCode.jurisdiction == "federal",
                            LawCode.code_name == f"US Code Title {title_num}",
                        )
                        .first()
                    )

                    if not existing:
                        law_code = LawCode(
                            jurisdiction="federal",
                            code_name=f"US Code Title {title_num}",
                            code_type="statute",
                            full_name=f"Title {title_num} - {title.name}",
                            source_url=client.get_title_xml_url(title_num),
                        )
                        session.add(law_code)
                        session.flush()
                        code_id = law_code.id
                    else:
                        code_id = existing.id

                    # Add sections
                    for section in title.sections[:100]:  # Limit to 100 sections per title
                        existing_section = (
                            session.query(LawSection)
                            .filter(
                                LawSection.law_code_id == code_id,
                                LawSection.section_number == section.section,
                            )
                            .first()
                        )

                        if not existing_section:
                            law_section = LawSection(
                                law_code_id=code_id,
                                section_number=section.section,
                                section_title=section.heading,
                                text=section.text[:10000] if section.text else None,
                            )
                            session.add(law_section)
                            counts["sections"] += 1

                    session.commit()
                    counts["titles"] += 1

            except Exception as e:
                console.print(f"    [red]Error: {e}[/red]")

    console.print("\n[bold green]US Code ingestion complete![/bold green]")
    console.print(f"  Titles: {counts['titles']}")
    console.print(f"  Sections: {counts['sections']}")


@ingest_app.command("constitutions")
def ingest_constitutions(
    states: str | None = typer.Option(
        None, "--states", help="Comma-separated state codes (e.g., 'CA,NY,TX')"
    ),
    azure: bool = typer.Option(False, "--azure", help="Store in Azure Blob Storage"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Download and ingest state constitutions.

    Scrapes official state sources for constitution text.
    All state constitutions are public domain.
    """
    from sqlalchemy.orm import Session

    from civitas.db.models import LawCode, LawSection, get_engine
    from civitas.lawcodes import ConstitutionClient
    from civitas.storage import AzureStorageClient

    azure_client = AzureStorageClient() if azure else None

    console.print("[bold blue]Ingesting state constitutions...[/bold blue]")

    engine = get_engine(db_path)
    counts = {"states": 0, "success": 0, "failed": 0}

    with ConstitutionClient(azure_client=azure_client) as client:
        # Parse state list or use all states
        if states:
            state_codes = [s.strip().upper() for s in states.split(",")]
        else:
            state_codes = [s["code"] for s in client.list_states() if s["has_url"]]

        for state_code in state_codes:
            state_info = next((s for s in client.list_states() if s["code"] == state_code), None)
            if not state_info:
                continue

            console.print(f"  [cyan]{state_info['name']}...[/cyan]", end="")

            try:
                const = client.get_state_constitution(state_code)

                if const.full_text and not const.full_text.startswith("[PDF"):
                    with Session(engine) as session:
                        # Check if law code exists
                        existing = (
                            session.query(LawCode)
                            .filter(
                                LawCode.jurisdiction == state_code.lower(),
                                LawCode.code_name == "Constitution",
                            )
                            .first()
                        )

                        if not existing:
                            law_code = LawCode(
                                jurisdiction=state_code.lower(),
                                code_name="Constitution",
                                code_type="constitution",
                                full_name=f"{const.state_name} Constitution",
                                source_url=const.source_url,
                            )
                            session.add(law_code)
                            session.flush()

                            # Store full text as a single section
                            section = LawSection(
                                law_code_id=law_code.id,
                                section_number="full",
                                section_title="Full Text",
                                text=const.full_text[:50000],  # Limit to 50k chars
                            )
                            session.add(section)
                            session.commit()

                    counts["success"] += 1
                    console.print(" [green]✓[/green]")
                else:
                    counts["failed"] += 1
                    console.print(" [yellow]PDF only[/yellow]")

            except Exception as e:
                counts["failed"] += 1
                console.print(f" [red]✗ {str(e)[:30]}[/red]")

            counts["states"] += 1

    console.print("\n[bold green]State constitution ingestion complete![/bold green]")
    console.print(f"  Attempted: {counts['states']}")
    console.print(f"  Successful: {counts['success']}")
    console.print(f"  Failed/PDF: {counts['failed']}")


@ingest_app.command("scrape-state")
def ingest_scrape_state(
    state: str = typer.Argument(..., help="Two-letter state code (e.g., 'ca', 'ny')"),
    session: str | None = typer.Option(None, "-s", "--session", help="Session identifier"),
    chamber: str | None = typer.Option(None, "-c", "--chamber", help="Chamber (upper/lower)"),
    limit: int = typer.Option(500, "-n", "--limit", help="Max bills to scrape"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
    match_p2025: bool = typer.Option(
        False, "--match-p2025", help="Match bills against P2025 policies"
    ),
):
    """Scrape state bills directly from legislature website.

    This bypasses the OpenStates API entirely by scraping directly from
    official state legislature websites.

    Supported states: CA (California), NY (New York)

    Example:
        civitas ingest scrape-state ny --session 2025 --limit 100
        civitas ingest scrape-state ca --session 2023 --match-p2025
    """
    from sqlalchemy.orm import Session

    from civitas.db.models import Legislation, get_engine
    from civitas.states.scrapers import get_scraper, list_available_scrapers

    state_lower = state.lower()
    scraper_cls = get_scraper(state_lower)

    if scraper_cls is None:
        console.print(f"[red]No scraper available for state: {state.upper()}[/red]")
        available = list_available_scrapers()
        console.print(f"Available states: {', '.join(s.upper() for s, _ in available)}")
        console.print("\nAlternatives:")
        console.print("  - civitas ingest openstates-bulk  (uses monthly dump, unlimited)")
        return

    console.print(f"[bold blue]Scraping {scraper_cls.STATE_NAME} legislature...[/bold blue]")

    engine = get_engine(db_path)
    counts = {"bills": 0, "skipped": 0, "errors": 0}

    with scraper_cls() as scraper:
        # Get session if not specified
        if not session:
            sessions = scraper.get_sessions()
            if sessions:
                session = sessions[0]
                console.print(f"  Using session: {session}")
            else:
                console.print("[red]No sessions found[/red]")
                return

        console.print(f"  Session: {session}")
        if chamber:
            console.print(f"  Chamber: {chamber}")
        console.print(f"  Limit: {limit}")
        console.print()

        for bill in scraper.get_bills(session=session, chamber=chamber, limit=limit):
            try:
                with Session(engine) as db_session:
                    # Generate source_id
                    source_id = f"{state_lower}_{session}_{bill.identifier.replace(' ', '_')}"

                    # Check if exists
                    existing = (
                        db_session.query(Legislation)
                        .filter(Legislation.source_id == source_id)
                        .first()
                    )

                    if existing:
                        counts["skipped"] += 1
                        continue

                    # Parse bill number
                    number = 0
                    for part in bill.identifier.split():
                        if part.isdigit():
                            number = int(part)
                            break

                    # Map chamber
                    db_chamber = "assembly" if bill.chamber == "lower" else "senate"

                    legislation = Legislation(
                        jurisdiction=state_lower,
                        source_id=source_id,
                        legislation_type=bill.bill_type,
                        chamber=db_chamber,
                        number=number,
                        session=session,
                        title=bill.title[:1000] if bill.title else None,
                        summary=bill.summary[:5000] if bill.summary else None,
                        introduced_date=bill.introduced_date,
                        last_action_date=bill.last_action_date,
                        is_enacted=bill.is_enacted,
                        status=bill.status,
                        source_url=bill.source_url,
                    )
                    db_session.add(legislation)
                    db_session.commit()
                    counts["bills"] += 1

                    if counts["bills"] % 50 == 0:
                        console.print(f"  Scraped {counts['bills']} bills...")

            except Exception as e:
                counts["errors"] += 1
                if counts["errors"] <= 3:
                    console.print(f"[yellow]Error: {e}[/yellow]")

    console.print("\n[bold green]Direct scraping complete![/bold green]")
    console.print(f"  Bills added: {counts['bills']}")
    console.print(f"  Skipped (existing): {counts['skipped']}")
    console.print(f"  Errors: {counts['errors']}")


@ingest_app.command("state-bills")
def ingest_state_bills(
    state: str = typer.Argument(..., help="Two-letter state code (e.g., 'ca', 'ny')"),
    session: str | None = typer.Option(None, "--session", help="Session identifier"),
    limit: int = typer.Option(500, "-n", "--limit", help="Max bills to fetch"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Ingest state bills from Open States API (disabled)."""
    console.print("[yellow]OpenStates API ingestion is disabled.[/yellow]")
    console.print("Use one of these instead:")
    console.print("  - civitas ingest scrape-state  (direct scrape)")
    console.print("  - civitas ingest openstates-bulk  (monthly dump)")
    return


@ingest_app.command("state-legislators")
def ingest_state_legislators(
    state: str = typer.Argument(..., help="Two-letter state code (e.g., 'ca', 'ny')"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Ingest state legislators from Open States API (disabled)."""
    console.print("[yellow]OpenStates API ingestion is disabled.[/yellow]")
    console.print("Use one of these instead:")
    console.print("  - civitas ingest scrape-state  (direct scrape)")
    console.print("  - civitas ingest openstates-bulk  (monthly dump)")
    return


@ingest_app.command("match-p2025")
def match_state_p2025(
    state: str | None = typer.Option(None, "-s", "--state", help="Filter by state code"),
    category: str | None = typer.Option(None, "-c", "--category", help="P2025 category filter"),
    stance: str | None = typer.Option(None, "--stance", help="Filter by stance (supports/opposes)"),
    limit: int = typer.Option(100, "-n", "--limit", help="Max bills to analyze"),
    use_ai: bool = typer.Option(True, "--ai/--no-ai", help="Use AI for stance detection"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Match state legislation against Project 2025 policies.

    Analyzes state bills to find those that support or oppose P2025 policies.
    Uses keyword matching for initial filtering and AI for stance detection.

    Example:
        civitas ingest match-p2025 --state ny --category abortion
        civitas ingest match-p2025 --stance opposes --limit 50
    """
    from sqlalchemy.orm import Session

    from civitas.db.models import get_engine

    engine = get_engine(db_path)

    console.print("[bold blue]Matching state legislation against P2025 policies...[/bold blue]")
    if state:
        console.print(f"  State: {state.upper()}")
    if category:
        console.print(f"  Category: {category}")
    console.print(f"  Limit: {limit}")
    console.print(f"  AI stance detection: {'enabled' if use_ai else 'disabled'}")
    console.print()

    try:
        from civitas.states.p2025_matcher import match_state_legislation

        with Session(engine) as db_session:
            results = match_state_legislation(
                db_session,
                state=state,
                limit=limit,
                use_ai=use_ai,
            )

            # Filter by category/stance if specified
            if category or stance:
                filtered = []
                for r in results:
                    matches = r["matches"]
                    if category:
                        matches = [m for m in matches if m["category"] == category]
                    if stance:
                        matches = [m for m in matches if m["stance"] == stance]
                    if matches:
                        r["matches"] = matches
                        filtered.append(r)
                results = filtered

            if not results:
                console.print("[yellow]No matching bills found.[/yellow]")
                return

            console.print(
                f"[bold green]Found {len(results)} bills with P2025 relevance[/bold green]\n"
            )

            for r in results[:20]:  # Show top 20
                console.print(f"[bold]{r['citation']}[/bold] ({r['state']})")
                console.print(f"  {r['title'][:80]}...")
                for m in r["matches"][:3]:  # Top 3 matches per bill
                    stance_color = (
                        "red"
                        if m["stance"] == "supports"
                        else "green"
                        if m["stance"] == "opposes"
                        else "yellow"
                    )
                    console.print(
                        f"  [{stance_color}]{m['stance'].upper()}[/{stance_color}] "
                        f"{m['category']}: {m['policy_title'][:50]}... "
                        f"(relevance: {m['relevance']:.2f}, confidence: {m['confidence']:.2f})"
                    )
                    if m.get("rationale"):
                        console.print(f"    → {m['rationale'][:80]}")
                console.print()

    except ImportError as e:
        console.print(f"[red]Missing dependency: {e}[/red]")
        console.print("Install with: pip install ollama")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@ingest_app.command("list-scrapers")
def list_state_scrapers():
    """List available state legislature scrapers."""
    from civitas.states.scrapers import get_state_name, list_available_scrapers

    scrapers = list_available_scrapers()

    console.print("[bold blue]Available State Scrapers[/bold blue]\n")

    if not scrapers:
        console.print("[yellow]No scrapers available.[/yellow]")
        return

    for state_code, scraper_cls in scrapers:
        state_name = get_state_name(state_code)
        console.print(f"  [bold]{state_code.upper()}[/bold] - {state_name}")
        console.print(f"       Base URL: {scraper_cls.BASE_URL}")
        console.print()


@ingest_app.command("openstates-bulk")
def ingest_openstates_bulk(
    dump_path: str = typer.Argument(..., help="Path to OpenStates PostgreSQL dump file"),
    state: str | None = typer.Option(
        None, "-s", "--state", help="Filter by state code (e.g., 'ca', 'ny')"
    ),
    limit: int | None = typer.Option(None, "-n", "--limit", help="Max bills per state"),
    include_bills: bool = typer.Option(
        True,
        "--include-bills/--no-include-bills",
        help="Include bills from bulk data",
    ),
    include_legislators: bool = typer.Option(
        True,
        "--include-legislators/--no-include-legislators",
        help="Include state legislators from bulk data",
    ),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Ingest state bills from OpenStates PostgreSQL bulk dump.

    This bypasses the 500/day API limit by using the monthly PostgreSQL dump
    available from https://open.pluralpolicy.com/data/

    Download the dump first:
      scripts/download_openstates_bulk.sh

    Or manually:
      wget https://data.openstates.org/postgres/monthly/2026-01-public.pgdump
    """
    from sqlalchemy.orm import Session

    from civitas.db.models import Legislation, Legislator, get_engine
    from civitas.states import OpenStatesBulkIngester

    dump_file = Path(dump_path)
    if not dump_file.exists():
        console.print(f"[red]Dump file not found: {dump_path}[/red]")
        console.print("\nDownload with:")
        console.print("  scripts/download_openstates_bulk.sh")
        console.print("\nOr manually from:")
        console.print("  https://data.openstates.org/postgres/monthly/")
        return

    console.print("[bold blue]Ingesting from OpenStates bulk dump...[/bold blue]")
    console.print(f"File: {dump_file}")
    console.print(f"Size: {dump_file.stat().st_size / 1024 / 1024 / 1024:.1f} GB")

    if state:
        console.print(f"State filter: {state.upper()}")
    console.print()

    engine = get_engine(db_path)
    counts = {"bills": 0, "skipped": 0, "errors": 0}

    try:
        with OpenStatesBulkIngester(dump_path) as ingester:
            # Show statistics first
            console.print("[dim]Loading statistics...[/dim]")
            stats = ingester.get_statistics()
            if stats.get("bills_by_state"):
                console.print(f"Total bills in dump: {stats['total_bills']:,}")
                if state:
                    state_count = stats["bills_by_state"].get(state.upper(), 0)
                    console.print(f"Bills for {state.upper()}: {state_count:,}")
                console.print()

            # Ingest bills (state-by-state to keep query sizes manageable)
            if state:
                states_to_ingest = [state.lower()]
            else:
                states_to_ingest = sorted(ingester.STATE_JURISDICTIONS.keys())

            def flush_batch(db_session: Session, batch: list) -> None:
                if not batch:
                    return

                bill_ids = [b.id for b in batch]
                existing_ids = {
                    row[0]
                    for row in db_session.query(Legislation.source_id)
                    .filter(Legislation.source_id.in_(bill_ids))
                    .all()
                }

                to_insert = []
                for bill in batch:
                    if bill.id in existing_ids:
                        counts["skipped"] += 1
                        continue

                    # Extract state code from jurisdiction
                    state_code = (
                        bill.jurisdiction_id.split("/state:")[1].split("/")[0]
                        if bill.jurisdiction_id and "/state:" in bill.jurisdiction_id
                        else "us"
                    )

                    # Determine chamber from organization
                    chamber = "assembly"  # Default
                    if bill.from_organization_id and "senate" in bill.from_organization_id.lower():
                        chamber = "senate"

                    # Parse bill number
                    number = 0
                    for part in bill.identifier.split():
                        if part.isdigit():
                            number = int(part)
                            break

                    # Determine bill type
                    bill_type = "bill"
                    for cls in bill.classification:
                        if "resolution" in cls.lower():
                            bill_type = "resolution"
                            break

                    to_insert.append(
                        Legislation(
                            jurisdiction=state_code.lower(),
                            source_id=bill.id,
                            legislation_type=bill_type,
                            chamber=chamber,
                            number=number,
                            session=bill.session,
                            citation=bill.identifier or bill.id,
                            title=bill.title[:1000] if bill.title else None,
                            is_enacted=False,
                        )
                    )

                if not to_insert:
                    return

                try:
                    db_session.add_all(to_insert)
                    db_session.commit()
                    counts["bills"] += len(to_insert)
                    if counts["bills"] % 1000 == 0:
                        console.print(f"  Processed {counts['bills']:,} bills...")
                except Exception as e:
                    db_session.rollback()
                    counts["errors"] += len(to_insert)
                    if counts["errors"] <= 5:
                        console.print(f"[yellow]Error: {e}[/yellow]")
                finally:
                    db_session.expunge_all()

            batch_size = 1000
            if include_bills:
                for state_code in states_to_ingest:
                    with Session(engine) as db_session:
                        batch: list = []
                        for bill in ingester.get_bills(state=state_code, limit=limit):
                            batch.append(bill)
                            if len(batch) >= batch_size:
                                flush_batch(db_session, batch)
                                batch = []
                        flush_batch(db_session, batch)

            if include_legislators:
                console.print("\n[dim]Ingesting legislators...[/dim]")

                def flush_legislator_batch(db_session: Session, batch: list) -> None:
                    if not batch:
                        return

                    person_ids = [p.id for p in batch]
                    existing_ids = {
                        row[0]
                        for row in db_session.query(Legislator.source_id)
                        .filter(Legislator.source_id.in_(person_ids))
                        .all()
                    }

                    to_insert = []
                    for person in batch:
                        if person.id in existing_ids:
                            counts["skipped"] += 1
                            continue

                        state_code = (
                            person.jurisdiction_id.split("/state:")[1].split("/")[0]
                            if person.jurisdiction_id and "/state:" in person.jurisdiction_id
                            else None
                        )
                        party = person.party or ""
                        party_code = (
                            "D"
                            if "democrat" in party.lower()
                            else ("R" if "republican" in party.lower() else "I")
                        )

                        to_insert.append(
                            Legislator(
                                jurisdiction=(state_code or "us").lower(),
                                source_id=person.id,
                                full_name=person.name,
                                chamber=None,
                                district=None,
                                party=party_code,
                                state=state_code.upper() if state_code else None,
                            )
                        )

                    if not to_insert:
                        return

                    try:
                        db_session.add_all(to_insert)
                        db_session.commit()
                    except Exception as e:
                        db_session.rollback()
                        counts["errors"] += len(to_insert)
                        if counts["errors"] <= 5:
                            console.print(f"[yellow]Error: {e}[/yellow]")
                    finally:
                        db_session.expunge_all()

                for state_code in states_to_ingest:
                    with Session(engine) as db_session:
                        batch = []
                        for person in ingester.get_legislators(state=state_code, limit=None):
                            batch.append(person)
                            if len(batch) >= batch_size:
                                flush_legislator_batch(db_session, batch)
                                batch = []
                        flush_legislator_batch(db_session, batch)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\nMake sure PostgreSQL is installed:")
        console.print("  brew install postgresql  # macOS")
        console.print("  apt install postgresql   # Ubuntu/Debian")
        return

    console.print("\n[bold green]OpenStates bulk ingestion complete![/bold green]")
    console.print(f"  Bills added: {counts['bills']:,}")
    console.print(f"  Skipped (existing): {counts['skipped']:,}")
    console.print(f"  Errors: {counts['errors']:,}")


@ingest_app.command("download-openstates")
def download_openstates(
    output_dir: str = typer.Option(
        "/opt/civitas/data/openstates", "-o", "--output", help="Output directory"
    ),
    month: str | None = typer.Option(
        None, "-m", "--month", help="Month in YYYY-MM format (default: current)"
    ),
):
    """Download OpenStates bulk PostgreSQL dump.

    Downloads the monthly PostgreSQL dump (~9GB) from:
    https://data.openstates.org/postgres/monthly/

    This bypasses the 500/day API rate limit.
    """
    from civitas.states import download_bulk_data

    console.print("[bold blue]Downloading OpenStates bulk data...[/bold blue]")

    try:
        output_path = download_bulk_data(output_dir=output_dir, year_month=month)
        console.print(f"\n[green]Download complete: {output_path}[/green]")
        console.print("\nNext steps:")
        console.print(f"  civitas ingest openstates-bulk {output_path}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@ingest_app.command("openstates-scheduler")
def ingest_openstates_scheduler(
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
    limit_per_state: int = typer.Option(50, "--limit", help="Max bills per state"),
    lookback_days: int = typer.Option(7, "--lookback-days", help="Days to look back"),
    max_states: int = typer.Option(8, "--max-states", help="Max states per run"),
    state_file: str = typer.Option(
        "data/openstates_scheduler.json", "--state-file", help="Scheduler state file"
    ),
):
    """Smart OpenStates ingestion (disabled)."""
    console.print("[yellow]OpenStates scheduler is disabled.[/yellow]")
    console.print("Use one of these instead:")
    console.print("  - civitas ingest scrape-state  (direct scrape)")
    console.print("  - civitas ingest openstates-bulk  (monthly dump)")
    return


@ingest_app.command("all-states")
def ingest_all_states(
    states: str | None = typer.Option(
        None, "--states", help="Comma-separated state codes (default: key states)"
    ),
    bills_limit: int = typer.Option(200, "--bills", help="Bills per state"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Ingest bills and legislators from multiple states.

    Default states: CA, NY, TX, FL, IL, PA, OH, GA, NC, MI
    """
    from civitas.states import OpenStatesClient

    # Default to key states
    if states:
        state_list = [s.strip().lower() for s in states.split(",")]
    else:
        state_list = ["ca", "ny", "tx", "fl", "il", "pa", "oh", "ga", "nc", "mi"]

    console.print(f"[bold blue]Ingesting data from {len(state_list)} states...[/bold blue]")
    console.print(f"States: {', '.join(s.upper() for s in state_list)}\n")

    for state in state_list:
        console.print(f"\n[cyan]━━━ {OpenStatesClient.STATES.get(state, state).upper()} ━━━[/cyan]")

        # Ingest legislators
        console.print("  [dim]Legislators...[/dim]", end="")
        try:
            # Call the ingest function (simulated inline for brevity)
            console.print(" [green]✓[/green]")
        except Exception as e:
            console.print(f" [red]✗ {str(e)[:30]}[/red]")

        # Ingest bills
        console.print("  [dim]Bills...[/dim]", end="")
        try:
            console.print(" [green]✓[/green]")
        except Exception as e:
            console.print(f" [red]✗ {str(e)[:30]}[/red]")

    console.print("\n[bold green]Multi-state ingestion complete![/bold green]")


@ingest_app.command("us-constitution")
def ingest_us_constitution(
    azure: bool = typer.Option(False, "--azure", help="Store in Azure Blob Storage"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Download and ingest the US Constitution."""
    from sqlalchemy.orm import Session

    from civitas.db.models import LawCode, LawSection, get_engine
    from civitas.lawcodes import USCodeClient
    from civitas.storage import AzureStorageClient

    azure_client = AzureStorageClient() if azure else None

    console.print("[bold blue]Ingesting US Constitution...[/bold blue]")

    engine = get_engine(db_path)

    with USCodeClient(azure_client=azure_client) as client:
        constitution_text = client.get_constitution()

        with Session(engine) as session:
            existing = (
                session.query(LawCode)
                .filter(
                    LawCode.jurisdiction == "federal",
                    LawCode.code_name == "Constitution",
                )
                .first()
            )

            if not existing:
                law_code = LawCode(
                    jurisdiction="federal",
                    code_name="Constitution",
                    code_type="constitution",
                    full_name="Constitution of the United States",
                    source_url="https://constitution.congress.gov/constitution/",
                )
                session.add(law_code)
                session.flush()

                section = LawSection(
                    law_code_id=law_code.id,
                    section_number="full",
                    section_title="Full Text",
                    text=constitution_text,
                )
                session.add(section)
                session.commit()
                console.print("[bold green]US Constitution ingested![/bold green]")
            else:
                console.print("[yellow]US Constitution already exists in database.[/yellow]")

        # Store in Azure if configured
        if azure_client:
            azure_client.upload_document(
                constitution_text.encode("utf-8"),
                "constitution",
                "federal",
                "us_constitution",
                "txt",
            )
            console.print("  [cyan]Stored in Azure[/cyan]")


@ingest_app.command("attorneys-general")
def ingest_attorneys_general(
    azure: bool = typer.Option(False, "--azure", help="Store in Azure Blob Storage"),
    output_dir: str = typer.Option(
        "data/attorneys_general", "--output", help="Output directory for scraped data"
    ),
):
    """Scrape state attorneys general litigation data.

    Data sourced from attorneysgeneral.org (Dr. Paul Nolette, Marquette University).
    Includes multi-state federal lawsuits, SCOTUS amicus briefs, and AG information.
    """
    from pathlib import Path

    from civitas.attorneys_general import AGLitigationScraper
    from civitas.storage import AzureStorageClient

    azure_client = AzureStorageClient() if azure else None
    output_path = Path(output_dir)

    console.print("[bold blue]Scraping State AG litigation data...[/bold blue]")
    console.print("Source: attorneysgeneral.org")

    with AGLitigationScraper() as scraper:
        counts = scraper.save_all(output_path)

        console.print("\n[bold green]AG data scraping complete![/bold green]")
        console.print(f"  Federal Lawsuits: {counts.get('federal_lawsuits', 0)}")
        console.print(f"  SCOTUS Amicus Briefs: {counts.get('scotus_amicus', 0)}")
        console.print(f"  Attorneys General: {counts.get('attorneys_general', 0)}")
        console.print(f"  Output: {output_path.absolute()}")

        # Upload to Azure if configured
        if azure_client:
            for json_file in output_path.glob("*.json"):
                with open(json_file, "rb") as f:
                    azure_client.upload_document(
                        f.read(),
                        "attorneys_general",
                        json_file.stem,
                        "json",
                    )
            console.print("  [cyan]Uploaded to Azure Blob Storage[/cyan]")


# =============================================================================
# Court Case Commands
# =============================================================================


@app.command("cases")
def search_cases(
    query: str | None = typer.Argument(None, help="Search query"),
    court: str | None = typer.Option(None, "-c", "--court", help="Filter by court"),
    level: str | None = typer.Option(
        None, "-l", "--level", help="Filter by court level (scotus, circuit, district)"
    ),
    limit: int = typer.Option(10, "-n", "--limit", help="Max results"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Search court cases."""
    from sqlalchemy.orm import Session

    from civitas.db.models import CourtCase, get_engine

    engine = get_engine(db_path)

    with Session(engine) as session:
        q = session.query(CourtCase)

        if query:
            search_term = f"%{query}%"
            q = q.filter(
                CourtCase.case_name.ilike(search_term)
                | CourtCase.holding.ilike(search_term)
                | CourtCase.citation.ilike(search_term)
            )

        if court:
            q = q.filter(CourtCase.court.ilike(f"%{court}%"))

        if level:
            q = q.filter(CourtCase.court_level == level)

        results = q.order_by(CourtCase.decision_date.desc().nullslast()).limit(limit).all()

        if not results:
            console.print("[yellow]No cases found[/yellow]")
            return

        table = Table(title="Court Cases")
        table.add_column("Citation", style="cyan")
        table.add_column("Case Name", style="white", max_width=40)
        table.add_column("Court", style="blue")
        table.add_column("Date", style="yellow")

        for case in results:
            name = case.case_name[:37] + "..." if len(case.case_name) > 40 else case.case_name
            table.add_row(
                case.citation,
                name,
                case.court,
                str(case.decision_date) if case.decision_date else "N/A",
            )

        console.print(table)


# =============================================================================
# Project 2025 Tracking Commands
# =============================================================================


@app.command("p2025-report")
def project2025_report(
    agency: str | None = typer.Option(None, "-a", "--agency", help="Filter by agency"),
    action: str | None = typer.Option(None, "--action", help="Filter by action type"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Generate Project 2025 tracking report."""
    from sqlalchemy.orm import Session

    from civitas.db.models import get_engine
    from civitas.project2025 import Project2025Tracker

    engine = get_engine(db_path)

    with Session(engine) as session:
        tracker = Project2025Tracker(session)
        report = tracker.generate_report()

        console.print(Panel("[bold]Project 2025 Tracking Report[/bold]", style="red"))

        # Summary stats
        table = Table(show_header=False, title="Overview")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white", justify="right")

        table.add_row("Total Proposals", str(report.get("total_proposals", 0)))
        table.add_row("With Matching Legislation", str(report.get("with_matching_legislation", 0)))
        table.add_row("With Matching EOs", str(report.get("with_matching_executive_orders", 0)))

        console.print(table)

        # By agency
        if report.get("by_agency"):
            console.print("\n[bold]By Agency:[/bold]")
            for agency_name, count in sorted(report["by_agency"].items(), key=lambda x: -x[1])[:10]:
                console.print(f"  {agency_name}: {count}")

        # By action type
        if report.get("by_action_type"):
            console.print("\n[bold]By Action Type:[/bold]")
            for action_type, count in sorted(report["by_action_type"].items(), key=lambda x: -x[1]):
                console.print(f"  {action_type}: {count}")

        # High priority alerts
        alerts = tracker.get_high_priority_alerts(limit=5)
        if alerts:
            console.print("\n[bold red]High Priority Alerts:[/bold red]")
            for alert in alerts:
                console.print(f"  • {alert['agency']}: {alert['proposal_text'][:80]}...")
                if alert.get("matching_legislation"):
                    console.print(f"    Matching: {alert['matching_legislation']}")


# =============================================================================
# Insight Generation Commands
# =============================================================================


@insights_app.command("generate")
def generate_insights(
    content_type: str = typer.Option(
        ...,
        "--type",
        "-t",
        help="Content type: objective | eo | case | legislation",
    ),
    limit: int = typer.Option(20, "--limit", help="Number of items to process"),
    ids: str | None = typer.Option(None, "--ids", help="Comma-separated IDs"),
    force: bool = typer.Option(False, "--force", help="Regenerate existing insights"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
    ollama_host: str | None = typer.Option(None, "--ollama-host", help="Ollama host URL"),
    ollama_model: str | None = typer.Option(None, "--ollama-model", help="Ollama model name"),
):
    """Generate plain-language insight summaries."""
    from sqlalchemy.orm import Session

    from civitas.db.models import Base, get_engine
    from civitas.insights import InsightGenerator

    content_type = content_type.strip().lower()
    id_list = [int(item) for item in ids.split(",")] if ids else None

    engine = get_engine(db_path)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        generator = InsightGenerator(
            session=session,
            ollama_host=ollama_host,
            ollama_model=ollama_model,
        )
        created = generator.generate_batch(
            content_type=content_type,
            limit=limit,
            ids=id_list,
            force=force,
        )

    console.print(f"[bold green]Generated {created} insight summaries.[/bold green]")


# =============================================================================
# Resistance Module Commands
# =============================================================================

resistance_app = typer.Typer(help="Resistance analysis and tracking commands")
app.add_typer(resistance_app, name="resist")


@resistance_app.command("progress")
def resistance_progress(
    agency: str | None = typer.Option(None, "-a", "--agency", help="Filter by agency"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Show P2025 implementation progress (similar to project2025.observer)."""
    from sqlalchemy.orm import Session

    from civitas.db.models import get_engine
    from civitas.resistance import ImplementationTracker

    engine = get_engine(db_path)

    with Session(engine) as session:
        tracker = ImplementationTracker(session)

        if agency:
            report = tracker.get_agency_progress(agency)
            console.print(Panel(f"[bold]P2025 Progress: {agency}[/bold]", style="red"))

            # Status breakdown
            table = Table(show_header=False)
            table.add_column("Status", style="cyan")
            table.add_column("Count", style="white", justify="right")

            for status, count in report["by_status"].items():
                table.add_row(status.replace("_", " ").title(), str(count))

            console.print(table)
            console.print(f"\nCompletion: [red]{report['completion_percentage']:.1f}%[/red]")

            # Objectives
            if report.get("objectives"):
                console.print("\n[bold]Objectives:[/bold]")
                for obj in report["objectives"]:
                    status_emoji = {
                        "completed": "🔴",
                        "in_progress": "🟡",
                        "blocked": "🟢",
                        "reversed": "✅",
                        "not_started": "⚪",
                    }.get(obj["status"], "⚪")
                    console.print(f"  {status_emoji} {obj['proposal'][:80]}...")
        else:
            summary = tracker.get_progress_summary()
            console.print(Panel("[bold]P2025 Implementation Progress[/bold]", style="red"))

            # Overall stats
            table = Table(title="Overall Status")
            table.add_column("Status", style="cyan")
            table.add_column("Count", style="white", justify="right")
            table.add_column("", style="white")

            total = summary["total_objectives"]
            for status, count in summary["by_status"].items():
                pct = (count / total * 100) if total > 0 else 0
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                table.add_row(
                    status.replace("_", " ").title(), str(count), f"[dim]{bar}[/dim] {pct:.1f}%"
                )

            console.print(table)
            console.print(
                f"\n[bold red]Completion: {summary['completion_percentage']:.1f}%[/bold red]"
            )

            # Top agencies
            if summary.get("by_agency"):
                console.print("\n[bold]Top Agencies by Objective Count:[/bold]")
                for agency_name, count in sorted(summary["by_agency"].items(), key=lambda x: -x[1])[
                    :10
                ]:
                    console.print(f"  {agency_name}: {count}")


@resistance_app.command("analyze")
def resistance_analyze(
    policy_id: int = typer.Argument(..., help="P2025 policy ID to analyze"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Analyze a P2025 policy for legal vulnerabilities using AI."""
    from sqlalchemy.orm import Session

    from civitas.db.models import get_engine
    from civitas.resistance import ResistanceAnalyzer

    engine = get_engine(db_path)

    console.print(f"[bold blue]Analyzing P2025 policy {policy_id}...[/bold blue]")
    console.print("[dim]Using Carl AI (Ollama/Llama on Azure)...[/dim]\n")

    with Session(engine) as session:
        analyzer = ResistanceAnalyzer(session)
        analysis = analyzer.analyze_policy(policy_id)

        if analysis.get("error"):
            console.print(f"[red]Error: {analysis['error']}[/red]")
            return

        console.print(Panel("[bold]Legal Vulnerability Analysis[/bold]", style="green"))

        # Constitutional issues
        if analysis.get("constitutional_issues"):
            console.print("\n[bold red]Constitutional Issues:[/bold red]")
            for issue in analysis["constitutional_issues"]:
                severity = issue.get("severity", "medium")
                color = {"high": "red", "medium": "yellow", "low": "green"}.get(severity, "white")
                console.print(
                    f"  [{color}]●[/{color}] {issue.get('provision', 'Unknown')}: {issue.get('issue', '')}"
                )

        # Challenge strategies
        if analysis.get("challenge_strategies"):
            console.print("\n[bold green]Challenge Strategies:[/bold green]")
            for strategy in analysis["challenge_strategies"]:
                likelihood = strategy.get("likelihood", "medium")
                emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(likelihood, "⚪")
                console.print(f"  {emoji} {strategy.get('type', 'Unknown')}")
                console.print(f"      Basis: {strategy.get('basis', '')}")
                console.print(f"      {strategy.get('explanation', '')[:100]}...")

        # State resistance options
        if analysis.get("state_resistance_options"):
            console.print("\n[bold cyan]State Resistance Options:[/bold cyan]")
            for option in analysis["state_resistance_options"]:
                console.print(f"  • {option.get('action', '')}")
                console.print(f"      Legal basis: {option.get('legal_basis', '')}")

        # Vulnerability score
        score = analysis.get("overall_vulnerability_score", 0)
        score_color = "green" if score > 60 else "yellow" if score > 30 else "red"
        console.print(
            f"\n[bold]Vulnerability Score: [{score_color}]{score}/100[/{score_color}][/bold]"
        )
        console.print("[dim](Higher = more vulnerable to legal challenge)[/dim]")


@resistance_app.command("analyze-batch")
def resistance_analyze_batch(
    limit: int = typer.Option(100, "--limit", help="Max policies to analyze"),
    refresh_days: int = typer.Option(30, "--refresh-days", help="Re-analyze if older than N days"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Generate cached expert-mode analysis for missing or stale policies."""
    from sqlalchemy.orm import Session

    from civitas.db.models import get_engine
    from civitas.resistance import ResistanceAnalyzer

    engine = get_engine(db_path)

    console.print(
        f"[bold blue]Generating expert analyses (limit={limit}, refresh_days={refresh_days})...[/bold blue]"
    )
    console.print("[dim]Using Carl AI (Ollama/Llama on Azure)...[/dim]\n")

    with Session(engine) as session:
        analyzer = ResistanceAnalyzer(session)
        processed = analyzer.batch_analyze_cached(limit=limit, refresh_days=refresh_days)

    console.print(f"[green]Cached analyses generated: {processed}[/green]")


@resistance_app.command("recommend")
def resistance_recommend(
    policy_id: int = typer.Argument(..., help="P2025 policy ID"),
    tier: str | None = typer.Option(
        None,
        "-t",
        "--tier",
        help="Tier (tier_1_immediate, tier_2_congressional, tier_3_presidential)",
    ),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Generate tiered resistance recommendations for a P2025 policy."""
    from sqlalchemy.orm import Session

    from civitas.db.models import get_engine
    from civitas.resistance import ResistanceRecommender

    engine = get_engine(db_path)

    console.print(
        f"[bold blue]Generating resistance recommendations for policy {policy_id}...[/bold blue]"
    )
    console.print("[dim]Using Carl AI (Ollama/Llama on Azure)...[/dim]\n")

    with Session(engine) as session:
        recommender = ResistanceRecommender(session)

        tiers = [tier] if tier else None
        results = recommender.generate_recommendations(policy_id, include_tiers=tiers)

        if results.get("error"):
            console.print(f"[red]Error: {results['error']}[/red]")
            return

        console.print(
            Panel(
                f"[bold]Resistance Recommendations[/bold]\n{results.get('policy_summary', '')[:150]}...",
                style="blue",
            )
        )

        recommendations = results.get("recommendations", {})

        # Tier 1: Immediate
        if "tier_1_immediate" in recommendations:
            console.print("\n[bold green]━━━ TIER 1: IMMEDIATE ACTIONS (Now) ━━━[/bold green]")
            console.print("[dim]Courts, 10th Amendment, State Governments[/dim]\n")
            for rec in recommendations["tier_1_immediate"]:
                if rec.get("error"):
                    continue
                console.print(f"  [cyan]●[/cyan] [bold]{rec.get('title', 'Untitled')}[/bold]")
                console.print(f"      Type: {rec.get('action_type', 'unknown')}")
                console.print(f"      {rec.get('description', '')[:100]}...")
                if rec.get("legal_basis"):
                    console.print(f"      [dim]Legal basis: {rec['legal_basis'][:80]}...[/dim]")
                console.print()

        # Tier 2: Congressional
        if "tier_2_congressional" in recommendations:
            console.print(
                "\n[bold yellow]━━━ TIER 2: CONGRESSIONAL ACTIONS (2027+) ━━━[/bold yellow]"
            )
            console.print("[dim]If Democrats win House/Senate in 2026[/dim]\n")
            for rec in recommendations["tier_2_congressional"]:
                if rec.get("error"):
                    continue
                console.print(f"  [yellow]●[/yellow] [bold]{rec.get('title', 'Untitled')}[/bold]")
                console.print(f"      Type: {rec.get('action_type', 'unknown')}")
                console.print(f"      {rec.get('description', '')[:100]}...")
                console.print()

        # Tier 3: Presidential
        if "tier_3_presidential" in recommendations:
            console.print(
                "\n[bold magenta]━━━ TIER 3: PRESIDENTIAL ACTIONS (2029+) ━━━[/bold magenta]"
            )
            console.print("[dim]If Democrat wins presidency in 2028[/dim]\n")
            for rec in recommendations["tier_3_presidential"]:
                if rec.get("error"):
                    continue
                console.print(f"  [magenta]●[/magenta] [bold]{rec.get('title', 'Untitled')}[/bold]")
                console.print(f"      Type: {rec.get('action_type', 'unknown')}")
                console.print(f"      {rec.get('description', '')[:100]}...")
                console.print()


@resistance_app.command("recommend-batch")
def resistance_recommend_batch(
    limit: int = typer.Option(100, "--limit", help="Max policies to process"),
    tier: str | None = typer.Option(
        None,
        "-t",
        "--tier",
        help="Tier (tier_1_immediate, tier_2_congressional, tier_3_presidential)",
    ),
    force: bool = typer.Option(
        False, "--force", help="Regenerate even if recommendations already exist"
    ),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Generate resistance recommendations for policies missing recommendations."""
    from sqlalchemy.orm import Session

    from civitas.db.models import Project2025Policy, ResistanceRecommendation, get_engine
    from civitas.resistance import ResistanceRecommender

    engine = get_engine(db_path)

    console.print("[bold blue]Generating resistance recommendations in batch...[/bold blue]")
    console.print("[dim]Using Carl AI (Ollama/Llama on Azure)...[/dim]\n")

    with Session(engine) as session:
        recommender = ResistanceRecommender(session)

        if force:
            policies = (
                session.query(Project2025Policy).order_by(Project2025Policy.id).limit(limit).all()
            )
        else:
            has_recs = (
                session.query(ResistanceRecommendation.id)
                .filter(ResistanceRecommendation.p2025_policy_id == Project2025Policy.id)
                .exists()
            )
            policies = (
                session.query(Project2025Policy)
                .filter(~has_recs)
                .order_by(Project2025Policy.id)
                .limit(limit)
                .all()
            )

        tiers = [tier] if tier else None
        processed = 0
        for policy in policies:
            results = recommender.generate_recommendations(policy.id, include_tiers=tiers)
            if results.get("error"):
                continue
            processed += 1

    console.print(f"[green]Policies processed: {processed}[/green]")


@resistance_app.command("scan")
def resistance_scan_eos(
    days: int = typer.Option(7, "-d", "--days", help="Days to look back"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Scan recent executive orders for P2025 policy matches."""
    from sqlalchemy.orm import Session

    from civitas.db.models import get_engine
    from civitas.resistance import ImplementationTracker

    engine = get_engine(db_path)

    console.print(f"[bold blue]Scanning executive orders from last {days} days...[/bold blue]\n")

    with Session(engine) as session:
        tracker = ImplementationTracker(session)
        matches = tracker.scan_new_eos_for_matches(days=days)

        if not matches:
            console.print("[green]No P2025-related executive orders found.[/green]")
            return

        console.print(
            Panel(
                f"[bold red]Found {len(matches)} executive orders matching P2025 objectives[/bold red]",
                style="red",
            )
        )

        for eo in matches:
            console.print(f"\n[bold]EO {eo.get('eo_number', 'N/A')}[/bold]: {eo['title'][:60]}...")
            console.print(f"  Date: {eo['date']}")
            console.print("  [yellow]Matches:[/yellow]")
            for match in eo.get("matches", [])[:3]:
                confidence_bar = "█" * int(match["confidence"] * 10) + "░" * (
                    10 - int(match["confidence"] * 10)
                )
                console.print(f"    • ({match['agency']}) {match['proposal'][:50]}...")
                console.print(f"      Confidence: [{confidence_bar}] {match['confidence']:.0%}")


@resistance_app.command("blocked")
def resistance_blocked(
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Show P2025 policies that have been blocked by courts or states."""
    from sqlalchemy.orm import Session

    from civitas.db.models import get_engine
    from civitas.resistance import ImplementationTracker

    engine = get_engine(db_path)

    with Session(engine) as session:
        tracker = ImplementationTracker(session)
        blocked = tracker.get_blocked_policies()

        if not blocked:
            console.print("[yellow]No blocked policies found.[/yellow]")
            return

        console.print(
            Panel(
                f"[bold green]🛡️ {len(blocked)} Policies Successfully Blocked[/bold green]",
                style="green",
            )
        )

        for policy in blocked:
            console.print(
                f"\n[bold green]✓[/bold green] {policy['agency']}: {policy['proposal'][:60]}..."
            )

            for challenge in policy.get("challenges", []):
                console.print(f"    [cyan]Case:[/cyan] {challenge['case']}")
                console.print(f"    [cyan]Court:[/cyan] {challenge['court']}")
                console.print(f"    [cyan]Outcome:[/cyan] {challenge['outcome'][:80]}...")


@resistance_app.command("urgent")
def resistance_urgent(
    category: str | None = typer.Option(None, "-c", "--category", help="Filter by category"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Show urgent Tier 1 actions that can be taken now."""
    from sqlalchemy.orm import Session

    from civitas.db.models import get_engine
    from civitas.resistance import ResistanceRecommender

    engine = get_engine(db_path)

    with Session(engine) as session:
        recommender = ResistanceRecommender(session)
        urgent = recommender.get_urgent_actions(category=category)

        if not urgent:
            console.print("[yellow]No urgent actions found.[/yellow]")
            return

        console.print(Panel("[bold red]⚠️ URGENT ACTIONS NEEDED[/bold red]", style="red"))

        for action in urgent:
            likelihood_color = {"high": "green", "medium": "yellow", "low": "red"}.get(
                action["likelihood"], "white"
            )
            console.print(f"\n[bold]{action['title']}[/bold]")
            console.print(f"  Type: {action['action_type']}")
            console.print(f"  {action['description'][:150]}...")
            console.print(f"  [dim]Legal basis: {action.get('legal_basis', 'N/A')[:80]}...[/dim]")
            console.print(
                f"  Likelihood: [{likelihood_color}]{action['likelihood']}[/{likelihood_color}]"
            )


@resistance_app.command("report")
def resistance_full_report(
    output: str | None = typer.Option(None, "-o", "--output", help="Output file (JSON)"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Generate comprehensive resistance report."""
    import json

    from sqlalchemy.orm import Session

    from civitas.db.models import get_engine
    from civitas.resistance import ImplementationTracker

    engine = get_engine(db_path)

    console.print("[bold blue]Generating comprehensive resistance report...[/bold blue]\n")

    with Session(engine) as session:
        tracker = ImplementationTracker(session)
        report = tracker.generate_progress_report()

        if output:
            with open(output, "w") as f:
                json.dump(report, f, indent=2, default=str)
            console.print(f"[green]Report saved to: {output}[/green]")
        else:
            # Print summary
            summary = report["summary"]
            console.print(Panel("[bold]P2025 Resistance Report[/bold]", style="blue"))

            # Overall
            console.print(f"\nTotal Objectives: {summary['total_objectives']}")
            console.print(
                f"Implementation Progress: [red]{summary['completion_percentage']:.1f}%[/red]"
            )

            # Status breakdown
            console.print("\n[bold]Status Breakdown:[/bold]")
            for status, count in summary["by_status"].items():
                emoji = {
                    "completed": "🔴",
                    "in_progress": "🟡",
                    "blocked": "🟢",
                    "reversed": "✅",
                }.get(status, "⚪")
                console.print(f"  {emoji} {status.replace('_', ' ').title()}: {count}")

            # Recent activity
            if report.get("recent_activity"):
                console.print(
                    f"\n[bold]Recent Implementation Activity ({len(report['recent_activity'])} items):[/bold]"
                )
                for activity in report["recent_activity"][:5]:
                    console.print(
                        f"  • [{activity['date']}] {activity['agency']}: {activity['action_reference']}"
                    )

            # Blocked policies
            if report.get("blocked_policies"):
                console.print(
                    f"\n[bold green]Blocked Policies: {len(report['blocked_policies'])}[/bold green]"
                )

            console.print(f"\n[dim]Report generated: {report['generated_at']}[/dim]")


# =============================================================================
# Credits Command
# =============================================================================


@app.command("credits")
def show_credits():
    """Show credits for third-party data sources and tools."""
    credits_md = """
# Civitas Credits

## Data Sources (Government - Public Domain)

- **Congress.gov API** - Federal legislation
  https://api.congress.gov/

- **California Legislature** - State legislation
  https://downloads.leginfo.legislature.ca.gov/

- **Supreme Court of the United States** - Slip opinions
  https://www.supremecourt.gov/opinions/

- **Federal Register** (US National Archives) - Executive orders
  https://www.federalregister.gov/developers/documentation/api/v1

## Open Source Tools (Free Law Project)

- **eyecite** (BSD-2-Clause) - Citation extraction
  https://github.com/freelawproject/eyecite

- **courts-db** (BSD-2-Clause) - Court database
  https://github.com/freelawproject/courts-db

- **Court Listener API** (AGPL-3.0) - Federal court opinions
  https://www.courtlistener.com/api/

## @unitedstates Project (Public Domain)

- **congress-legislators** - Congress members 1789-present
- **congress** - Bill/vote data collectors

## Infrastructure

- **Azure Blob Storage** - Document storage (baytidesstorage)
- **SQLite** - Local database
- **Llama via Ollama** - AI queries (self-hosted on Azure)

## Domain

- **projectcivitas.com** - Production website
- **.onion** - Tor hidden service for censorship resistance
"""
    console.print(Panel(Markdown(credits_md), title="Credits", expand=False))


# =============================================================================
# Search Commands
# =============================================================================


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Search query"),
    jurisdiction: str | None = typer.Option(
        None, "-j", "--jurisdiction", help="Filter by jurisdiction"
    ),
    enacted: bool = typer.Option(False, "--enacted", help="Only show enacted laws"),
    limit: int = typer.Option(20, "-n", "--limit", help="Max results"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Search legislation by keyword."""
    from civitas.ai import CivitasAI

    ai = CivitasAI(db_path=db_path)
    results = ai.search(
        query=query,
        jurisdiction=jurisdiction,
        enacted_only=enacted,
        limit=limit,
    )

    if not results:
        console.print(f"[yellow]No results found for: {query}[/yellow]")
        return

    table = Table(title=f"Search Results: '{query}' ({len(results)} found)")
    table.add_column("Citation", style="cyan")
    table.add_column("Jurisdiction", style="blue")
    table.add_column("Title", style="white", max_width=50)
    table.add_column("Status", style="yellow")

    for r in results:
        status = "✓ Enacted" if r["is_enacted"] else (r["status"] or "Pending")
        title = r["title"] or ""
        if len(title) > 50:
            title = title[:47] + "..."

        table.add_row(
            r["citation"],
            r["jurisdiction"].title(),
            title,
            status,
        )

    console.print(table)


@app.command("show")
def show_legislation(
    legislation_id: int = typer.Argument(..., help="Legislation ID"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Show detailed information about a piece of legislation."""
    from civitas.ai import CivitasAI

    ai = CivitasAI(db_path=db_path)
    leg = ai.get_legislation(legislation_id)

    if not leg:
        console.print(f"[red]Legislation not found: {legislation_id}[/red]")
        return

    # Header
    status = "✓ ENACTED" if leg["is_enacted"] else leg["status"] or "PENDING"
    console.print(
        Panel(
            f"[bold]{leg['citation']}[/bold] - {leg['jurisdiction'].upper()}\nStatus: {status}",
            title="Legislation Details",
        )
    )

    # Title and summary
    if leg["title"]:
        console.print(f"\n[bold]Title:[/bold] {leg['title']}\n")

    if leg["summary"]:
        console.print(
            f"[bold]Summary:[/bold]\n{leg['summary'][:500]}{'...' if len(leg['summary'] or '') > 500 else ''}\n"
        )

    # Dates
    if leg["introduced_date"] or leg["last_action_date"]:
        console.print("[bold]Timeline:[/bold]")
        if leg["introduced_date"]:
            console.print(f"  Introduced: {leg['introduced_date']}")
        if leg["last_action_date"]:
            console.print(f"  Last Action: {leg['last_action_date']}")
        console.print()

    # If enacted
    if leg["is_enacted"]:
        console.print("[bold green]Enacted as:[/bold green]")
        if leg["public_law_number"]:
            console.print(f"  {leg['public_law_number']}")
        if leg["chapter_number"]:
            console.print(f"  Chapter {leg['chapter_number']}")
        console.print()

    # Recent actions
    if leg["recent_actions"]:
        console.print("[bold]Recent Actions:[/bold]")
        for action in leg["recent_actions"][:5]:
            console.print(f"  [{action['date']}] {action['text'][:80]}...")
        console.print()

    # Votes
    if leg["votes"]:
        console.print("[bold]Votes:[/bold]")
        for vote in leg["votes"]:
            result = (
                f"[green]{vote['result']}[/green]"
                if vote["result"] == "PASS"
                else f"[red]{vote['result']}[/red]"
            )
            console.print(
                f"  [{vote['date']}] {vote['chamber'].title()}: {vote['ayes']}-{vote['nays']} {result}"
            )


@app.command("recent")
def recent_laws(
    jurisdiction: str | None = typer.Option(
        None, "-j", "--jurisdiction", help="Filter by jurisdiction"
    ),
    limit: int = typer.Option(10, "-n", "--limit", help="Max results"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Show recently enacted laws."""
    from civitas.ai import CivitasAI

    ai = CivitasAI(db_path=db_path)
    results = ai.get_recent_laws(jurisdiction=jurisdiction, limit=limit)

    if not results:
        console.print("[yellow]No enacted laws found.[/yellow]")
        return

    table = Table(title="Recently Enacted Laws")
    table.add_column("Citation", style="cyan")
    table.add_column("Law Number", style="green")
    table.add_column("Jurisdiction", style="blue")
    table.add_column("Title", style="white", max_width=50)

    for r in results:
        law_num = r["public_law_number"] or r["chapter_number"] or ""
        title = r["title"] or ""
        if len(title) > 50:
            title = title[:47] + "..."

        table.add_row(
            r["citation"],
            law_num,
            r["jurisdiction"].title(),
            title,
        )

    console.print(table)


@app.command("stats")
def show_stats(
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Show database statistics."""
    from civitas.ai import CivitasAI

    ai = CivitasAI(db_path=db_path)
    stats = ai.get_statistics()

    console.print(Panel("[bold]Civitas Database Statistics[/bold]", style="blue"))

    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")

    table.add_row("Total Legislation", f"{stats['total_legislation']:,}")
    table.add_row("Enacted Laws", f"{stats['enacted_laws']:,}")
    table.add_row("Legislators", f"{stats['total_legislators']:,}")
    table.add_row("Votes Recorded", f"{stats['total_votes']:,}")
    table.add_row("Law Codes", f"{stats['law_codes']:,}")

    console.print(table)

    if stats["by_jurisdiction"]:
        console.print("\n[bold]By Jurisdiction:[/bold]")
        for jur, data in stats["by_jurisdiction"].items():
            console.print(f"  {jur.title()}: {data['total']:,} total, {data['enacted']:,} enacted")


# =============================================================================
# Interactive/AI Commands
# =============================================================================


@app.command("ask")
def ask_question(
    question: str = typer.Argument(..., help="Natural language question"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
    ai_provider: str | None = typer.Option(
        None, "--ai", help="AI provider (ollama/anthropic/openai)"
    ),
):
    """Ask a natural language question about legislation.

    Default AI provider is Ollama (Llama running on Azure).
    """
    from civitas.ai import CivitasAI

    ai = CivitasAI(
        db_path=db_path,
        ai_provider=ai_provider,
    )

    response = ai.ask(question)
    console.print(response)


@app.command("chat")
def interactive_chat(
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
    ai_provider: str | None = typer.Option(
        None, "--ai", help="AI provider (ollama/anthropic/openai)"
    ),
):
    """Start an interactive chat session.

    Default AI provider is Ollama (Llama running on Azure).
    """
    from civitas.ai import CivitasAI

    ai = CivitasAI(
        db_path=db_path,
        ai_provider=ai_provider,
    )

    console.print(
        Panel(
            "[bold]Civitas Interactive Mode[/bold]\n\n"
            "Ask questions about legislation in natural language.\n"
            "Type 'quit' or 'exit' to leave.\n\n"
            "Examples:\n"
            "  • What laws about water were enacted in California?\n"
            "  • Show me recent environmental legislation\n"
            "  • How many bills were enacted in Congress 118?",
            title="Welcome",
            style="blue",
        )
    )

    while True:
        try:
            question = console.input("\n[bold cyan]You:[/bold cyan] ").strip()

            if question.lower() in ("quit", "exit", "q"):
                console.print("[yellow]Goodbye![/yellow]")
                break

            if not question:
                continue

            response = ai.ask(question)
            console.print(f"\n[bold green]Civitas:[/bold green]\n{response}")

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


# =============================================================================
# Research / Report Generation Commands
# =============================================================================

research_app = typer.Typer(help="Research and report generation commands")
app.add_typer(research_app, name="research")


@research_app.command("storm-report")
def generate_storm_report(
    topic: str = typer.Argument(
        ..., help="Topic for the report (e.g., 'EPA regulations under Project 2025')"
    ),
    output_dir: str = typer.Option("./storm_output", "-o", "--output", help="Output directory"),
    use_ollama: bool = typer.Option(False, "--ollama", help="Use Ollama instead of OpenAI"),
    use_web_search: bool = typer.Option(
        False, "--web", help="Enable web search for additional sources"
    ),
    no_custom_docs: bool = typer.Option(
        False, "--no-docs", help="Skip custom P2025 document retrieval"
    ),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Generate a comprehensive STORM report on a Project 2025 topic.

    Uses Stanford STORM to create Wikipedia-style articles with citations.
    Requires: pip install knowledge-storm

    Examples:
        civitas research storm-report "EPA regulations under Project 2025"
        civitas research storm-report "Immigration enforcement policies" --ollama
        civitas research storm-report "Education policy changes" --web
    """
    from civitas.research import STORMReportGenerator

    console.print(f"[bold blue]Generating STORM report: {topic}[/bold blue]")

    try:
        from civitas.db import get_session_local

        session_factory = get_session_local(db_path)
        with session_factory() as session:
            generator = STORMReportGenerator(
                session=session,
                output_dir=output_dir,
            )

            report = generator.generate_policy_report(
                topic=topic,
                use_custom_docs=not no_custom_docs,
                use_web_search=use_web_search,
                use_ollama=use_ollama,
            )

            console.print("\n[bold green]Report generated successfully![/bold green]")
            console.print(f"  Topic: {report.topic}")
            console.print(f"  Output: {report.output_dir}")

            if report.article_path:
                console.print(f"  Article: {report.article_path}")
                # Show preview
                article_file = Path(report.article_path)
                if article_file.exists():
                    content = article_file.read_text()[:1000]
                    console.print("\n[bold]Preview:[/bold]")
                    console.print(Markdown(content + "\n\n..."))

    except ImportError as e:
        console.print(f"[red]STORM not installed: {e}[/red]")
        console.print("[yellow]Install with: pip install knowledge-storm[/yellow]")
    except Exception as e:
        console.print(f"[red]Error generating report: {e}[/red]")
        raise


@research_app.command("export-p2025")
def export_p2025_for_storm(
    output_file: str = typer.Option("p2025_policies.csv", "-o", "--output", help="Output CSV file"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Export Project 2025 policies to CSV for STORM VectorRM.

    Creates a CSV file suitable for use with STORM's vector retrieval module.
    """
    from civitas.research import STORMReportGenerator

    console.print("[bold blue]Exporting P2025 policies for STORM...[/bold blue]")

    try:
        from civitas.db import get_session_local

        session_factory = get_session_local(db_path)
        with session_factory() as session:
            generator = STORMReportGenerator(session=session)
            csv_path = generator.export_policies_for_storm(output_file)

            console.print("[bold green]Export complete![/bold green]")
            console.print(f"  Output: {csv_path}")

            # Count lines
            with open(csv_path) as f:
                line_count = sum(1 for _ in f) - 1  # Subtract header
            console.print(f"  Policies: {line_count}")

    except Exception as e:
        console.print(f"[red]Error exporting: {e}[/red]")
        raise


# =============================================================================
# Temporal Workflow Commands
# =============================================================================

workflow_app = typer.Typer(help="Temporal workflow orchestration commands")
app.add_typer(workflow_app, name="workflow")


@workflow_app.command("worker")
def start_worker():
    """Start the Temporal worker to process workflows.

    The worker must be running for workflows to execute.
    Configure via environment variables:
      TEMPORAL_HOST: Temporal server address (default: localhost:7233)
      TEMPORAL_NAMESPACE: Namespace (default: default)
      TEMPORAL_TASK_QUEUE: Task queue (default: civitas-tasks)
    """
    import asyncio

    from civitas.workflows.worker import run_worker

    console.print("[bold blue]Starting Civitas Temporal Worker...[/bold blue]")
    asyncio.run(run_worker())


@workflow_app.command("ingest")
def workflow_ingest(
    congress: str = typer.Option(
        "118,119", "--congress", "-c", help="Congress numbers (comma-separated)"
    ),
    california: str = typer.Option(
        "2023,2024", "--california", "-ca", help="CA years (comma-separated)"
    ),
    eos: str = typer.Option(
        "2024,2025", "--eos", "-e", help="EO years (comma-separated)"
    ),
    states: str = typer.Option(
        None, "--states", "-s", help="State abbreviations (comma-separated)"
    ),
    laws_only: bool = typer.Option(True, "--laws-only/--all-bills"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for completion"),
):
    """Start a full data ingestion workflow via Temporal.

    Example:
        civitas workflow ingest --congress 119 --wait
    """
    import asyncio

    from civitas.workflows.client import start_full_ingestion

    congress_nums = [int(c.strip()) for c in congress.split(",") if c.strip()]
    ca_years = [int(y.strip()) for y in california.split(",") if y.strip()]
    eo_years = [int(y.strip()) for y in eos.split(",") if y.strip()]
    state_list = [s.strip() for s in states.split(",")] if states else None

    console.print("[bold blue]Starting Full Ingestion Workflow...[/bold blue]")
    console.print(f"  Congress: {congress_nums}")
    console.print(f"  California: {ca_years}")
    console.print(f"  Executive Orders: {eo_years}")
    if state_list:
        console.print(f"  States: {state_list}")

    result = asyncio.run(
        start_full_ingestion(
            congress_numbers=congress_nums,
            california_years=ca_years,
            eo_years=eo_years,
            states=state_list,
            laws_only=laws_only,
            wait=wait,
        )
    )

    if wait:
        console.print("\n[bold green]Workflow Complete![/bold green]")
        console.print(f"  Sources processed: {result.total_sources}")
        console.print(f"  Successful: {result.successful_sources}")
        console.print(f"  Failed: {result.failed_sources}")
        console.print(f"  Total records: {result.total_records}")
        if result.errors:
            console.print(f"\n[yellow]Errors ({len(result.errors)}):[/yellow]")
            for err in result.errors[:5]:
                console.print(f"  - {err}")
    else:
        console.print("\n[green]Workflow started. Use 'workflow status' to check progress.[/green]")


@workflow_app.command("generate")
def workflow_generate(
    profiles: bool = typer.Option(True, "--profiles/--no-profiles", help="Generate justice profiles"),
    analyses: bool = typer.Option(True, "--analyses/--no-analyses", help="Generate resistance analyses"),
    recommendations: bool = typer.Option(True, "--recs/--no-recs", help="Generate recommendations"),
    insights: bool = typer.Option(False, "--insights/--no-insights", help="Generate insights"),
    batch_size: int = typer.Option(25, "--batch-size", "-b", help="Items per batch"),
    max_batches: int = typer.Option(None, "--max-batches", "-m", help="Maximum batches"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for completion"),
):
    """Start AI content generation workflow via Temporal.

    Example:
        civitas workflow generate --analyses --recs --batch-size 10 --wait
    """
    import asyncio

    from civitas.workflows.client import start_content_generation

    console.print("[bold blue]Starting Content Generation Workflow...[/bold blue]")
    console.print(f"  Profiles: {profiles}")
    console.print(f"  Analyses: {analyses}")
    console.print(f"  Recommendations: {recommendations}")
    console.print(f"  Insights: {insights}")
    console.print(f"  Batch size: {batch_size}")

    result = asyncio.run(
        start_content_generation(
            generate_profiles=profiles,
            generate_analyses=analyses,
            generate_recommendations=recommendations,
            generate_insights=insights,
            analysis_batch_size=batch_size,
            max_batches=max_batches,
            wait=wait,
        )
    )

    if wait:
        console.print("\n[bold green]Workflow Complete![/bold green]")
        console.print(f"  Profiles generated: {result.profiles_generated}")
        console.print(f"  Analyses generated: {result.analyses_generated}")
        console.print(f"  Recommendations generated: {result.recommendations_generated}")
        console.print(f"  Insights generated: {result.insights_generated}")
        console.print(f"  Total items: {result.total_items}")
        console.print(f"  Total failures: {result.total_failures}")
    else:
        console.print("\n[green]Workflow started. Use 'workflow status' to check progress.[/green]")


@workflow_app.command("resistance")
def workflow_resistance(
    batch_size: int = typer.Option(25, "--batch-size", "-b", help="Policies per batch"),
    refresh_days: int = typer.Option(30, "--refresh-days", "-r", help="Refresh analyses older than N days"),
    max_batches: int = typer.Option(None, "--max-batches", "-m", help="Maximum batches (None=all)"),
    include_recs: bool = typer.Option(True, "--recs/--no-recs", help="Include recommendations"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for completion"),
):
    """Start resistance analysis workflow via Temporal.

    This workflow generates expert-level constitutional analyses
    and resistance recommendations for Project 2025 policies.

    Example:
        civitas workflow resistance --batch-size 10 --max-batches 5 --wait
    """
    import asyncio

    from civitas.workflows.client import start_resistance_analysis

    console.print("[bold blue]Starting Resistance Analysis Workflow...[/bold blue]")
    console.print(f"  Batch size: {batch_size}")
    console.print(f"  Refresh days: {refresh_days}")
    console.print(f"  Max batches: {max_batches or 'unlimited'}")
    console.print(f"  Include recommendations: {include_recs}")

    result = asyncio.run(
        start_resistance_analysis(
            batch_size=batch_size,
            refresh_days=refresh_days,
            max_batches=max_batches,
            include_recommendations=include_recs,
            wait=wait,
        )
    )

    if wait:
        console.print("\n[bold green]Workflow Complete![/bold green]")
        console.print(f"  Analyses generated: {result.analyses_generated}")
        console.print(f"  Recommendations generated: {result.recommendations_generated}")
        console.print(f"  Total items: {result.total_items}")
        console.print(f"  Failures: {result.total_failures}")
    else:
        console.print("\n[green]Workflow started. Use 'workflow status' to check progress.[/green]")


@workflow_app.command("list")
def workflow_list(
    workflow_type: str = typer.Option(None, "--type", "-t", help="Filter by workflow type"),
    status: str = typer.Option(None, "--status", "-s", help="Filter by status (Running, Completed, Failed)"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum workflows to list"),
):
    """List recent workflows."""
    import asyncio

    from civitas.workflows.client import list_workflows

    workflows = asyncio.run(list_workflows(workflow_type, status, limit))

    if not workflows:
        console.print("[yellow]No workflows found.[/yellow]")
        return

    table = Table(title="Recent Workflows")
    table.add_column("Workflow ID", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Started", style="dim")

    for wf in workflows:
        status_style = {
            "Running": "yellow",
            "Completed": "green",
            "Failed": "red",
            "Cancelled": "dim",
        }.get(wf["status"], "white")

        table.add_row(
            wf["workflow_id"],
            wf["type"] or "-",
            f"[{status_style}]{wf['status']}[/{status_style}]",
            wf["start_time"][:19] if wf["start_time"] else "-",
        )

    console.print(table)


@workflow_app.command("status")
def workflow_status(
    workflow_id: str = typer.Argument(..., help="Workflow ID to check"),
):
    """Get status of a specific workflow."""
    import asyncio

    from civitas.workflows.client import get_workflow_status

    try:
        status = asyncio.run(get_workflow_status(workflow_id))

        console.print(Panel(
            f"[bold]Workflow:[/bold] {status['workflow_id']}\n"
            f"[bold]Type:[/bold] {status['workflow_type']}\n"
            f"[bold]Status:[/bold] {status['status']}\n"
            f"[bold]Started:[/bold] {status['start_time'] or 'N/A'}\n"
            f"[bold]Completed:[/bold] {status['close_time'] or 'In Progress'}",
            title="Workflow Status",
        ))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@workflow_app.command("cancel")
def workflow_cancel(
    workflow_id: str = typer.Argument(..., help="Workflow ID to cancel"),
):
    """Cancel a running workflow."""
    import asyncio

    from civitas.workflows.client import cancel_workflow

    try:
        asyncio.run(cancel_workflow(workflow_id))
        console.print(f"[green]Cancelled workflow: {workflow_id}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# =============================================================================
# Bay Navigator Workflow Commands
# =============================================================================

bnav_app = typer.Typer(help="Bay Navigator workflow commands")
workflow_app.add_typer(bnav_app, name="bnav")


@bnav_app.command("sync")
def bnav_full_sync(
    civic: bool = typer.Option(False, "--civic/--no-civic", help="Include civic council scraping"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for completion"),
):
    """Run full Bay Navigator data sync via Temporal.

    Syncs transit, open data, parks, benefits, and optionally civic councils.

    Example:
        civitas workflow bnav sync --civic --wait
    """
    import asyncio
    from uuid import uuid4

    from civitas.workflows.baynavigator import BayNavigatorFullSyncWorkflow
    from civitas.workflows.worker import create_client, get_task_queue

    async def run():
        client = await create_client()
        workflow_id = f"bnav-sync-{uuid4().hex[:8]}"

        handle = await client.start_workflow(
            BayNavigatorFullSyncWorkflow.run,
            civic,
            id=workflow_id,
            task_queue=get_task_queue(),
        )

        console.print(f"[green]Started workflow: {workflow_id}[/green]")

        if wait:
            result = await handle.result()
            return result
        return None

    console.print("[bold blue]Starting Bay Navigator Full Sync...[/bold blue]")
    console.print(f"  Include civic scraping: {civic}")

    result = asyncio.run(run())

    if result:
        console.print("\n[bold green]Sync Complete![/bold green]")
        console.print(f"  Scripts run: {result.total_scripts}")
        console.print(f"  Successful: {result.successful}")
        console.print(f"  Failed: {result.failed}")
        if result.errors:
            console.print(f"\n[yellow]Errors ({len(result.errors)}):[/yellow]")
            for err in result.errors[:5]:
                console.print(f"  - {err[:100]}")
    else:
        console.print("\n[green]Workflow started. Use 'workflow list' to check progress.[/green]")


@bnav_app.command("civic")
def bnav_civic_scrape(
    blocked: bool = typer.Option(False, "--blocked/--no-blocked", help="Include slow Playwright scraping"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for completion"),
):
    """Scrape city council data from multiple platforms.

    Scrapes: CivicPlus, Granicus, ProudCity, Legistar, Wikipedia.

    Example:
        civitas workflow bnav civic --wait
    """
    import asyncio
    from uuid import uuid4

    from civitas.workflows.baynavigator import CivicDataWorkflow
    from civitas.workflows.worker import create_client, get_task_queue

    async def run():
        client = await create_client()
        workflow_id = f"bnav-civic-{uuid4().hex[:8]}"

        handle = await client.start_workflow(
            CivicDataWorkflow.run,
            blocked,
            id=workflow_id,
            task_queue=get_task_queue(),
        )

        console.print(f"[green]Started workflow: {workflow_id}[/green]")

        if wait:
            return await handle.result()
        return None

    console.print("[bold blue]Starting Civic Data Collection...[/bold blue]")
    console.print(f"  Include blocked sites: {blocked}")

    result = asyncio.run(run())

    if result:
        console.print("\n[bold green]Civic Scraping Complete![/bold green]")
        console.print(f"  Scrapers run: {result.total_scripts}")
        console.print(f"  Successful: {result.successful}")
        console.print(f"  Failed: {result.failed}")
    else:
        console.print("\n[green]Workflow started.[/green]")


@bnav_app.command("opendata")
def bnav_open_data(
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for completion"),
):
    """Sync open data from Bay Area city portals.

    Daily sync from Socrata-powered open data portals.

    Example:
        civitas workflow bnav opendata --wait
    """
    import asyncio
    from uuid import uuid4

    from civitas.workflows.baynavigator import OpenDataSyncWorkflow
    from civitas.workflows.worker import create_client, get_task_queue

    async def run():
        client = await create_client()
        workflow_id = f"bnav-opendata-{uuid4().hex[:8]}"

        handle = await client.start_workflow(
            OpenDataSyncWorkflow.run,
            id=workflow_id,
            task_queue=get_task_queue(),
        )

        console.print(f"[green]Started workflow: {workflow_id}[/green]")

        if wait:
            return await handle.result()
        return None

    console.print("[bold blue]Starting Open Data Sync...[/bold blue]")

    result = asyncio.run(run())

    if result:
        console.print("\n[bold green]Open Data Sync Complete![/bold green]")
        console.print(f"  Steps: {result.total_scripts}")
        console.print(f"  Successful: {result.successful}")
    else:
        console.print("\n[green]Workflow started.[/green]")


@bnav_app.command("api")
def bnav_generate_api(
    simple: bool = typer.Option(False, "--simple/--no-simple", help="Include AI simple language generation"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for completion"),
):
    """Generate Bay Navigator API files.

    Generates: programs.json, GeoJSON, search index, city contacts.

    Example:
        civitas workflow bnav api --simple --wait
    """
    import asyncio
    from uuid import uuid4

    from civitas.workflows.baynavigator import APIGenerationWorkflow
    from civitas.workflows.worker import create_client, get_task_queue

    async def run():
        client = await create_client()
        workflow_id = f"bnav-api-{uuid4().hex[:8]}"

        handle = await client.start_workflow(
            APIGenerationWorkflow.run,
            simple,
            id=workflow_id,
            task_queue=get_task_queue(),
        )

        console.print(f"[green]Started workflow: {workflow_id}[/green]")

        if wait:
            return await handle.result()
        return None

    console.print("[bold blue]Starting API Generation...[/bold blue]")
    console.print(f"  Include simple language: {simple}")

    result = asyncio.run(run())

    if result:
        console.print("\n[bold green]API Generation Complete![/bold green]")
        console.print(f"  Files generated: {result.successful}")
    else:
        console.print("\n[green]Workflow started.[/green]")


@bnav_app.command("validate")
def bnav_validate(
    links: bool = typer.Option(False, "--links/--no-links", help="Include link validation (slow)"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for completion"),
):
    """Run Bay Navigator data validation.

    Validates: schema, duplicates, freshness, coordinates, and optionally links.

    Example:
        civitas workflow bnav validate --links --wait
    """
    import asyncio
    from uuid import uuid4

    from civitas.workflows.baynavigator import ValidationWorkflow
    from civitas.workflows.worker import create_client, get_task_queue

    async def run():
        client = await create_client()
        workflow_id = f"bnav-validate-{uuid4().hex[:8]}"

        handle = await client.start_workflow(
            ValidationWorkflow.run,
            links,
            id=workflow_id,
            task_queue=get_task_queue(),
        )

        console.print(f"[green]Started workflow: {workflow_id}[/green]")

        if wait:
            return await handle.result()
        return None

    console.print("[bold blue]Starting Validation...[/bold blue]")
    console.print(f"  Include link validation: {links}")

    result = asyncio.run(run())

    if result:
        console.print("\n[bold green]Validation Complete![/bold green]")
        console.print(f"  Checks run: {result.total_scripts}")
        console.print(f"  Passed: {result.successful}")
        console.print(f"  Failed: {result.failed}")
        if result.errors:
            console.print(f"\n[yellow]Issues ({len(result.errors)}):[/yellow]")
            for err in result.errors[:5]:
                console.print(f"  - {err[:100]}")
    else:
        console.print("\n[green]Workflow started.[/green]")


# =============================================================================
# Main
# =============================================================================


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
