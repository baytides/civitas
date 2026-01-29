#!/usr/bin/env python3
"""Download legal documents from Internet Archive and upload to Azure.

This script downloads:
- US Reports (Supreme Court opinions, 1991-2016)
- Historical Executive Orders (1862-1938)
- Congressional Record volumes
- Federal Register volumes

All documents are uploaded to Azure Blob Storage and can optionally be
sent to Carl (Ollama server) for AI analysis.

Usage:
    # Download everything
    python scripts/download_internet_archive.py

    # Download only US Reports
    python scripts/download_internet_archive.py --us-reports-only

    # Download and immediately process with Carl
    python scripts/download_internet_archive.py --process-with-carl

    # Dry run (list what would be downloaded)
    python scripts/download_internet_archive.py --dry-run
"""

import argparse
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="Download legal documents from Internet Archive"
    )
    parser.add_argument(
        "--us-reports-only",
        action="store_true",
        help="Only download US Reports (SCOTUS opinions)",
    )
    parser.add_argument(
        "--executive-orders-only",
        action="store_true",
        help="Only download historical Executive Orders",
    )
    parser.add_argument(
        "--congressional-record-only",
        action="store_true",
        help="Only download Congressional Record",
    )
    parser.add_argument(
        "--federal-register-only",
        action="store_true",
        help="Only download Federal Register",
    )
    parser.add_argument(
        "--congressional-limit",
        type=int,
        default=50,
        help="Limit number of Congressional Record volumes (default: 50)",
    )
    parser.add_argument(
        "--federal-register-limit",
        type=int,
        default=50,
        help="Limit number of Federal Register volumes (default: 50)",
    )
    parser.add_argument(
        "--process-with-carl",
        action="store_true",
        help="Send downloaded documents to Carl for AI analysis",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be downloaded without downloading",
    )
    parser.add_argument(
        "--no-azure",
        action="store_true",
        help="Skip Azure upload (local storage only)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/archive",
        help="Local directory for downloads (default: data/archive)",
    )
    parser.add_argument(
        "--us-reports-limit",
        type=int,
        default=None,
        help="Limit number of US Reports to download (default: all)",
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Check Azure configuration
    azure_configured = bool(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
    if not azure_configured and not args.no_azure:
        console.print(
            "[yellow]Warning: AZURE_STORAGE_CONNECTION_STRING not set. "
            "Documents will only be stored locally.[/yellow]"
        )
        console.print(
            "[yellow]Set the environment variable or use --no-azure to suppress this warning.[/yellow]"
        )

    # Initialize Azure client if configured
    azure_client = None
    if azure_configured and not args.no_azure:
        from civitas.storage.azure_blob import AzureStorageClient

        azure_client = AzureStorageClient()
        console.print("[green]Azure Storage configured[/green]")

    # Initialize Internet Archive client
    from civitas.sources.internet_archive import InternetArchiveClient

    client = InternetArchiveClient(
        data_dir=args.data_dir,
        azure_client=azure_client,
    )

    # Dry run - just list what's available
    if args.dry_run:
        console.print("\n[bold]Dry Run - Listing available documents:[/bold]\n")

        table = Table(title="Available Documents")
        table.add_column("Source", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Description")

        # Count US Reports (limit to avoid long wait)
        console.print("Counting US Reports...")
        us_reports = list(client.list_us_reports(max_results=1100))
        table.add_row("US Reports (SCOTUS)", str(len(us_reports)), "Supreme Court opinions")

        # Historical EOs is a single item
        table.add_row("Historical EOs", "1 collection", "Executive Orders 1-8030 (1862-1938)")

        # Count Congressional Record (limit count query)
        console.print("Counting Congressional Record...")
        cong_records = list(client.list_congressional_records(max_results=100))
        table.add_row(
            "Congressional Record",
            f"{len(cong_records)}+ (limit: {args.congressional_limit})",
            "Floor debates and proceedings",
        )

        # Count Federal Register (limit count query)
        console.print("Counting Federal Register...")
        fed_register = list(client.list_federal_register(max_results=100))
        table.add_row(
            "Federal Register",
            f"{len(fed_register)}+ (limit: {args.federal_register_limit})",
            "Agency rules and regulations",
        )

        console.print(table)
        return

    # Track downloaded documents for processing
    downloaded_docs = []

    # Determine what to download
    download_all = not any([
        args.us_reports_only,
        args.executive_orders_only,
        args.congressional_record_only,
        args.federal_register_only,
    ])

    # Download US Reports
    if download_all or args.us_reports_only:
        console.print("\n[bold green]═══ Downloading US Reports ═══[/bold green]")
        for doc in client.download_us_reports(max_items=args.us_reports_limit):
            downloaded_docs.append(doc)
            if doc.azure_url:
                console.print(f"  [green]Uploaded to Azure:[/green] {doc.identifier}")
            else:
                console.print(f"  [blue]Downloaded locally:[/blue] {doc.identifier}")

    # Download Historical Executive Orders
    if download_all or args.executive_orders_only:
        console.print("\n[bold green]═══ Downloading Historical Executive Orders ═══[/bold green]")
        for doc in client.download_historical_executive_orders():
            downloaded_docs.append(doc)
            if doc.azure_url:
                console.print(f"  [green]Uploaded to Azure:[/green] {doc.identifier}")
            else:
                console.print(f"  [blue]Downloaded locally:[/blue] {doc.identifier}")

    # Download Congressional Record
    if download_all or args.congressional_record_only:
        console.print("\n[bold green]═══ Downloading Congressional Record ═══[/bold green]")
        for doc in client.download_congressional_records(limit=args.congressional_limit):
            downloaded_docs.append(doc)
            if doc.azure_url:
                console.print(f"  [green]Uploaded to Azure:[/green] {doc.identifier}")
            else:
                console.print(f"  [blue]Downloaded locally:[/blue] {doc.identifier}")

    # Download Federal Register
    if download_all or args.federal_register_only:
        console.print("\n[bold green]═══ Downloading Federal Register ═══[/bold green]")
        for doc in client.download_federal_register(limit=args.federal_register_limit):
            downloaded_docs.append(doc)
            if doc.azure_url:
                console.print(f"  [green]Uploaded to Azure:[/green] {doc.identifier}")
            else:
                console.print(f"  [blue]Downloaded locally:[/blue] {doc.identifier}")

    # Summary
    console.print("\n[bold]═══ Download Summary ═══[/bold]")
    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total documents", str(len(downloaded_docs)))

    azure_uploaded = sum(1 for d in downloaded_docs if d.azure_url)
    table.add_row("Uploaded to Azure", str(azure_uploaded))

    total_size = sum(
        len(d.text_content) if d.text_content else 0
        for d in downloaded_docs
    )
    table.add_row("Total text size", f"{total_size / 1024 / 1024:.2f} MB")

    by_source = {}
    for doc in downloaded_docs:
        by_source[doc.source] = by_source.get(doc.source, 0) + 1
    for source, count in by_source.items():
        table.add_row(f"  {source}", str(count))

    console.print(table)

    # Process with Carl if requested
    if args.process_with_carl and downloaded_docs:
        console.print("\n[bold blue]═══ Processing with Carl ═══[/bold blue]")
        process_with_carl(downloaded_docs)

    client.close()


def process_with_carl(documents):
    """Send documents to Carl (Ollama) for AI analysis.

    This extracts key information like:
    - Case citations and holdings (for US Reports)
    - Executive order numbers and subjects (for EOs)
    - Key legislation discussed (for Congressional Record)
    """
    import os

    ollama_host = os.getenv("OLLAMA_HOST", "http://20.98.70.48:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")

    console.print(f"Connecting to Carl at {ollama_host}...")
    console.print(f"Using model: {ollama_model}")

    try:
        import httpx

        # Test connection
        response = httpx.get(f"{ollama_host}/api/tags", timeout=10)
        if response.status_code != 200:
            console.print("[red]Could not connect to Carl[/red]")
            return
        console.print("[green]Connected to Carl[/green]")

    except Exception as e:
        console.print(f"[red]Error connecting to Carl: {e}[/red]")
        return

    # Process documents based on type
    for doc in documents:
        console.print(f"\nProcessing: {doc.identifier}")

        if not doc.text_content:
            console.print("  [yellow]No text content, skipping[/yellow]")
            continue

        # Truncate very long documents for analysis
        text_sample = doc.text_content[:10000] if len(doc.text_content) > 10000 else doc.text_content

        # Create appropriate prompt based on source
        if doc.source == "us-reports":
            prompt = f"""Analyze this Supreme Court opinion text and extract:
1. Case name and citation
2. Key holding (1-2 sentences)
3. Constitutional provisions discussed
4. Precedents cited
5. Potential relevance to current legal challenges

Text:
{text_sample}

Provide a structured analysis."""

        elif doc.source == "executive-orders-historical":
            prompt = f"""Analyze this historical executive order text and extract:
1. Executive order number(s)
2. President who issued it
3. Subject matter
4. Key provisions
5. Historical significance

Text:
{text_sample}

Provide a structured analysis."""

        elif doc.source == "congressional-record":
            prompt = f"""Analyze this Congressional Record text and extract:
1. Date and Congress session
2. Key topics discussed
3. Legislation mentioned
4. Notable speakers and positions
5. Any constitutional or legal issues raised

Text:
{text_sample}

Provide a structured analysis."""

        elif doc.source == "federal-register":
            prompt = f"""Analyze this Federal Register text and extract:
1. Agency and rule type
2. Subject matter
3. Key provisions
4. Public comment period (if mentioned)
5. Legal authority cited

Text:
{text_sample}

Provide a structured analysis."""

        else:
            prompt = f"""Analyze this legal document and provide a summary:
{text_sample}"""

        # Send to Carl
        try:
            response = httpx.post(
                f"{ollama_host}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120,
            )

            if response.status_code == 200:
                result = response.json()
                analysis = result.get("response", "")
                console.print(f"  [green]Analysis complete[/green] ({len(analysis)} chars)")

                # Save analysis alongside the document
                analysis_path = doc.file_path.with_suffix(".analysis.txt")
                analysis_path.write_text(analysis)
                console.print(f"  Saved to: {analysis_path}")

            else:
                console.print(f"  [red]Error: {response.status_code}[/red]")

        except Exception as e:
            console.print(f"  [red]Error processing: {e}[/red]")


if __name__ == "__main__":
    main()
