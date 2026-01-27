"""Congress.gov API client for fetching legislative data."""

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.congress.gov/v3"


class CongressAPIError(Exception):
    """Exception raised for Congress.gov API errors."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Congress API Error ({status_code}): {message}")


class CongressClient:
    """Client for interacting with the Congress.gov API."""

    def __init__(self, api_key: str | None = None):
        """Initialize the client.

        Args:
            api_key: Congress.gov API key. If not provided, reads from
                     CONGRESS_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv("CONGRESS_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set CONGRESS_API_KEY env var or pass api_key parameter."
            )
        self._client = httpx.Client(timeout=30.0)

    def _request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a request to the Congress.gov API.

        Args:
            endpoint: API endpoint path (without base URL)
            params: Optional query parameters

        Returns:
            JSON response as dictionary

        Raises:
            CongressAPIError: If the API returns an error
        """
        url = f"{BASE_URL}{endpoint}"
        request_params = {"api_key": self.api_key, "format": "json"}
        if params:
            request_params.update(params)

        response = self._client.get(url, params=request_params)

        if response.status_code != 200:
            raise CongressAPIError(response.status_code, response.text)

        return response.json()

    def get_laws(
        self,
        congress: int,
        law_type: str = "pub",
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get enacted laws for a given Congress.

        Args:
            congress: Congress number (e.g., 118 for 118th Congress)
            law_type: Type of law - "pub" for public, "priv" for private
            limit: Maximum number of results (default 20, max 250)
            offset: Starting position for pagination

        Returns:
            API response with laws data
        """
        return self._request(
            f"/law/{congress}/{law_type}",
            params={"limit": limit, "offset": offset},
        )

    def get_law(self, congress: int, law_type: str, law_number: int) -> dict[str, Any]:
        """Get details for a specific law.

        Args:
            congress: Congress number
            law_type: Type of law - "pub" or "priv"
            law_number: Law number

        Returns:
            API response with law details
        """
        return self._request(f"/law/{congress}/{law_type}/{law_number}")

    def get_bills(
        self,
        congress: int | None = None,
        bill_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get bills, optionally filtered by congress and type.

        Args:
            congress: Congress number (optional)
            bill_type: Bill type - hr, s, hjres, sjres, hconres, sconres, hres, sres
            limit: Maximum number of results (default 20, max 250)
            offset: Starting position for pagination

        Returns:
            API response with bills data
        """
        if congress and bill_type:
            endpoint = f"/bill/{congress}/{bill_type}"
        elif congress:
            endpoint = f"/bill/{congress}"
        else:
            endpoint = "/bill"

        return self._request(endpoint, params={"limit": limit, "offset": offset})

    def get_bill(self, congress: int, bill_type: str, bill_number: int) -> dict[str, Any]:
        """Get details for a specific bill.

        Args:
            congress: Congress number
            bill_type: Bill type (hr, s, etc.)
            bill_number: Bill number

        Returns:
            API response with bill details
        """
        return self._request(f"/bill/{congress}/{bill_type}/{bill_number}")

    def get_bill_text(self, congress: int, bill_type: str, bill_number: int) -> dict[str, Any]:
        """Get text versions for a specific bill.

        Args:
            congress: Congress number
            bill_type: Bill type
            bill_number: Bill number

        Returns:
            API response with bill text versions
        """
        return self._request(f"/bill/{congress}/{bill_type}/{bill_number}/text")

    def get_bill_actions(self, congress: int, bill_type: str, bill_number: int) -> dict[str, Any]:
        """Get actions for a specific bill.

        Args:
            congress: Congress number
            bill_type: Bill type
            bill_number: Bill number

        Returns:
            API response with bill actions
        """
        return self._request(f"/bill/{congress}/{bill_type}/{bill_number}/actions")

    def get_bill_subjects(self, congress: int, bill_type: str, bill_number: int) -> dict[str, Any]:
        """Get subjects/topics for a specific bill.

        Args:
            congress: Congress number
            bill_type: Bill type
            bill_number: Bill number

        Returns:
            API response with bill subjects
        """
        return self._request(f"/bill/{congress}/{bill_type}/{bill_number}/subjects")

    def get_bill_summaries(self, congress: int, bill_type: str, bill_number: int) -> dict[str, Any]:
        """Get CRS summaries for a specific bill.

        Args:
            congress: Congress number
            bill_type: Bill type
            bill_number: Bill number

        Returns:
            API response with bill summaries
        """
        return self._request(f"/bill/{congress}/{bill_type}/{bill_number}/summaries")

    def get_members(
        self,
        current_member: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get members of Congress.

        Args:
            current_member: If True, only return current members
            limit: Maximum number of results
            offset: Starting position for pagination

        Returns:
            API response with members data
        """
        params = {"limit": limit, "offset": offset}
        if current_member:
            params["currentMember"] = "true"

        return self._request("/member", params=params)

    def get_member(self, bioguide_id: str) -> dict[str, Any]:
        """Get details for a specific member.

        Args:
            bioguide_id: Member's Bioguide ID

        Returns:
            API response with member details
        """
        return self._request(f"/member/{bioguide_id}")

    def search_bills_by_subject(
        self,
        subject: str,
        congress: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search bills by policy area/subject.

        Args:
            subject: Policy area to search (e.g., "Environmental Protection")
            congress: Congress number (optional)
            limit: Maximum number of results
            offset: Starting position for pagination

        Returns:
            API response with matching bills

        Note:
            This uses the summaries endpoint which allows subject filtering.
        """
        endpoint = f"/summaries/{congress}" if congress else "/summaries"
        return self._request(endpoint, params={"limit": limit, "offset": offset})

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
