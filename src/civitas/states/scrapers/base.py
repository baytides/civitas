"""Base classes for state legislature scrapers.

Provides a common interface for scraping bills, legislators, and votes
from any state legislature website.
"""

from abc import ABC, abstractmethod
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()


@dataclass
class ScrapedBill:
    """A bill scraped from a state legislature website."""

    identifier: str  # e.g., "AB 123", "SB 456"
    title: str
    session: str
    chamber: str  # "upper" or "lower"
    state: str  # Two-letter state code

    # Optional fields
    bill_type: str = "bill"  # bill, resolution, constitutional_amendment
    summary: str | None = None
    subjects: list[str] = field(default_factory=list)
    sponsors: list[dict] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    votes: list[dict] = field(default_factory=list)
    versions: list[dict] = field(default_factory=list)  # Text versions
    source_url: str | None = None

    # Dates
    introduced_date: date | None = None
    last_action_date: date | None = None

    # Status
    is_enacted: bool = False
    status: str | None = None  # Latest status text


@dataclass
class ScrapedLegislator:
    """A legislator scraped from a state legislature website."""

    name: str
    chamber: str  # "upper" or "lower"
    district: str
    state: str  # Two-letter state code

    # Optional fields
    party: str | None = None
    email: str | None = None
    phone: str | None = None
    photo_url: str | None = None
    capitol_office: str | None = None
    district_office: str | None = None
    source_url: str | None = None


@dataclass
class ScrapedVote:
    """A vote record scraped from a state legislature website."""

    bill_identifier: str
    motion: str
    date: date
    chamber: str
    result: str  # "pass" or "fail"

    # Vote counts
    yes_count: int = 0
    no_count: int = 0
    abstain_count: int = 0
    absent_count: int = 0

    # Individual votes (optional)
    yes_votes: list[str] = field(default_factory=list)
    no_votes: list[str] = field(default_factory=list)
    abstain_votes: list[str] = field(default_factory=list)
    absent_votes: list[str] = field(default_factory=list)

    source_url: str | None = None


class StateScraper(ABC):
    """Base class for state legislature scrapers.

    Subclass this to create scrapers for specific states.

    Example:
        class CaliforniaScraper(StateScraper):
            STATE = "ca"
            BASE_URL = "https://leginfo.legislature.ca.gov"

            def get_bills(self, session):
                # Implement scraping logic
                pass
    """

    # Override in subclasses
    STATE: str = ""  # Two-letter state code
    STATE_NAME: str = ""  # Full state name
    BASE_URL: str = ""  # Legislature website base URL

    # Rate limiting
    REQUESTS_PER_MINUTE: int = 30

    def __init__(self, timeout: float = 30.0):
        """Initialize the scraper.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._client: httpx.Client | None = None
        self._last_request_time: float = 0

    def __enter__(self):
        self._client = httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Civitas/1.0 (civic data project; https://projectcivitas.com)",
            },
        )
        return self

    def __exit__(self, *args):
        if self._client:
            self._client.close()

    @property
    def client(self) -> httpx.Client:
        """Get HTTP client, ensuring we're in a context manager."""
        if self._client is None:
            raise RuntimeError("Use scraper as context manager: with Scraper() as s:")
        return self._client

    def _rate_limit(self):
        """Apply rate limiting between requests."""
        import time

        min_interval = 60.0 / self.REQUESTS_PER_MINUTE
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    def get(self, url: str, **kwargs) -> httpx.Response:
        """Make a rate-limited GET request."""
        self._rate_limit()
        return self.client.get(url, **kwargs)

    def get_soup(self, url: str, **kwargs) -> BeautifulSoup:
        """Fetch URL and return BeautifulSoup object."""
        response = self.get(url, **kwargs)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def get_json(self, url: str, **kwargs) -> Any:
        """Fetch URL and return JSON."""
        response = self.get(url, **kwargs)
        response.raise_for_status()
        return response.json()

    @abstractmethod
    def get_sessions(self) -> list[str]:
        """Get list of available legislative sessions.

        Returns:
            List of session identifiers (e.g., ["2023-2024", "2021-2022"])
        """
        pass

    @abstractmethod
    def get_bills(
        self,
        session: str,
        chamber: str | None = None,
        limit: int | None = None,
    ) -> Generator[ScrapedBill, None, None]:
        """Scrape bills for a session.

        Args:
            session: Session identifier
            chamber: Optional chamber filter ("upper" or "lower")
            limit: Maximum number of bills to return

        Yields:
            ScrapedBill objects
        """
        pass

    @abstractmethod
    def get_bill(self, session: str, identifier: str) -> ScrapedBill | None:
        """Get a specific bill by identifier.

        Args:
            session: Session identifier
            identifier: Bill identifier (e.g., "AB 123")

        Returns:
            ScrapedBill or None if not found
        """
        pass

    def get_legislators(
        self,
        chamber: str | None = None,
    ) -> Generator[ScrapedLegislator, None, None]:
        """Scrape current legislators.

        Args:
            chamber: Optional chamber filter

        Yields:
            ScrapedLegislator objects
        """
        raise NotImplementedError("Legislator scraping not implemented for this state")

    def get_votes(
        self,
        session: str,
        bill_identifier: str | None = None,
    ) -> Generator[ScrapedVote, None, None]:
        """Scrape vote records.

        Args:
            session: Session identifier
            bill_identifier: Optional bill filter

        Yields:
            ScrapedVote objects
        """
        raise NotImplementedError("Vote scraping not implemented for this state")

    def _parse_date(self, date_str: str, formats: list[str] | None = None) -> date | None:
        """Parse date string with multiple format attempts.

        Args:
            date_str: Date string to parse
            formats: List of strptime formats to try

        Returns:
            Parsed date or None
        """
        if not date_str:
            return None

        date_str = date_str.strip()
        formats = formats or [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m/%d/%y",
            "%B %d, %Y",
            "%b %d, %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None
