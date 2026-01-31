"""MuckRock client for accessing FOIA requests and documents.

MuckRock is a platform for filing, tracking, and sharing FOIA requests.
This client provides access to:
- Completed FOIA requests and responses
- Government agency information
- FOIA request templates and guidance
- FOIAonline archive (EPA, NLRB, GSA, DLA documents)

Authentication:
- Set MUCKROCK_USERNAME and MUCKROCK_PASSWORD environment variables, OR
- Set MUCKROCK_ACCESS_TOKEN and MUCKROCK_REFRESH_TOKEN for JWT auth

API v2 endpoint: https://www.muckrock.com/api_v2/
Auth endpoint: https://accounts.muckrock.com/api/token/
"""

import os
import time
from dataclasses import dataclass, field

import httpx
from rich.console import Console

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
    """Client for MuckRock API v2.

    Example:
        >>> client = MuckRockClient()
        >>> requests = client.search_requests("executive order")
        >>> for req in requests:
        ...     print(f"{req.title}: {req.status}")

    With Azure storage:
        >>> client = MuckRockClient(azure_client=azure)
        >>> client.download_files(request_id)  # Saves to Azure
    """

    BASE_URL = "https://www.muckrock.com/api_v2"
    AUTH_URL = "https://accounts.muckrock.com/api"

    # Rate limit: 1 request/second, burst to 20/second briefly
    RATE_LIMIT = 1.0  # seconds between requests

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        azure_client=None,
    ):
        """Initialize MuckRock client.

        Args:
            username: MuckRock username (or MUCKROCK_USERNAME env var)
            password: MuckRock password (or MUCKROCK_PASSWORD env var)
            access_token: JWT access token (or MUCKROCK_ACCESS_TOKEN env var)
            refresh_token: JWT refresh token (or MUCKROCK_REFRESH_TOKEN env var)
            azure_client: Optional AzureStorageClient for cloud storage
        """
        self.username = username or os.getenv("MUCKROCK_USERNAME")
        self.password = password or os.getenv("MUCKROCK_PASSWORD")
        self._access_token = access_token or os.getenv("MUCKROCK_ACCESS_TOKEN")
        self._refresh_token = refresh_token or os.getenv("MUCKROCK_REFRESH_TOKEN")
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
                    console.print("[green]Refreshed MuckRock token[/green]")
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
                    console.print("[green]Authenticated with MuckRock[/green]")
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
        params = {"search": query, "format": "json", "page_size": min(limit, 50)}
        if status:
            params["status"] = status

        url = "/requests/"
        remaining = limit

        while url and remaining > 0:
            response = self._get(url, params=params if url.startswith("/") else None)
            data = response.json()

            for item in data.get("results", []):
                results.append(self._parse_request(item))
                remaining -= 1
                if remaining <= 0:
                    break

            url = data.get("next")
            if url:
                # Next URL is absolute, extract path
                url = url.replace(self.BASE_URL, "")
            params = None  # Params are in the next URL

        return results

    def get_request(self, request_id: int) -> FOIARequest | None:
        """Get a specific FOIA request by ID.

        Args:
            request_id: MuckRock request ID

        Returns:
            FOIARequest or None
        """
        try:
            response = self._get(f"/requests/{request_id}/", {"format": "json"})
            return self._parse_request(response.json())
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
            response = self._get(
                "/files/",
                {"foia": request_id, "format": "json", "page_size": 100},
            )
            data = response.json()

            for item in data.get("results", []):
                files.append(
                    FOIAFile(
                        id=item.get("id", 0),
                        title=item.get("title", ""),
                        file_url=item.get("ffile", ""),
                        doc_id=item.get("doc_id"),
                        pages=item.get("pages", 0),
                        date=item.get("datetime"),
                    )
                )
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
        results = []
        params = {"format": "json", "page_size": min(limit, 50)}
        if query:
            params["search"] = query
        if jurisdiction:
            params["jurisdiction"] = jurisdiction

        try:
            response = self._get("/agencies/", params)
            data = response.json()

            for item in data.get("results", []):
                results.append(
                    Agency(
                        id=item.get("id", 0),
                        name=item.get("name", ""),
                        jurisdiction=item.get("jurisdiction", {}).get("name")
                        if isinstance(item.get("jurisdiction"), dict)
                        else item.get("jurisdiction"),
                        types=item.get("types", []),
                        status=item.get("status"),
                    )
                )
        except Exception as e:
            console.print(f"[red]Error searching agencies: {e}[/red]")

        return results[:limit]

    def _parse_request(self, data: dict) -> FOIARequest:
        """Parse a FOIA request from API response."""
        agency = data.get("agency")
        agency_name = None
        if isinstance(agency, dict):
            agency_name = agency.get("name")
        elif isinstance(agency, str):
            agency_name = agency

        jurisdiction = data.get("jurisdiction")
        jurisdiction_name = None
        if isinstance(jurisdiction, dict):
            jurisdiction_name = jurisdiction.get("name")
        elif isinstance(jurisdiction, str):
            jurisdiction_name = jurisdiction

        user = data.get("user")
        username = None
        if isinstance(user, dict):
            username = user.get("username")
        elif isinstance(user, str):
            username = user

        return FOIARequest(
            id=data.get("id", 0),
            title=data.get("title", ""),
            status=data.get("status", ""),
            agency=agency_name,
            jurisdiction=jurisdiction_name,
            user=username,
            date_submitted=data.get("datetime_submitted"),
            date_due=data.get("date_due"),
            date_done=data.get("datetime_done"),
            tracking_id=data.get("tracking_id"),
            tags=data.get("tags", []),
        )

    def is_configured(self) -> bool:
        """Check if credentials are configured.

        Returns:
            True if authentication method is available
        """
        return bool((self.username and self.password) or self._access_token or self._refresh_token)

    def test_connection(self) -> bool:
        """Test the connection to MuckRock.

        Returns:
            True if connection successful
        """
        try:
            # Try accessing the API root
            response = self._get("/", {"format": "json"})
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
