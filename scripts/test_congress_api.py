#!/usr/bin/env python3
"""Test script to verify Congress.gov API client functionality."""

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich import print as rprint
from rich.console import Console
from rich.table import Table

from civitas.congress import CongressClient, BillSummary, LawListResponse

console = Console()


def test_get_laws():
    """Test fetching enacted laws."""
    console.print("\n[bold blue]Testing: Get Laws from 118th Congress[/bold blue]")

    with CongressClient() as client:
        response = client.get_laws(congress=118, limit=5)

    # Parse response
    laws = LawListResponse(**response)

    table = Table(title=f"Recent Laws (118th Congress) - {laws.pagination.count} total")
    table.add_column("Public Law", style="cyan")
    table.add_column("Bill", style="green")
    table.add_column("Title", style="white", max_width=50)
    table.add_column("Latest Action", style="yellow")

    for bill in laws.bills:
        pl_num = ""
        if bill.laws:
            pl_num = f"P.L. {bill.congress}-{bill.laws[0].number}"

        table.add_row(
            pl_num,
            f"{bill.type} {bill.number}",
            bill.title[:50] + "..." if len(bill.title) > 50 else bill.title,
            bill.latest_action.text[:40] + "..."
            if len(bill.latest_action.text) > 40
            else bill.latest_action.text,
        )

    console.print(table)
    console.print(f"[green]✓ Successfully fetched {len(laws.bills)} laws[/green]")


def test_get_bill_detail():
    """Test fetching detailed bill information."""
    console.print("\n[bold blue]Testing: Get Bill Details[/bold blue]")

    with CongressClient() as client:
        # Get a recent bill - Infrastructure Investment and Jobs Act
        response = client.get_bill(congress=117, bill_type="hr", bill_number=3684)

    bill_data = response.get("bill", {})
    console.print(f"[cyan]Bill:[/cyan] {bill_data.get('type')} {bill_data.get('number')}")
    console.print(f"[cyan]Title:[/cyan] {bill_data.get('title')}")
    console.print(f"[cyan]Introduced:[/cyan] {bill_data.get('introducedDate')}")
    console.print(f"[cyan]Policy Area:[/cyan] {bill_data.get('policyArea', {}).get('name', 'N/A')}")

    if bill_data.get("laws"):
        for law in bill_data["laws"]:
            console.print(f"[green]Enacted as:[/green] {law['type']} {law['number']}")

    console.print("[green]✓ Successfully fetched bill details[/green]")


def test_search_environmental_laws():
    """Test searching for environmental legislation."""
    console.print("\n[bold blue]Testing: Search Environmental Laws[/bold blue]")

    with CongressClient() as client:
        # Get laws from recent congresses
        response = client.get_laws(congress=117, limit=20)

    laws = LawListResponse(**response)

    # Filter for environmental keywords
    env_keywords = ["environment", "water", "air", "climate", "conservation", "wildlife", "ocean"]
    env_laws = []

    for bill in laws.bills:
        title_lower = bill.title.lower()
        if any(kw in title_lower for kw in env_keywords):
            env_laws.append(bill)

    if env_laws:
        table = Table(title="Environmental Laws Found (117th Congress)")
        table.add_column("Public Law", style="cyan")
        table.add_column("Title", style="white")

        for bill in env_laws:
            pl_num = ""
            if bill.laws:
                pl_num = f"P.L. {bill.congress}-{bill.laws[0].number}"
            table.add_row(pl_num, bill.title[:70])

        console.print(table)
    else:
        console.print("[yellow]No environmental laws found in sample[/yellow]")

    console.print(f"[green]✓ Searched {len(laws.bills)} laws[/green]")


def test_get_members():
    """Test fetching members of Congress."""
    console.print("\n[bold blue]Testing: Get Current Members of Congress[/bold blue]")

    with CongressClient() as client:
        response = client.get_members(current_member=True, limit=10)

    members = response.get("members", [])

    table = Table(title="Current Members of Congress")
    table.add_column("Name", style="cyan")
    table.add_column("Party", style="green")
    table.add_column("State", style="yellow")
    table.add_column("District", style="blue")

    for member in members[:10]:
        table.add_row(
            member.get("name", "N/A"),
            member.get("partyName", "N/A"),
            member.get("state", "N/A"),
            str(member.get("district", "N/A")),
        )

    console.print(table)
    console.print(f"[green]✓ Successfully fetched {len(members)} members[/green]")


def main():
    """Run all tests."""
    console.print("[bold green]===== Civitas Congress.gov API Tests =====[/bold green]")

    try:
        test_get_laws()
        test_get_bill_detail()
        test_search_environmental_laws()
        test_get_members()
        console.print("\n[bold green]All tests passed![/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]Test failed: {e}[/bold red]")
        raise


if __name__ == "__main__":
    main()
