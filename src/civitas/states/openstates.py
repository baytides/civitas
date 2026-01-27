"""Open States API client for state legislative data.

API Documentation: https://docs.openstates.org/api-v3/
Credits: Open States Project (GPL-3.0 / CC0-1.0)
https://github.com/openstates

Provides access to:
- State bills and legislation
- State legislators and committees
- Legislative sessions
- Voting records
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Generator, Optional
import os

import httpx


@dataclass
class StateLegislator:
    """A state legislator from Open States."""

    id: str
    name: str
    state: str
    chamber: str  # "upper" or "lower"
    party: str
    district: str
    image: Optional[str] = None
    email: Optional[str] = None
    current_role: Optional[dict] = None
    offices: list[dict] = field(default_factory=list)


@dataclass
class StateBill:
    """A state bill from Open States."""

    id: str
    identifier: str  # e.g., "HB 123"
    title: str
    state: str
    session: str
    chamber: str  # "upper" or "lower"
    classification: list[str] = field(default_factory=list)  # ["bill", "resolution"]
    subject: list[str] = field(default_factory=list)
    abstracts: list[dict] = field(default_factory=list)
    sponsors: list[dict] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    votes: list[dict] = field(default_factory=list)
    versions: list[dict] = field(default_factory=list)  # Bill text versions
    sources: list[dict] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    first_action_date: Optional[date] = None
    latest_action_date: Optional[date] = None
    latest_action_description: Optional[str] = None


@dataclass
class StateSession:
    """A legislative session."""

    identifier: str
    name: str
    classification: str  # "primary" or "special"
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class OpenStatesClient:
    """Client for the Open States API v3.

    API Documentation: https://docs.openstates.org/api-v3/

    Requires an API key from: https://openstates.org/accounts/login/

    Example:
        >>> client = OpenStatesClient()
        >>> # Get recent bills from California
        >>> for bill in client.get_bills(state="ca", session="2023-2024"):
        ...     print(f"{bill.identifier}: {bill.title}")
        >>> # Search for bills by topic
        >>> for bill in client.search_bills("climate change", states=["ca", "ny"]):
        ...     print(f"{bill.state} {bill.identifier}")
    """

    BASE_URL = "https://v3.openstates.org"

    # State codes to full names
    STATES = {
        "al": "Alabama", "ak": "Alaska", "az": "Arizona", "ar": "Arkansas",
        "ca": "California", "co": "Colorado", "ct": "Connecticut", "de": "Delaware",
        "fl": "Florida", "ga": "Georgia", "hi": "Hawaii", "id": "Idaho",
        "il": "Illinois", "in": "Indiana", "ia": "Iowa", "ks": "Kansas",
        "ky": "Kentucky", "la": "Louisiana", "me": "Maine", "md": "Maryland",
        "ma": "Massachusetts", "mi": "Michigan", "mn": "Minnesota", "ms": "Mississippi",
        "mo": "Missouri", "mt": "Montana", "ne": "Nebraska", "nv": "Nevada",
        "nh": "New Hampshire", "nj": "New Jersey", "nm": "New Mexico", "ny": "New York",
        "nc": "North Carolina", "nd": "North Dakota", "oh": "Ohio", "ok": "Oklahoma",
        "or": "Oregon", "pa": "Pennsylvania", "ri": "Rhode Island", "sc": "South Carolina",
        "sd": "South Dakota", "tn": "Tennessee", "tx": "Texas", "ut": "Utah",
        "vt": "Vermont", "va": "Virginia", "wa": "Washington", "wv": "West Virginia",
        "wi": "Wisconsin", "wy": "Wyoming", "dc": "District of Columbia",
        "pr": "Puerto Rico",
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Open States client.

        Args:
            api_key: Open States API key (or set OPENSTATES_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENSTATES_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Open States API key required. "
                "Get one at https://openstates.org/accounts/login/ "
                "and set OPENSTATES_API_KEY environment variable."
            )

        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "X-API-KEY": self.api_key,
                "User-Agent": "Civitas/1.0 (civic data project)",
            },
            timeout=30.0,
        )

    def get_jurisdictions(self) -> list[dict]:
        """Get all available jurisdictions (states)."""
        response = self._client.get("/jurisdictions")
        response.raise_for_status()
        return response.json()["results"]

    def get_sessions(self, state: str) -> list[StateSession]:
        """Get legislative sessions for a state.

        Args:
            state: Two-letter state code (e.g., "ca")
        """
        response = self._client.get(
            "/jurisdictions",
            params={"classification": "state", "abbr": state.lower()}
        )
        response.raise_for_status()

        results = response.json()["results"]
        if not results:
            return []

        jurisdiction = results[0]
        sessions = []

        for session_data in jurisdiction.get("legislative_sessions", []):
            sessions.append(StateSession(
                identifier=session_data["identifier"],
                name=session_data["name"],
                classification=session_data.get("classification", "primary"),
                start_date=self._parse_date(session_data.get("start_date")),
                end_date=self._parse_date(session_data.get("end_date")),
            ))

        return sessions

    def get_bills(
        self,
        state: str,
        session: Optional[str] = None,
        chamber: Optional[str] = None,
        classification: Optional[str] = None,
        subject: Optional[str] = None,
        updated_since: Optional[date] = None,
        limit: int = 100,
    ) -> Generator[StateBill, None, None]:
        """Get bills for a state.

        Args:
            state: Two-letter state code
            session: Session identifier (e.g., "2023-2024")
            chamber: "upper" or "lower"
            classification: "bill", "resolution", etc.
            subject: Subject filter
            updated_since: Only bills updated after this date
            limit: Maximum number of bills to return
        """
        params = {
            "jurisdiction": f"ocd-jurisdiction/country:us/state:{state.lower()}/government",
            "per_page": min(limit, 100),
        }

        if session:
            params["session"] = session
        if chamber:
            params["chamber"] = chamber
        if classification:
            params["classification"] = classification
        if subject:
            params["subject"] = subject
        if updated_since:
            params["updated_since"] = updated_since.isoformat()

        page = 1
        total_fetched = 0

        while total_fetched < limit:
            params["page"] = page
            response = self._client.get("/bills", params=params)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if not results:
                break

            for bill_data in results:
                if total_fetched >= limit:
                    break
                yield self._parse_bill(bill_data)
                total_fetched += 1

            # Check if there are more pages
            pagination = data.get("pagination", {})
            if page >= pagination.get("max_page", 1):
                break

            page += 1

    def search_bills(
        self,
        query: str,
        states: Optional[list[str]] = None,
        session: Optional[str] = None,
        limit: int = 50,
    ) -> Generator[StateBill, None, None]:
        """Search bills across states.

        Args:
            query: Search query
            states: List of state codes to search (default: all)
            session: Session identifier
            limit: Maximum results
        """
        params = {
            "q": query,
            "per_page": min(limit, 100),
        }

        if states:
            jurisdictions = [
                f"ocd-jurisdiction/country:us/state:{s.lower()}/government"
                for s in states
            ]
            params["jurisdiction"] = jurisdictions

        if session:
            params["session"] = session

        page = 1
        total_fetched = 0

        while total_fetched < limit:
            params["page"] = page
            response = self._client.get("/bills", params=params)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if not results:
                break

            for bill_data in results:
                if total_fetched >= limit:
                    break
                yield self._parse_bill(bill_data)
                total_fetched += 1

            pagination = data.get("pagination", {})
            if page >= pagination.get("max_page", 1):
                break

            page += 1

    def get_bill(self, state: str, session: str, identifier: str) -> Optional[StateBill]:
        """Get a specific bill by identifier.

        Args:
            state: Two-letter state code
            session: Session identifier
            identifier: Bill identifier (e.g., "HB 123")
        """
        jurisdiction = f"ocd-jurisdiction/country:us/state:{state.lower()}/government"
        params = {
            "jurisdiction": jurisdiction,
            "session": session,
            "identifier": identifier,
        }

        response = self._client.get("/bills", params=params)
        response.raise_for_status()

        results = response.json().get("results", [])
        if results:
            return self._parse_bill(results[0])
        return None

    def get_legislators(
        self,
        state: str,
        chamber: Optional[str] = None,
        party: Optional[str] = None,
        current: bool = True,
        limit: int = 200,
    ) -> Generator[StateLegislator, None, None]:
        """Get legislators for a state.

        Args:
            state: Two-letter state code
            chamber: "upper" or "lower"
            party: Party filter (e.g., "Democratic", "Republican")
            current: Only current legislators
            limit: Maximum results
        """
        params = {
            "jurisdiction": f"ocd-jurisdiction/country:us/state:{state.lower()}/government",
            "per_page": min(limit, 100),
        }

        if chamber:
            params["org_classification"] = chamber
        if party:
            params["party"] = party

        page = 1
        total_fetched = 0

        while total_fetched < limit:
            params["page"] = page
            response = self._client.get("/people", params=params)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if not results:
                break

            for person_data in results:
                if total_fetched >= limit:
                    break
                yield self._parse_legislator(person_data)
                total_fetched += 1

            pagination = data.get("pagination", {})
            if page >= pagination.get("max_page", 1):
                break

            page += 1

    def get_legislator(self, legislator_id: str) -> Optional[StateLegislator]:
        """Get a specific legislator by ID."""
        response = self._client.get(f"/people/{legislator_id}")

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return self._parse_legislator(response.json())

    def _parse_bill(self, data: dict) -> StateBill:
        """Parse bill data from API response."""
        # Extract state from jurisdiction
        jurisdiction = data.get("jurisdiction", {})
        state = jurisdiction.get("name", "").split()[0].lower() if jurisdiction else ""

        # Get latest action
        actions = data.get("actions", [])
        latest_action = actions[-1] if actions else None

        return StateBill(
            id=data.get("id", ""),
            identifier=data.get("identifier", ""),
            title=data.get("title", ""),
            state=state,
            session=data.get("session", ""),
            chamber=data.get("from_organization", {}).get("classification", ""),
            classification=data.get("classification", []),
            subject=data.get("subject", []),
            abstracts=data.get("abstracts", []),
            sponsors=data.get("sponsorships", []),
            actions=actions,
            votes=data.get("votes", []),
            versions=data.get("versions", []),
            sources=data.get("sources", []),
            created_at=self._parse_datetime(data.get("created_at")),
            updated_at=self._parse_datetime(data.get("updated_at")),
            first_action_date=self._parse_date(data.get("first_action_date")),
            latest_action_date=self._parse_date(latest_action.get("date") if latest_action else None),
            latest_action_description=latest_action.get("description") if latest_action else None,
        )

    def _parse_legislator(self, data: dict) -> StateLegislator:
        """Parse legislator data from API response."""
        # Get current role
        roles = data.get("current_role", {}) or {}
        jurisdiction = data.get("jurisdiction", {})
        state = jurisdiction.get("name", "").split()[0].lower() if jurisdiction else ""

        return StateLegislator(
            id=data.get("id", ""),
            name=data.get("name", ""),
            state=state,
            chamber=roles.get("org_classification", ""),
            party=data.get("party", [{}])[0].get("name", "") if data.get("party") else "",
            district=roles.get("district", ""),
            image=data.get("image"),
            email=data.get("email"),
            current_role=roles,
            offices=data.get("offices", []),
        )

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string."""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
