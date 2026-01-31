"""Internet Archive client for downloading legal documents.

Provides access to:
- US Reports (Supreme Court opinions)
- Historical Executive Orders
- Congressional Record
- Federal Register
- Code of Federal Regulations

Uses the internetarchive Python library for downloads and the
scrape/metadata APIs for discovery.
"""

import os
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class IAItem:
    """An item from the Internet Archive."""

    identifier: str
    title: str
    mediatype: str | None = None
    year: str | None = None
    description: str | None = None
    collection: list[str] = field(default_factory=list)
    files: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def text_files(self) -> list[dict]:
        """Get text/OCR files from this item."""
        return [
            f
            for f in self.files
            if f.get("name", "").endswith(("_djvu.txt", ".txt"))
            and f.get("format") in ("DjVuTXT", "Text", None)
        ]

    @property
    def pdf_files(self) -> list[dict]:
        """Get PDF files from this item."""
        return [f for f in self.files if f.get("name", "").endswith(".pdf")]


@dataclass
class DownloadedDocument:
    """A document downloaded from Internet Archive."""

    identifier: str
    title: str
    source: str  # e.g., "us-reports", "executive-orders"
    file_path: Path
    text_content: str | None = None
    year: str | None = None
    volume: str | None = None
    metadata: dict = field(default_factory=dict)
    azure_url: str | None = None  # URL in Azure storage if uploaded


