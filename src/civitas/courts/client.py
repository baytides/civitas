"""Client for Court Listener API (federal courts).

Credits: Court Listener API by Free Law Project (AGPL-3.0)
https://www.courtlistener.com/api/rest/v4/

Provides access to opinions from:
- U.S. Circuit Courts of Appeals (ca1-ca11, cadc, cafc)
- U.S. District Courts
- Bankruptcy Courts
- And more

Note: Higher rate limits available with API token.
Get a token at: https://www.courtlistener.com/sign-in/
"""

import os
from collections.abc import Generator
from datetime import date, timedelta

import httpx

from .models import CourtListenerCase, CourtListenerOpinion


class CourtListenerClient:
    """Client for the Court Listener API.

    Example:
        >>> client = CourtListenerClient(api_token="your-token")
        >>> for opinion in client.get_recent_opinions(court="ca9", days=30):
        ...     print(f"{opinion.case_name}: {opinion.court}")
    """

    BASE_URL = "https://www.courtlistener.com/api/rest/v4"

    # Federal Circuit Courts
    CIRCUIT_COURTS = [
        "ca1",   # First Circuit
        "ca2",   # Second Circuit
        "ca3",   # Third Circuit
        "ca4",   # Fourth Circuit
        "ca5",   # Fifth Circuit
        "ca6",   # Sixth Circuit
        "ca7",   # Seventh Circuit
        "ca8",   # Eighth Circuit
        "ca9",   # Ninth Circuit
        "ca10",  # Tenth Circuit
        "ca11",  # Eleventh Circuit
        "cadc",  # D.C. Circuit
        "cafc",  # Federal Circuit
    ]

    def __init__(
        self,
        api_token: str | None = None,
        azure_client=None,
    ):
        """Initialize Court Listener client.

        Args:
            api_token: Optional API token for higher rate limits.
                       Falls back to COURT_LISTENER_TOKEN env var.
            azure_client: Optional AzureStorageClient for document storage
        """
        self.api_token = api_token or os.getenv("COURT_LISTENER_TOKEN")
        self.azure = azure_client

        headers = {"User-Agent": "Civitas/1.0 (civic data project)"}
        if self.api_token:
            headers["Authorization"] = f"Token {self.api_token}"

        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers=headers,
            timeout=30.0,
        )

    def search_opinions(
        self,
        query: str,
        court: str | None = None,
        filed_after: date | None = None,
        filed_before: date | None = None,
        limit: int = 20,
    ) -> list[CourtListenerOpinion]:
        """Search for opinions.

        Args:
            query: Search query string
            court: Filter by court ID (e.g., "ca9", "scotus")
            filed_after: Opinions filed after this date
            filed_before: Opinions filed before this date
            limit: Maximum results to return

        Returns:
            List of matching opinions
        """
        params = {
            "q": query,
            "page_size": min(limit, 100),
        }

        if court:
            params["court"] = court
        if filed_after:
            params["filed_after"] = filed_after.isoformat()
        if filed_before:
            params["filed_before"] = filed_before.isoformat()

        response = self._client.get("/search/", params=params)
        response.raise_for_status()

        return [
            self._parse_opinion(item)
            for item in response.json().get("results", [])
        ]

    def get_recent_opinions(
        self,
        court: str | None = None,
        days: int = 30,
        limit: int = 50,
    ) -> Generator[CourtListenerOpinion, None, None]:
        """Get recent opinions from federal courts.

        Args:
            court: Filter by court ID (e.g., "ca9" for Ninth Circuit)
            days: Number of days to look back
            limit: Maximum opinions to return

        Yields:
            CourtListenerOpinion objects
        """
        filed_after = date.today() - timedelta(days=days)

        params = {
            "filed_after": filed_after.isoformat(),
            "page_size": min(limit, 100),
            "order_by": "-date_filed",
        }

        if court:
            params["court"] = court

        response = self._client.get("/opinions/", params=params)
        response.raise_for_status()

        for item in response.json().get("results", []):
            opinion = self._parse_opinion(item)

            # Store in Azure if configured
            if self.azure and opinion.plain_text:
                self.azure.upload_json(
                    opinion.model_dump(),
                    "opinion",
                    "courtlistener",
                    str(opinion.id),
                )

            yield opinion

    def get_circuit_opinions(
        self,
        days: int = 30,
        limit_per_court: int = 10,
    ) -> Generator[CourtListenerOpinion, None, None]:
        """Get recent opinions from all federal circuit courts.

        Args:
            days: Number of days to look back
            limit_per_court: Maximum opinions per court

        Yields:
            CourtListenerOpinion objects from all circuits
        """
        for court in self.CIRCUIT_COURTS:
            try:
                count = 0
                for opinion in self.get_recent_opinions(
                    court=court,
                    days=days,
                    limit=limit_per_court,
                ):
                    yield opinion
                    count += 1
                    if count >= limit_per_court:
                        break
            except Exception as e:
                print(f"Error fetching from {court}: {e}")
                continue

    def get_opinion(self, opinion_id: int) -> CourtListenerOpinion | None:
        """Get a specific opinion by ID.

        Args:
            opinion_id: Court Listener opinion ID

        Returns:
            CourtListenerOpinion or None if not found
        """
        try:
            response = self._client.get(f"/opinions/{opinion_id}/")
            response.raise_for_status()
            return self._parse_opinion(response.json())
        except httpx.HTTPStatusError:
            return None

    def get_case(self, case_id: int) -> CourtListenerCase | None:
        """Get a specific case by ID.

        Args:
            case_id: Court Listener case/cluster ID

        Returns:
            CourtListenerCase or None if not found
        """
        try:
            response = self._client.get(f"/clusters/{case_id}/")
            response.raise_for_status()
            return self._parse_case(response.json())
        except httpx.HTTPStatusError:
            return None

    def _parse_opinion(self, data: dict) -> CourtListenerOpinion:
        """Parse opinion data from API response."""
        return CourtListenerOpinion(
            id=data.get("id", 0),
            case_id=data.get("cluster_id") or data.get("cluster"),
            case_name=data.get("case_name", ""),
            court=data.get("court", ""),
            court_name=data.get("court_full_name"),
            date_created=data.get("date_filed") or data.get("date_created", date.today()),
            plain_text=data.get("plain_text"),
            html=data.get("html_with_citations"),
            opinion_type=data.get("type", "unknown"),
            author=data.get("author_str"),
            citation=(
                data.get("citations", [None])[0]
                if data.get("citations")
                else None
            ),
            absolute_url=data.get("absolute_url"),
        )

    def _parse_case(self, data: dict) -> CourtListenerCase:
        """Parse case data from API response."""
        return CourtListenerCase(
            id=data.get("id", 0),
            case_name=data.get("case_name", ""),
            docket_number=data.get("docket_number", ""),
            court=data.get("court", ""),
            court_name=data.get("court_full_name"),
            date_filed=data.get("date_filed"),
            date_terminated=data.get("date_terminated"),
            status=data.get("status"),
            nature_of_suit=data.get("nature_of_suit"),
            absolute_url=data.get("absolute_url"),
        )

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
