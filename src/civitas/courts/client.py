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
import time
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
        "ca1",  # First Circuit
        "ca2",  # Second Circuit
        "ca3",  # Third Circuit
        "ca4",  # Fourth Circuit
        "ca5",  # Fifth Circuit
        "ca6",  # Sixth Circuit
        "ca7",  # Seventh Circuit
        "ca8",  # Eighth Circuit
        "ca9",  # Ninth Circuit
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
            timeout=60.0,
        )

    def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        """GET with retry/backoff for timeouts and transient errors."""
        for attempt in range(1, 4):
            try:
                response = self._client.get(url, params=params)
                response.raise_for_status()
                return response
            except (httpx.ReadTimeout, httpx.ConnectTimeout):
                if attempt == 3:
                    raise
                time.sleep(1.5 * attempt)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in {429, 500, 502, 503, 504} and attempt < 3:
                    time.sleep(1.5 * attempt)
                    continue
                raise

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
            params["date_filed__gte"] = filed_after.isoformat()
        if filed_before:
            params["date_filed__lte"] = filed_before.isoformat()

        response = self._get("/search/", params=params)

        return [self._parse_opinion(item) for item in response.json().get("results", [])]

    def get_recent_opinions(
        self,
        court: str | None = None,
        days: int = 30,
        limit: int | None = 50,
        page_size: int = 100,
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
        yield from self.get_opinions(
            court=court,
            filed_after=filed_after,
            filed_before=None,
            limit=limit,
            page_size=page_size,
        )

    def get_opinions(
        self,
        court: str | None = None,
        filed_after: date | None = None,
        filed_before: date | None = None,
        limit: int | None = 50,
        page_size: int = 100,
    ) -> Generator[CourtListenerOpinion, None, None]:
        """Get opinions within a date range."""
        params = {
            "page_size": min(page_size, 100),
            "order_by": "-date_filed",
        }

        if court:
            params["court"] = court
        if filed_after:
            params["date_filed__gte"] = filed_after.isoformat()
        if filed_before:
            params["date_filed__lte"] = filed_before.isoformat()

        remaining = limit if limit is not None else None
        url = "/opinions/"
        while True:
            try:
                response = self._get(url, params=params if url.startswith("/") else None)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    break
                raise
            payload = response.json()

            for item in payload.get("results", []):
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

                if remaining is not None:
                    remaining -= 1
                    if remaining <= 0:
                        return

            next_url = payload.get("next")
            if not next_url:
                break

            url = next_url
            params = None

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

    def get_scotus_opinions(
        self,
        days: int | None = None,
        filed_after: date | None = None,
        filed_before: date | None = None,
        limit: int | None = 100,
    ) -> Generator[CourtListenerOpinion, None, None]:
        """Get Supreme Court opinions.

        Args:
            days: Number of days to look back (alternative to filed_after)
            filed_after: Opinions filed after this date
            filed_before: Opinions filed before this date
            limit: Maximum opinions to return

        Yields:
            CourtListenerOpinion objects from SCOTUS
        """
        if days is not None and filed_after is None:
            filed_after = date.today() - timedelta(days=days)

        yield from self.get_opinions(
            court="scotus",
            filed_after=filed_after,
            filed_before=filed_before,
            limit=limit,
        )

    def get_scotus_opinions_by_justice(
        self,
        justice_name: str,
        limit: int = 50,
    ) -> Generator[CourtListenerOpinion, None, None]:
        """Get opinions authored by a specific SCOTUS justice.

        Args:
            justice_name: Last name of the justice (e.g., "Roberts", "Sotomayor")
            limit: Maximum opinions to return

        Yields:
            CourtListenerOpinion objects authored by the justice
        """
        # Search for opinions where the justice is listed as author
        params = {
            "court": "scotus",
            "author": justice_name,
            "page_size": min(limit, 100),
            "order_by": "-date_filed",
        }

        remaining = limit
        url = "/opinions/"
        while remaining > 0:
            try:
                response = self._get(url, params=params if url.startswith("/") else None)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    break
                raise
            payload = response.json()

            for item in payload.get("results", []):
                opinion = self._parse_opinion(item)
                yield opinion
                remaining -= 1
                if remaining <= 0:
                    return

            next_url = payload.get("next")
            if not next_url:
                break
            url = next_url
            params = None

    def get_opinion(self, opinion_id: int) -> CourtListenerOpinion | None:
        """Get a specific opinion by ID.

        Args:
            opinion_id: Court Listener opinion ID

        Returns:
            CourtListenerOpinion or None if not found
        """
        try:
            response = self._get(f"/opinions/{opinion_id}/")
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
            response = self._get(f"/clusters/{case_id}/")
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
            citation=(data.get("citations", [None])[0] if data.get("citations") else None),
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
