"""DocumentCloud client for accessing primary source documents.

DocumentCloud is a platform for analyzing, annotating, and publishing
primary source documents. This client provides access to:
- Court filings and legal documents
- Government documents and reports
- FOIA responses
- Executive orders and policy documents

Requires DocumentCloud journalist credentials.
Set DC_USERNAME and DC_PASSWORD environment variables.

Note: This module is configured but not actively extracting data.
Run extraction when ready to ingest DocumentCloud content.
"""

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from documentcloud import DocumentCloud as DCClient

console = Console()


@dataclass
class DCDocument:
    """A document from DocumentCloud."""

    id: int
    title: str
    source: str | None = None
    description: str | None = None
    full_text: str | None = None
    page_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None
    canonical_url: str | None = None
    pdf_url: str | None = None
    data: dict = field(default_factory=dict)  # Custom metadata


@dataclass
class DCSearchResult:
    """Search result with mentions showing where keywords appear."""

    document: DCDocument
    mentions: list[dict] = field(default_factory=list)  # {page, text}


class DocumentCloudClient:
    """Client for DocumentCloud API.

    Example:
        >>> client = DocumentCloudClient()
        >>> results = client.search("executive order immigration")
        >>> for doc in results:
        ...     print(f"{doc.title}: {doc.page_count} pages")

    With Azure storage:
        >>> client = DocumentCloudClient(azure_client=azure)
        >>> client.download_document(doc_id)  # Saves to Azure
    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        azure_client=None,
    ):
        """Initialize DocumentCloud client.

        Args:
            username: DocumentCloud username (or DC_USERNAME env var)
            password: DocumentCloud password (or DC_PASSWORD env var)
            azure_client: Optional AzureStorageClient for cloud storage
        """
        self.username = username or os.getenv("DC_USERNAME")
        self.password = password or os.getenv("DC_PASSWORD")
        self.azure = azure_client
        self._client: "DCClient | None" = None

    @property
    def client(self) -> "DCClient":
        """Lazy load the DocumentCloud client."""
        if self._client is None:
            try:
                from documentcloud import DocumentCloud
            except ImportError:
                raise ImportError(
                    "documentcloud not installed. pip install documentcloud"
                )

            if self.username and self.password:
                self._client = DocumentCloud(self.username, self.password)
                console.print("[green]Authenticated with DocumentCloud[/green]")
            else:
                self._client = DocumentCloud()
                console.print(
                    "[yellow]Using DocumentCloud without authentication "
                    "(limited access)[/yellow]"
                )

        return self._client

    def search(
        self,
        query: str,
        limit: int = 100,
        include_mentions: bool = False,
    ) -> list[DCSearchResult]:
        """Search DocumentCloud for documents.

        Args:
            query: Search query (supports full-text and field search)
            limit: Maximum results to return
            include_mentions: Include keyword mention context

        Returns:
            List of search results
        """
        results = []
        dc_results = self.client.documents.search(
            query,
            mentions=include_mentions,
        )

        for doc in dc_results[:limit]:
            dc_doc = DCDocument(
                id=doc.id,
                title=doc.title,
                source=getattr(doc, "source", None),
                description=getattr(doc, "description", None),
                page_count=getattr(doc, "page_count", 0),
                created_at=str(getattr(doc, "created_at", "")),
                canonical_url=getattr(doc, "canonical_url", None),
            )

            mentions = []
            if include_mentions and hasattr(doc, "mentions"):
                for m in doc.mentions:
                    mentions.append({
                        "page": m.page,
                        "text": m.text,
                    })

            results.append(DCSearchResult(document=dc_doc, mentions=mentions))

        return results

    def get_document(self, doc_id: int) -> DCDocument | None:
        """Get a specific document by ID.

        Args:
            doc_id: DocumentCloud document ID

        Returns:
            DCDocument or None if not found
        """
        try:
            doc = self.client.documents.get(doc_id)
            return DCDocument(
                id=doc.id,
                title=doc.title,
                source=getattr(doc, "source", None),
                description=getattr(doc, "description", None),
                full_text=doc.full_text,
                page_count=getattr(doc, "page_count", 0),
                created_at=str(getattr(doc, "created_at", "")),
                updated_at=str(getattr(doc, "updated_at", "")),
                canonical_url=getattr(doc, "canonical_url", None),
                pdf_url=getattr(doc, "pdf_url", None),
                data=getattr(doc, "data", {}),
            )
        except Exception as e:
            console.print(f"[red]Error fetching document {doc_id}: {e}[/red]")
            return None

    def get_full_text(self, doc_id: int) -> str | None:
        """Get the full OCR'd text of a document.

        Args:
            doc_id: DocumentCloud document ID

        Returns:
            Full text or None
        """
        doc = self.get_document(doc_id)
        return doc.full_text if doc else None

    def is_configured(self) -> bool:
        """Check if credentials are configured.

        Returns:
            True if username and password are set
        """
        return bool(self.username and self.password)

    def test_connection(self) -> bool:
        """Test the connection to DocumentCloud.

        Returns:
            True if connection successful
        """
        try:
            # Try a simple search
            self.client.documents.search("test", mentions=False)
            return True
        except Exception as e:
            console.print(f"[red]Connection test failed: {e}[/red]")
            return False


# Predefined searches for Civitas-relevant documents
CIVITAS_SEARCHES = {
    "scotus_recent": 'source:"Supreme Court" AND created_at:[NOW-1YEAR TO NOW]',
    "executive_orders": 'title:"executive order" OR title:"presidential"',
    "doj_filings": 'source:"Department of Justice"',
    "immigration": "immigration OR deportation OR asylum OR border",
    "voting_rights": '"voting rights" OR "election" OR "ballot"',
    "environmental": 'EPA OR "environmental protection" OR climate',
    "civil_rights": '"civil rights" OR discrimination OR "equal protection"',
    "project_2025": '"Project 2025" OR "Heritage Foundation" OR "Mandate for Leadership"',
}