class InternetArchiveClient:
    """Client for downloading legal documents from Internet Archive.

    Example:
        >>> client = InternetArchiveClient(data_dir="data/archive")
        >>> for doc in client.download_us_reports():
        ...     print(f"Downloaded: {doc.title}")
        ...     print(f"Text length: {len(doc.text_content)}")

    With Azure storage:
        >>> from civitas.storage.azure_blob import AzureStorageClient
        >>> azure = AzureStorageClient()
        >>> client = InternetArchiveClient(azure_client=azure)
        >>> for doc in client.download_us_reports():
        ...     print(f"Azure URL: {doc.azure_url}")
    """

    SEARCH_API = "https://archive.org/advancedsearch.php"
    METADATA_API = "https://archive.org/metadata"
    DOWNLOAD_URL = "https://archive.org/download"

    # Known collections for legal documents
    COLLECTIONS = {
        "scotus": "pub_united-states-supreme-court-cases-adjudged",  # SCOTUS opinions
        "congress-hearings": "pub_united-states-congress-hearings-prints-and-reports",
        "executive-orders": "PresidentialExecutiveOrdersVolume1",  # EOs 1862-1938
        "government-docs": "USGovernmentDocuments",  # General gov docs
    }

    def __init__(
        self,
        data_dir: Path | str = "data/archive",
        s3_access_key: str | None = None,
        s3_secret_key: str | None = None,
        azure_client=None,
    ):
        """Initialize Internet Archive client.

        Args:
            data_dir: Local directory for downloaded files
            s3_access_key: Optional IA S3 access key
            s3_secret_key: Optional IA S3 secret key
            azure_client: Optional AzureStorageClient for cloud storage
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.s3_access_key = s3_access_key or os.getenv("IA_S3_ACCESS_KEY")
        self.s3_secret_key = s3_secret_key or os.getenv("IA_S3_SECRET_KEY")
        self.azure = azure_client

        self._client = httpx.Client(
            timeout=60.0,
            follow_redirects=True,
            headers={"User-Agent": "Civitas/1.0 (civic data project)"},
        )

    def search(
        self,
        query: str,
        fields: list[str] | None = None,
        rows: int = 100,
        max_results: int | None = None,
    ) -> Generator[IAItem, None, None]:
        """Search the Internet Archive using Advanced Search API.

        Args:
            query: Lucene-style query
                (e.g., "collection:pub_united-states-supreme-court-cases-adjudged")
            fields: Fields to return (default: identifier, title, mediatype, year)
            rows: Number of results per page (max 10000)
            max_results: Maximum total results to return (None for all)

        Yields:
            IAItem objects
        """
        fields = fields or ["identifier", "title", "mediatype", "year", "description"]
        start = 0
        total_yielded = 0

        while True:
            # Build field parameters
            params = {
                "q": query,
                "rows": min(rows, 1000),  # Cap at 1000 per request
                "start": start,
                "output": "json",
            }
            # Add each field as a separate fl[] parameter
            for f in fields:
                params["fl[]"] = f

            # Build URL with proper field encoding
            url = f"{self.SEARCH_API}?q={query}&rows={rows}&start={start}&output=json"
            for f in fields:
                url += f"&fl[]={f}"

            response = self._client.get(url)
            response.raise_for_status()
            data = response.json()

            docs = data.get("response", {}).get("docs", [])
            num_found = data.get("response", {}).get("numFound", 0)

            if not docs:
                break

            for item in docs:
                yield IAItem(
                    identifier=item.get("identifier", ""),
                    title=item.get("title", ""),
                    mediatype=item.get("mediatype"),
                    year=item.get("year"),
                    description=item.get("description"),
                )
                total_yielded += 1

                if max_results and total_yielded >= max_results:
                    return

            start += len(docs)
            if start >= num_found:
                break

    def get_item_metadata(self, identifier: str) -> IAItem:
        """Get full metadata for an item.

        Args:
            identifier: Item identifier

        Returns:
            IAItem with full metadata and file list
        """
        url = f"{self.METADATA_API}/{identifier}"
        response = self._client.get(url)
        response.raise_for_status()
        data = response.json()

        metadata = data.get("metadata", {})
        files = data.get("files", [])

        # Handle collection as string or list
        collection = metadata.get("collection", [])
        if isinstance(collection, str):
            collection = [collection]

        return IAItem(
            identifier=identifier,
            title=metadata.get("title", ""),
            mediatype=metadata.get("mediatype"),
            year=metadata.get("year"),
            description=metadata.get("description"),
            collection=collection,
            files=files,
            metadata=metadata,
        )

    def download_file(
        self,
        identifier: str,
        filename: str,
        dest_dir: Path | None = None,
    ) -> Path:
        """Download a specific file from an item.

        Args:
            identifier: Item identifier
            filename: File name within the item
            dest_dir: Destination directory (default: data_dir/identifier)

        Returns:
            Path to downloaded file
        """
        dest_dir = dest_dir or self.data_dir / identifier
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / filename

        if dest_path.exists():
            return dest_path

        url = f"{self.DOWNLOAD_URL}/{identifier}/{filename}"
        response = self._client.get(url)
        response.raise_for_status()
        dest_path.write_bytes(response.content)

        return dest_path

    def download_text(self, identifier: str, filename: str) -> str:
        """Download and return text content from a file.

        Args:
            identifier: Item identifier
            filename: File name (usually *_djvu.txt)

        Returns:
            Text content
        """
        url = f"{self.DOWNLOAD_URL}/{identifier}/{filename}"
        response = self._client.get(url)
        response.raise_for_status()
        return response.text

    # =========================================================================
    # US Reports (Supreme Court Opinions)
    # =========================================================================

    def list_us_reports(self, max_results: int | None = None) -> Generator[IAItem, None, None]:
        """List all US Reports volumes available.

        Args:
            max_results: Maximum number of items to return

        Yields:
            IAItem for each volume
        """
        # SCOTUS cases collection
        yield from self.search(
            f"collection:{self.COLLECTIONS['scotus']}",
            max_results=max_results,
        )

    def download_us_reports(
        self,
        volumes: list[str] | None = None,
        text_only: bool = True,
        max_items: int | None = None,
    ) -> Generator[DownloadedDocument, None, None]:
        """Download US Reports volumes with full text.

        Args:
            volumes: Specific volume numbers to download (e.g., ["502", "503"])
                    If None, downloads all available
            text_only: If True, only download text files (not PDFs)
            max_items: Maximum number of items to download

        Yields:
            DownloadedDocument objects with text content
        """
        import re

        console.print("[bold blue]Fetching US Reports collection...[/bold blue]")

        # Get items from SCOTUS collection
        items = list(self.list_us_reports(max_results=max_items))
        console.print(f"Found {len(items)} items")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading US Reports...", total=len(items))

            for item in items:
                # Filter by volume if specified
                if volumes:
                    volume_match = False
                    for vol in volumes:
                        if vol in item.identifier or vol in item.title:
                            volume_match = True
                            break
                    if not volume_match:
                        progress.advance(task)
                        continue

                progress.update(task, description=f"Downloading {item.identifier}...")

                try:
                    # Get full metadata with file list
                    full_item = self.get_item_metadata(item.identifier)

                    # Find text file
                    text_files = full_item.text_files
                    if not text_files:
                        console.print(
                            f"[yellow]No text file for {item.identifier}[/yellow]"
                        )
                        progress.advance(task)
                        continue

                    # Download text
                    text_file = text_files[0]
                    text_content = self.download_text(
                        item.identifier, text_file["name"]
                    )

                    # Save locally
                    dest_dir = self.data_dir / "us-reports"
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    text_path = dest_dir / f"{item.identifier}.txt"
                    text_path.write_text(text_content)

                    # Extract volume number from identifier
                    volume = None
                    vol_match = re.search(r"(\d+)", item.identifier)
                    if vol_match:
                        volume = vol_match.group(1)

                    # Extract year for Azure organization
                    year = None
                    if item.year:
                        year_match = re.search(r"(\d{4})", str(item.year))
                        if year_match:
                            year = int(year_match.group(1))

                    # Upload to Azure if configured
                    azure_url = None
                    if self.azure:
                        azure_url = self.azure.upload_document(
                            text_content.encode("utf-8"),
                            "archive",
                            "us-reports",
                            item.identifier,
                            "txt",
                            year=year,
                        )

                    yield DownloadedDocument(
                        identifier=item.identifier,
                        title=item.title,
                        source="us-reports",
                        file_path=text_path,
                        text_content=text_content,
                        year=item.year,
                        volume=volume,
                        metadata=full_item.metadata,
                        azure_url=azure_url,
                    )

                except Exception as e:
                    console.print(f"[red]Error downloading {item.identifier}: {e}[/red]")

                progress.advance(task)

    # =========================================================================
    # Historical Executive Orders
    # =========================================================================

    def download_historical_executive_orders(
        self,
    ) -> Generator[DownloadedDocument, None, None]:
        """Download historical executive orders (1862-1938).

        Yields:
            DownloadedDocument objects
        """
        console.print(
            "[bold blue]Fetching Historical Executive Orders...[/bold blue]"
        )

        # The main EO collection
        identifier = "PresidentialExecutiveOrdersVolume1"

        try:
            item = self.get_item_metadata(identifier)

            # Find text files
            text_files = item.text_files
            if not text_files:
                console.print("[yellow]No text files found[/yellow]")
                return

            for text_file in text_files:
                console.print(f"Downloading {text_file['name']}...")

                text_content = self.download_text(identifier, text_file["name"])

                # Save locally
                dest_dir = self.data_dir / "executive-orders"
                dest_dir.mkdir(parents=True, exist_ok=True)
                text_path = dest_dir / text_file["name"]
                text_path.write_text(text_content)

                # Upload to Azure if configured
                azure_url = None
                if self.azure:
                    # Use a safe filename for the document ID
                    safe_name = text_file["name"].replace(".txt", "").replace("_djvu", "")
                    azure_url = self.azure.upload_document(
                        text_content.encode("utf-8"),
                        "archive",
                        "executive-orders-historical",
                        safe_name,
                        "txt",
                        year=1900,  # Historical EOs span 1862-1938
                    )

                yield DownloadedDocument(
                    identifier=identifier,
                    title=item.title,
                    source="executive-orders-historical",
                    file_path=text_path,
                    text_content=text_content,
                    year="1862-1938",
                    metadata=item.metadata,
                    azure_url=azure_url,
                )

        except Exception as e:
            console.print(f"[red]Error downloading executive orders: {e}[/red]")

    # =========================================================================
    # Congressional Record
    # =========================================================================

    def list_congressional_records(
        self, max_results: int | None = None
    ) -> Generator[IAItem, None, None]:
        """List available Congressional Record volumes.

        Args:
            max_results: Maximum number of items to return

        Yields:
            IAItem for each volume
        """
        yield from self.search(
            'title:"congressional record" AND mediatype:texts',
            max_results=max_results,
        )

    def download_congressional_records(
        self,
        limit: int | None = None,
    ) -> Generator[DownloadedDocument, None, None]:
        """Download Congressional Record volumes.

        Args:
            limit: Maximum number of volumes to download

        Yields:
            DownloadedDocument objects
        """
        import re

        console.print("[bold blue]Fetching Congressional Record...[/bold blue]")

        items = list(self.list_congressional_records())
        if limit:
            items = items[:limit]

        console.print(f"Found {len(items)} Congressional Record items")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading...", total=len(items))

            for item in items:
                progress.update(
                    task, description=f"Downloading {item.identifier[:40]}..."
                )

                try:
                    full_item = self.get_item_metadata(item.identifier)
                    text_files = full_item.text_files

                    if not text_files:
                        progress.advance(task)
                        continue

                    text_file = text_files[0]
                    text_content = self.download_text(
                        item.identifier, text_file["name"]
                    )

                    dest_dir = self.data_dir / "congressional-record"
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    text_path = dest_dir / f"{item.identifier}.txt"
                    text_path.write_text(text_content)

                    # Extract year for Azure organization
                    year = None
                    if item.year:
                        year_match = re.search(r"(\d{4})", str(item.year))
                        if year_match:
                            year = int(year_match.group(1))

                    # Upload to Azure if configured
                    azure_url = None
                    if self.azure:
                        azure_url = self.azure.upload_document(
                            text_content.encode("utf-8"),
                            "archive",
                            "congressional-record",
                            item.identifier,
                            "txt",
                            year=year,
                        )

                    yield DownloadedDocument(
                        identifier=item.identifier,
                        title=item.title,
                        source="congressional-record",
                        file_path=text_path,
                        text_content=text_content,
                        year=item.year,
                        metadata=full_item.metadata,
                        azure_url=azure_url,
                    )

                except Exception as e:
                    console.print(
                        f"[red]Error downloading {item.identifier}: {e}[/red]"
                    )

                progress.advance(task)

    # =========================================================================
    # Federal Register
    # =========================================================================

    def list_federal_register(
        self, max_results: int | None = None
    ) -> Generator[IAItem, None, None]:
        """List available Federal Register volumes.

        Args:
            max_results: Maximum number of items to return

        Yields:
            IAItem for each volume
        """
        yield from self.search(
            'title:"federal register" AND mediatype:texts',
            max_results=max_results,
        )

    def download_federal_register(
        self,
        limit: int | None = None,
    ) -> Generator[DownloadedDocument, None, None]:
        """Download Federal Register volumes.

        Args:
            limit: Maximum number of volumes to download

        Yields:
            DownloadedDocument objects
        """
        import re

        console.print("[bold blue]Fetching Federal Register...[/bold blue]")

        items = list(self.list_federal_register())
        if limit:
            items = items[:limit]

        console.print(f"Found {len(items)} Federal Register items")

        for item in items:
            try:
                full_item = self.get_item_metadata(item.identifier)
                text_files = full_item.text_files

                if not text_files:
                    continue

                text_file = text_files[0]
                text_content = self.download_text(item.identifier, text_file["name"])

                dest_dir = self.data_dir / "federal-register"
                dest_dir.mkdir(parents=True, exist_ok=True)
                text_path = dest_dir / f"{item.identifier}.txt"
                text_path.write_text(text_content)

                # Extract year for Azure organization
                year = None
                if item.year:
                    year_match = re.search(r"(\d{4})", str(item.year))
                    if year_match:
                        year = int(year_match.group(1))

                # Upload to Azure if configured
                azure_url = None
                if self.azure:
                    azure_url = self.azure.upload_document(
                        text_content.encode("utf-8"),
                        "archive",
                        "federal-register",
                        item.identifier,
                        "txt",
                        year=year,
                    )

                yield DownloadedDocument(
                    identifier=item.identifier,
                    title=item.title,
                    source="federal-register",
                    file_path=text_path,
                    text_content=text_content,
                    year=item.year,
                    metadata=full_item.metadata,
                    azure_url=azure_url,
                )

            except Exception as e:
                console.print(f"[red]Error downloading {item.identifier}: {e}[/red]")

    # =========================================================================
    # Bulk Download All Legal Documents
    # =========================================================================

    def download_all(
        self,
        include_us_reports: bool = True,
        include_executive_orders: bool = True,
        include_congressional_record: bool = True,
        include_federal_register: bool = True,
        congressional_limit: int | None = 50,
        federal_register_limit: int | None = 50,
    ) -> Generator[DownloadedDocument, None, None]:
        """Download all available legal documents.

        Args:
            include_us_reports: Download US Reports
            include_executive_orders: Download historical EOs
            include_congressional_record: Download Congressional Record
            include_federal_register: Download Federal Register
            congressional_limit: Limit congressional record downloads
            federal_register_limit: Limit federal register downloads

        Yields:
            DownloadedDocument objects
        """
        if include_us_reports:
            console.print("\n[bold green]═══ US Reports ═══[/bold green]")
            yield from self.download_us_reports()

        if include_executive_orders:
            console.print("\n[bold green]═══ Historical Executive Orders ═══[/bold green]")
            yield from self.download_historical_executive_orders()

        if include_congressional_record:
            console.print("\n[bold green]═══ Congressional Record ═══[/bold green]")
            yield from self.download_congressional_records(limit=congressional_limit)

        if include_federal_register:
            console.print("\n[bold green]═══ Federal Register ═══[/bold green]")
            yield from self.download_federal_register(limit=federal_register_limit)

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
