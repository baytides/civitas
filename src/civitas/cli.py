"""Command-line interface for Civitas."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

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
    data_dir: Optional[str] = typer.Option(None, "--data-dir", help="Data directory"),
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


# =============================================================================
# Search Commands
# =============================================================================

@app.command("search")
def search(
    query: str = typer.Argument(..., help="Search query"),
    jurisdiction: Optional[str] = typer.Option(None, "-j", "--jurisdiction", help="Filter by jurisdiction"),
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
    console.print(Panel(
        f"[bold]{leg['citation']}[/bold] - {leg['jurisdiction'].upper()}\n"
        f"Status: {status}",
        title="Legislation Details",
    ))

    # Title and summary
    if leg["title"]:
        console.print(f"\n[bold]Title:[/bold] {leg['title']}\n")

    if leg["summary"]:
        console.print(f"[bold]Summary:[/bold]\n{leg['summary'][:500]}{'...' if len(leg['summary'] or '') > 500 else ''}\n")

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
            result = f"[green]{vote['result']}[/green]" if vote["result"] == "PASS" else f"[red]{vote['result']}[/red]"
            console.print(f"  [{vote['date']}] {vote['chamber'].title()}: {vote['ayes']}-{vote['nays']} {result}")


@app.command("recent")
def recent_laws(
    jurisdiction: Optional[str] = typer.Option(None, "-j", "--jurisdiction", help="Filter by jurisdiction"),
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
    ai_provider: Optional[str] = typer.Option(None, "--ai", help="AI provider (anthropic/openai)"),
):
    """Ask a natural language question about legislation."""
    from civitas.ai import CivitasAI

    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")

    ai = CivitasAI(
        db_path=db_path,
        ai_provider=ai_provider,
        api_key=api_key,
    )

    response = ai.ask(question)
    console.print(response)


@app.command("chat")
def interactive_chat(
    db_path: str = typer.Option("civitas.db", "--db", help="Database path"),
    ai_provider: Optional[str] = typer.Option(None, "--ai", help="AI provider (anthropic/openai)"),
):
    """Start an interactive chat session."""
    from civitas.ai import CivitasAI

    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")

    ai = CivitasAI(
        db_path=db_path,
        ai_provider=ai_provider,
        api_key=api_key,
    )

    console.print(Panel(
        "[bold]Civitas Interactive Mode[/bold]\n\n"
        "Ask questions about legislation in natural language.\n"
        "Type 'quit' or 'exit' to leave.\n\n"
        "Examples:\n"
        "  • What laws about water were enacted in California?\n"
        "  • Show me recent environmental legislation\n"
        "  • How many bills were enacted in Congress 118?",
        title="Welcome",
        style="blue",
    ))

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
