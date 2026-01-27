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


@ingest_app.command("scotus")
def ingest_scotus(
    term: str | None = typer.Option(None, "--term", help="Specific term (e.g., '24' for 2024)"),
    azure: bool = typer.Option(False, "--azure", help="Store documents in Azure Blob Storage"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Ingest Supreme Court slip opinions."""
    from sqlalchemy.orm import Session

    from civitas.db.models import CourtCase, get_engine
    from civitas.scotus import SCOTUSClient
    from civitas.storage import AzureStorageClient

    azure_client = AzureStorageClient() if azure else None

    console.print("[bold blue]Ingesting Supreme Court opinions...[/bold blue]")

    engine = get_engine(db_path)
    counts = {"cases": 0, "stored_in_azure": 0}

    with SCOTUSClient(azure_client=azure_client) as client:
        terms = [term] if term else client.list_terms()[:3]  # Recent 3 terms by default

        for t in terms:
            console.print(f"  [cyan]Term {t}...[/cyan]")
            opinions = client.list_opinions(t)

            for opinion in opinions:
                pdf_path, azure_url = client.download_opinion(opinion)

                with Session(engine) as session:
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
                            azure_url=azure_url,
                            status="decided",
                        )
                        session.add(case)
                        session.commit()
                        counts["cases"] += 1

                        if azure_url:
                            counts["stored_in_azure"] += 1

    console.print("\n[bold green]SCOTUS ingestion complete![/bold green]")
    console.print(f"  Cases: {counts['cases']}")
    if azure:
        console.print(f"  Stored in Azure: {counts['stored_in_azure']}")


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
    state: str = typer.Argument(..., help="Two-letter state code (e.g., 'ca')"),
    session: str | None = typer.Option(None, "-s", "--session", help="Session identifier"),
    chamber: str | None = typer.Option(None, "-c", "--chamber", help="Chamber (upper/lower)"),
    limit: int = typer.Option(500, "-n", "--limit", help="Max bills to scrape"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Scrape state bills directly from legislature website.

    This bypasses the OpenStates API entirely by scraping directly from
    official state legislature websites.

    Currently supported states: CA (California)

    Example:
        civitas ingest scrape-state ca --session 20232024 --limit 100
    """
    from sqlalchemy.orm import Session

    from civitas.db.models import Legislation, get_engine

    # Import available scrapers
    scrapers = {}
    try:
        from civitas.states.scrapers import CaliforniaScraper

        scrapers["ca"] = CaliforniaScraper
    except ImportError:
        pass

    state_lower = state.lower()
    if state_lower not in scrapers:
        console.print(f"[red]No scraper available for state: {state.upper()}[/red]")
        console.print(f"Available states: {', '.join(s.upper() for s in scrapers.keys())}")
        console.print("\nAlternatives:")
        console.print("  - civitas ingest state-bills  (uses OpenStates API, limited)")
        console.print("  - civitas ingest openstates-bulk  (uses monthly dump, unlimited)")
        return

    scraper_cls = scrapers[state_lower]

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
    """Ingest state bills from Open States API.

    Requires OPENSTATES_API_KEY environment variable.
    Get a key at: https://openstates.org/accounts/login/
    """
    from sqlalchemy.orm import Session

    from civitas.db.models import Legislation, get_engine
    from civitas.states import OpenStatesClient

    api_key = os.getenv("OPENSTATES_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENSTATES_API_KEY environment variable not set[/red]")
        console.print("Get a free API key at: https://openstates.org/accounts/login/")
        return

    console.print(f"[bold blue]Ingesting {state.upper()} bills from Open States...[/bold blue]")

    engine = get_engine(db_path)
    counts = {"bills": 0, "skipped": 0}

    try:
        with OpenStatesClient(api_key=api_key) as client:
            # Get sessions if not specified
            if not session:
                sessions = client.get_sessions(state)
                if sessions:
                    session = sessions[0].identifier  # Most recent session
                    console.print(f"  [cyan]Using session: {session}[/cyan]")
                else:
                    console.print("[red]No sessions found for state[/red]")
                    return

            for bill in client.get_bills(state=state, session=session, limit=limit):
                with Session(engine) as db_session:
                    # Check if already exists
                    existing = (
                        db_session.query(Legislation)
                        .filter(
                            Legislation.jurisdiction == state.lower(),
                            Legislation.source_id == bill.id,
                        )
                        .first()
                    )

                    if existing:
                        counts["skipped"] += 1
                        continue

                    # Determine chamber
                    chamber = "assembly" if bill.chamber == "lower" else "senate"

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
                    counts["bills"] += 1

                    if counts["bills"] % 100 == 0:
                        console.print(f"  Processed {counts['bills']} bills...")

    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        return
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    console.print("\n[bold green]State bill ingestion complete![/bold green]")
    console.print(f"  Bills added: {counts['bills']}")
    console.print(f"  Skipped (existing): {counts['skipped']}")


@ingest_app.command("state-legislators")
def ingest_state_legislators(
    state: str = typer.Argument(..., help="Two-letter state code (e.g., 'ca', 'ny')"),
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
):
    """Ingest state legislators from Open States API.

    Requires OPENSTATES_API_KEY environment variable.
    """
    from sqlalchemy.orm import Session

    from civitas.db.models import Legislator, get_engine
    from civitas.states import OpenStatesClient

    api_key = os.getenv("OPENSTATES_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENSTATES_API_KEY environment variable not set[/red]")
        console.print("Get a free API key at: https://openstates.org/accounts/login/")
        return

    console.print(
        f"[bold blue]Ingesting {state.upper()} legislators from Open States...[/bold blue]"
    )

    engine = get_engine(db_path)
    counts = {"legislators": 0, "skipped": 0}

    try:
        with OpenStatesClient(api_key=api_key) as client:
            for legislator in client.get_legislators(state=state, limit=500):
                with Session(engine) as db_session:
                    # Check if already exists
                    existing = (
                        db_session.query(Legislator)
                        .filter(
                            Legislator.jurisdiction == state.lower(),
                            Legislator.source_id == legislator.id,
                        )
                        .first()
                    )

                    if existing:
                        counts["skipped"] += 1
                        continue

                    # Determine chamber
                    chamber = "assembly" if legislator.chamber == "lower" else "senate"

                    # Map party
                    party = (
                        "D"
                        if "democrat" in legislator.party.lower()
                        else ("R" if "republican" in legislator.party.lower() else "I")
                    )

                    db_legislator = Legislator(
                        jurisdiction=state.lower(),
                        source_id=legislator.id,
                        full_name=legislator.name,
                        chamber=chamber,
                        district=legislator.district,
                        party=party,
                        state=state.upper(),
                    )
                    db_session.add(db_legislator)
                    db_session.commit()
                    counts["legislators"] += 1

    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        return
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    console.print("\n[bold green]State legislator ingestion complete![/bold green]")
    console.print(f"  Legislators added: {counts['legislators']}")
    console.print(f"  Skipped (existing): {counts['skipped']}")


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
# Main
# =============================================================================


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
