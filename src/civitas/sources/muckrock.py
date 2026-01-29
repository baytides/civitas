"""MuckRock client for accessing FOIA requests and documents.

MuckRock is a platform for filing, tracking, and sharing FOIA requests.
This client provides access to:
- Completed FOIA requests and responses
- Government agency information
- FOIA request templates and guidance
- FOIAonline archive (EPA, NLRB, GSA, DLA documents)

Requires MuckRock journalist credentials.
Set MUCKROCK_USERNAME and MUCKROCK_PASSWORD environment variables.

Note: This module is configured but not actively extracting data.
Run extraction when ready to ingest MuckRock content.
"""

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from muckrock import MuckRock as MRClient

console = Console()


@dataclass
class FOIARequest:
    """A FOIA request from MuckRock."""

    id: int
    title: str
    status: str  # processing, awaiting_response, completed, rejected, etc.
    agency: str | None = None
    jurisdiction: str | None = None
    user: str | None = None
    date_submitted: str | None = None
    date_due: str | None = None
    date_done: str | None = None
    tracking_id: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class FOIAFile:
    """A file/document from a FOIA response."""

    id: int
    title: str
    file_url: str
    doc_id: int | None = None  # DocumentCloud ID if uploaded
    pages: int = 0
    date: str | None = None


@dataclass
class Agency:
    """A government agency in MuckRock's database."""

    id: int
    name: str
    jurisdiction: str | None = None
    types: list[str] = field(default_factory=list)
    status: str | None = None  # open, appeals, fee, not_responding, etc.


