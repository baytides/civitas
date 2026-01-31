"""DocumentCloud client for accessing primary source documents.

DocumentCloud is a platform for analyzing, annotating, and publishing
primary source documents. This client provides access to:
- Court filings and legal documents
- Government documents and reports
- FOIA responses
- Executive orders and policy documents

Authentication (uses same tokens as MuckRock):
- Set DC_USERNAME and DC_PASSWORD environment variables, OR
- Set DC_ACCESS_TOKEN and DC_REFRESH_TOKEN for JWT auth

API endpoint: https://api.www.documentcloud.org/api/
Auth endpoint: https://accounts.muckrock.com/api/token/
"""

import os
import time
from dataclasses import dataclass, field

import httpx
from rich.console import Console

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
        >>> for result in results:
        ...     print(f"{result.document.title}: {result.document.page_count} pages")

    With Azure storage:
        >>> client = DocumentCloudClient(azure_client=azure)
        >>> client.download_document(doc_id)  # Saves to Azure
    """

    BASE_URL = "https://api.www.documentcloud.org/api"
    AUTH_URL = "https://accounts.muckrock.com/api"

    # Rate limit: 10 requests/second for authenticated users
    RATE_LIMIT = 0.1  # 100ms between requests

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        azure_client=None,
    ):
        """Initialize DocumentCloud client.

        Args:
            username: DocumentCloud username (or DC_USERNAME env var)
            password: DocumentCloud password (or DC_PASSWORD env var)
            access_token: JWT access token (or DC_ACCESS_TOKEN env var)
            refresh_token: JWT refresh token (or DC_REFRESH_TOKEN env var)
            azure_client: Optional AzureStorageClient for cloud storage
        """
        self.username = username or os.getenv("DC_USERNAME")
        self.password = password or os.getenv("DC_PASSWORD")
        self._access_token = access_token or os.getenv("DC_ACCESS_TOKEN")
        self._refresh_token = refresh_token or os.getenv("DC_REFRESH_TOKEN")
        self.azure = azure_client
        self._last_request = 0.0

        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={"User-Agent": "Civitas/1.0 (civic data project)"},
            timeout=30.0,
        )

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request
        if elapsed < self.RATE_LIMIT:
            time.sleep(self.RATE_LIMIT - elapsed)
        self._last_request = time.time()

    def _authenticate(self) -> bool:
        """Authenticate and get/refresh JWT tokens."""
        # If we have a refresh token, try to refresh
        if self._refresh_token:
            try:
                response = httpx.post(
                    f"{self.AUTH_URL}/refresh/",
                    json={"refresh": self._refresh_token},
                    timeout=30.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    self._access_token = data.get("access")
                    self._refresh_token = data.get("refresh", self._refresh_token)
                    console.print("[green]Refreshed DocumentCloud token[/green]")
                    return True
            except Exception as e:
                console.print(f"[yellow]Token refresh failed: {e}[/yellow]")

        # Fall back to username/password authentication
        if self.username and self.password:
            try:
                response = httpx.post(
                    f"{self.AUTH_URL}/token/",
                    json={"username": self.username, "password": self.password},
                    timeout=30.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    self._access_token = data.get("access")
                    self._refresh_token = data.get("refresh")
                    console.print("[green]Authenticated with DocumentCloud[/green]")
                    return True
                else:
                    console.print(f"[red]Authentication failed: {response.status_code}[/red]")
            except Exception as e:
                console.print(f"[red]Authentication error: {e}[/red]")

        return False

    def _get(self, endpoint: str, params: dict | None = None) -> httpx.Response:
        """Make authenticated GET request with rate limiting and retry."""
        self._rate_limit()

        headers = {}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        for attempt in range(3):
            try:
                response = self._client.get(endpoint, params=params, headers=headers)

                # Handle 401 - try to refresh token
                if response.status_code == 401 and attempt < 2:
                    if self._authenticate():
                        headers["Authorization"] = f"Bearer {self._access_token}"
                        continue
                    raise httpx.HTTPStatusError(
                        "Authentication required",
                        request=response.request,
                        response=response,
                    )

                response.raise_for_status()
                return response

            except (httpx.ReadTimeout, httpx.ConnectTimeout):
                if attempt == 2:
                    raise
                time.sleep(1.5 * (attempt + 1))
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise

        raise httpx.HTTPStatusError("Max retries exceeded", request=None, response=None)

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
        params = {
            "q": query,
            "per_page": min(limit, 100),
            "hl": "true" if include_mentions else "false",
        }

        url = "/documents/"
        remaining = limit

        while url and remaining > 0:
            response = self._get(url, params=params if url.startswith("/") else None)
            data = response.json()

            for item in data.get("results", []):
                doc = self._parse_document(item)
                mentions = []

                if include_mentions and "highlight" in item:
                    for page_num, texts in item["highlight"].items():
                        for text in texts:
                            mentions.append({"page": page_num, "text": text})

                results.append(DCSearchResult(document=doc, mentions=mentions))
                remaining -= 1
                if remaining <= 0:
                    break

            url = data.get("next")
            if url:
                url = url.replace(self.BASE_URL, "")
            params = None

        return results

    def get_document(self, doc_id: int | str) -> DCDocument | None:
        """Get a specific document by ID.

        Args:
            doc_id: DocumentCloud document ID

        Returns:
            DCDocument or None if not found
        """
        try:
            response = self._get(f"/documents/{doc_id}/")
            return self._parse_document(response.json())
        except Exception as e:
            console.print(f"[red]Error fetching document {doc_id}: {e}[/red]")
            return None

    def get_full_text(self, doc_id: int | str) -> str | None:
        """Get the full OCR'd text of a document.

        Args:
            doc_id: DocumentCloud document ID

        Returns:
            Full text or None
        """
        try:
            response = self._get(f"/documents/{doc_id}/")
            data = response.json()
            # Full text may be at a separate URL
            text_url = data.get("asset_url")
            if text_url:
                # Fetch the text file
                text_response = httpx.get(
                    f"{text_url}documents/{doc_id}/{doc_id}.txt",
                    timeout=60.0,
                )
                if text_response.status_code == 200:
                    return text_response.text
            return data.get("full_text")
        except Exception as e:
            console.print(f"[red]Error fetching full text for {doc_id}: {e}[/red]")
            return None

    def _parse_document(self, data: dict) -> DCDocument:
        """Parse a document from API response."""
        return DCDocument(
            id=data.get("id", 0),
            title=data.get("title", ""),
            source=data.get("source"),
            description=data.get("description"),
            full_text=data.get("full_text"),
            page_count=data.get("page_count", 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            canonical_url=data.get("canonical_url"),
            pdf_url=data.get("pdf_url"),
            data=data.get("data", {}),
        )

    def is_configured(self) -> bool:
        """Check if credentials are configured.

        Returns:
            True if authentication method is available
        """
        return bool(
            (self.username and self.password)
            or self._access_token
            or self._refresh_token
        )

    def test_connection(self) -> bool:
        """Test the connection to DocumentCloud.

        Returns:
            True if connection successful
        """
        try:
            response = self._get("/documents/", {"per_page": 1})
            return response.status_code == 200
        except Exception as e:
            console.print(f"[red]Connection test failed: {e}[/red]")
            return False

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


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
