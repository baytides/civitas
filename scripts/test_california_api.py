#!/usr/bin/env python3
"""Test script to verify California Legislature data client functionality."""

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table

from civitas.california import CaliforniaLegislatureClient

console = Console()


def test_download_and_parse(session_year: int = 2023):
    """Test downloading and parsing a legislative session."""
    msg = f"Testing: California Legislature {session_year} Session"
    console.print(f"\n[bold blue]{msg}[/bold blue]")

    client = CaliforniaLegislatureClient(data_dir=Path("data/california"))

    # Check if data exists, download if not
    data_path = client.data_dir / str(session_year)
    if not data_path.exists():
        console.print(
            f"[yellow]Downloading {session_year} session data"
            " (this may take a while)...[/yellow]"
        )
        data_path = client.download_session(session_year)
    else:
        console.print(f"[green]Using cached data from {data_path}[/green]")

    # Test parsing bills
    console.print("\n[cyan]Parsing bills...[/cyan]")
    bills = list(client.parse_bills(data_path, limit=10))

    table = Table(title=f"Sample Bills ({session_year} Session)")
    table.add_column("Bill", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Chapter", style="green")
    table.add_column("Location", style="white", max_width=30)

    for bill in bills:
        table.add_row(
            bill.citation,
            bill.current_status or "N/A",
            bill.chapter_citation or "-",
            bill.current_location or "N/A",
        )

    console.print(table)
    console.print(f"[green]✓ Parsed {len(bills)} bills[/green]")

    # Test parsing legislators
    console.print("\n[cyan]Parsing legislators...[/cyan]")
    legislators = list(client.parse_legislators(data_path, limit=10))

    table = Table(title="Sample Legislators")
    table.add_column("Name", style="cyan")
    table.add_column("Chamber", style="yellow")
    table.add_column("District", style="green")
    table.add_column("Party", style="white")

    for leg in legislators:
        table.add_row(
            leg.full_name,
            leg.chamber,
            leg.district,
            leg.party or "N/A",
        )

    console.print(table)
    console.print(f"[green]✓ Parsed {len(legislators)} legislators[/green]")

    # Test parsing law codes
    console.print("\n[cyan]Parsing law codes...[/cyan]")
    codes = list(client.parse_law_codes(data_path))

    if codes:
        table = Table(title="California Law Codes")
        table.add_column("Code", style="cyan")
        table.add_column("Title", style="white", max_width=60)

        for code in codes[:15]:  # Show first 15
            table.add_row(
                code.code,
                (code.title[:60] + "...")
                if code.title and len(code.title) > 60
                else (code.title or "N/A"),
            )

        console.print(table)
        console.print(f"[green]✓ Parsed {len(codes)} law codes[/green]")

    # Test counting chaptered bills
    console.print("\n[cyan]Counting chaptered (enacted) bills...[/cyan]")
    chaptered_count = 0
    total_count = 0
    for bill in client.parse_bills(data_path):
        total_count += 1
        if bill.is_chaptered:
            chaptered_count += 1

    console.print(
        f"[green]✓ Found {chaptered_count} chaptered bills"
        f" out of {total_count} total[/green]"
    )

    client.close()


def test_search_environmental_bills(session_year: int = 2023):
    """Test searching for environmental bills."""
    console.print(f"\n[bold blue]Testing: Search Environmental Bills ({session_year})[/bold blue]")

    client = CaliforniaLegislatureClient(data_dir=Path("data/california"))
    data_path = client.data_dir / str(session_year)

    if not data_path.exists():
        console.print("[yellow]Data not downloaded. Run test_download_and_parse first.[/yellow]")
        return

    # Search for environmental keywords
    keywords = ["water", "climate", "coastal", "environment", "conservation"]

    for keyword in keywords[:2]:  # Test first 2 keywords
        console.print(f"\n[cyan]Searching for '{keyword}'...[/cyan]")
        results = client.search_bills(session_year, keyword)

        if results:
            table = Table(title=f"Bills matching '{keyword}'")
            table.add_column("Bill", style="cyan")
            table.add_column("Status", style="yellow")
            table.add_column("Subject", style="white", max_width=50)

            for bill, version in results[:5]:
                subject = ""
                if version and version.subject:
                    subject = (
                        version.subject[:50] + "..."
                        if len(version.subject) > 50
                        else version.subject
                    )

                table.add_row(
                    bill.citation,
                    "Chaptered" if bill.is_chaptered else (bill.current_status or "N/A"),
                    subject,
                )

            console.print(table)
            console.print(f"[green]✓ Found {len(results)} bills matching '{keyword}'[/green]")
        else:
            console.print(f"[yellow]No bills found matching '{keyword}'[/yellow]")

    client.close()


def main():
    """Run all tests."""
    console.print("[bold green]===== Civitas California Legislature Tests =====[/bold green]")

    try:
        test_download_and_parse(2023)
        test_search_environmental_bills(2023)
        console.print("\n[bold green]All tests passed![/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]Test failed: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