class MuckRockClient:
    """Client for MuckRock API.

    Example:
        >>> client = MuckRockClient()
        >>> requests = client.search_requests("executive order")
        >>> for req in requests:
        ...     print(f"{req.title}: {req.status}")

    With Azure storage:
        >>> client = MuckRockClient(azure_client=azure)
        >>> client.download_files(request_id)  # Saves to Azure
    """

    # Rate limit: 1 request/second, burst to 20/second briefly
    RATE_LIMIT = 1.0  # seconds between requests

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        azure_client=None,
    ):
        """Initialize MuckRock client.

        Args:
            username: MuckRock username (or MUCKROCK_USERNAME env var)
            password: MuckRock password (or MUCKROCK_PASSWORD env var)
            azure_client: Optional AzureStorageClient for cloud storage
        """
        self.username = username or os.getenv("MUCKROCK_USERNAME")
        self.password = password or os.getenv("MUCKROCK_PASSWORD")
        self.azure = azure_client
        self._client: "MRClient | None" = None

    @property
    def client(self) -> "MRClient":
        """Lazy load the MuckRock client."""
        if self._client is None:
            try:
                from muckrock import MuckRock
            except ImportError:
                raise ImportError(
                    "python-muckrock not installed. pip install python-muckrock"
                )

            if not self.username or not self.password:
                raise ValueError(
                    "MuckRock credentials required. "
                    "Set MUCKROCK_USERNAME and MUCKROCK_PASSWORD environment variables."
                )

            self._client = MuckRock(self.username, self.password)
            console.print("[green]Authenticated with MuckRock[/green]")

        return self._client

    def search_requests(
        self,
        query: str,
        status: str | None = None,
        limit: int = 100,
    ) -> list[FOIARequest]:
        """Search FOIA requests.

        Args:
            query: Search query
            status: Filter by status (completed, processing, etc.)
            limit: Maximum results

        Returns:
            List of matching FOIA requests
        """
        results = []

        request_list = self.client.requests.list(search=query)

        count = 0
        for req in request_list:
            if status and getattr(req, "status", "") != status:
                continue

            results.append(FOIARequest(
                id=req.id,
                title=getattr(req, "title", ""),
                status=getattr(req, "status", ""),
                agency=getattr(req, "agency", {}).get("name") if hasattr(req, "agency") else None,
                jurisdiction=getattr(req, "jurisdiction", {}).get("name") if hasattr(req, "jurisdiction") else None,
                user=getattr(req, "user", {}).get("username") if hasattr(req, "user") else None,
                date_submitted=str(getattr(req, "date_submitted", "")),
                date_due=str(getattr(req, "date_due", "")),
                date_done=str(getattr(req, "date_done", "")),
                tracking_id=getattr(req, "tracking_id", None),
                tags=getattr(req, "tags", []),
            ))

            count += 1
            if count >= limit:
                break

        return results

    def get_request(self, request_id: int) -> FOIARequest | None:
        """Get a specific FOIA request by ID.

        Args:
            request_id: MuckRock request ID

        Returns:
            FOIARequest or None
        """
        try:
            req = self.client.requests.retrieve(request_id)
            return FOIARequest(
                id=req.id,
                title=getattr(req, "title", ""),
                status=getattr(req, "status", ""),
                agency=getattr(req, "agency", {}).get("name") if hasattr(req, "agency") else None,
                jurisdiction=getattr(req, "jurisdiction", {}).get("name") if hasattr(req, "jurisdiction") else None,
                user=getattr(req, "user", {}).get("username") if hasattr(req, "user") else None,
                date_submitted=str(getattr(req, "date_submitted", "")),
                date_due=str(getattr(req, "date_due", "")),
                date_done=str(getattr(req, "date_done", "")),
                tracking_id=getattr(req, "tracking_id", None),
                tags=getattr(req, "tags", []),
            )
        except Exception as e:
            console.print(f"[red]Error fetching request {request_id}: {e}[/red]")
            return None

    def get_files(self, request_id: int) -> list[FOIAFile]:
        """Get files/documents from a FOIA request.

        Args:
            request_id: MuckRock request ID

        Returns:
            List of files from the request
        """
        files = []

        try:
            req = self.client.requests.retrieve(request_id)
            comms = req.get_communications()

            for comm in comms:
                for f in comm.get_files():
                    files.append(FOIAFile(
                        id=getattr(f, "id", 0),
                        title=getattr(f, "title", ""),
                        file_url=getattr(f, "ffile", ""),
                        doc_id=getattr(f, "doc_id", None),
                        pages=getattr(f, "pages", 0),
                        date=str(getattr(f, "date", "")),
                    ))

        except Exception as e:
            console.print(f"[red]Error fetching files for request {request_id}: {e}[/red]")

        return files

    def search_agencies(
        self,
        query: str | None = None,
        jurisdiction: str | None = None,
        limit: int = 100,
    ) -> list[Agency]:
        """Search government agencies.

        Args:
            query: Search query for agency name
            jurisdiction: Filter by jurisdiction
            limit: Maximum results

        Returns:
            List of matching agencies
        """
        # Note: This would need the agencies endpoint which may work differently
        # Placeholder for now
        console.print("[yellow]Agency search not fully implemented[/yellow]")
        return []

    def is_configured(self) -> bool:
        """Check if credentials are configured.

        Returns:
            True if username and password are set
        """
        return bool(self.username and self.password)

    def test_connection(self) -> bool:
        """Test the connection to MuckRock.

        Returns:
            True if connection successful
        """
        try:
            # Try listing requests
            list(self.client.requests.list(search="test"))
            return True
        except Exception as e:
            console.print(f"[red]Connection test failed: {e}[/red]")
            return False


# Predefined searches for Civitas-relevant FOIA requests
CIVITAS_SEARCHES = {
    "executive_orders": "executive order",
    "immigration": "immigration deportation ICE CBP",
    "epa_regulations": "EPA environmental regulation",
    "doj_policy": "DOJ Department of Justice policy",
    "election_security": "election security voting",
    "civil_rights": "civil rights discrimination",
    "project_2025": "Project 2025 Heritage Foundation",
    "agency_guidance": "guidance memorandum policy",
}

# Key agencies for Civitas
KEY_AGENCIES = [
    "Environmental Protection Agency",
    "Department of Justice",
    "Department of Homeland Security",
    "Immigration and Customs Enforcement",
    "Customs and Border Protection",
    "Department of State",
    "Department of Education",
    "Department of Labor",
    "National Labor Relations Board",
    "Federal Trade Commission",
]
