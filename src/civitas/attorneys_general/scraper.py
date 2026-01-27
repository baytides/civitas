"""Scraper for State AG litigation data.

Data Source: https://attorneysgeneral.org/
Maintained by Dr. Paul Nolette, Marquette University

This scraper collects:
- Multi-state lawsuits vs. federal government
- AG amicus briefs (Supreme Court and lower courts)
- Corporate settlements and enforcement actions
- Letters and formal comments
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Generator
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


@dataclass
class AGLawsuit:
    """A multi-state lawsuit filed by state attorneys general."""

    id: str
    title: str
    case_name: str | None = None
    court: str | None = None
    filing_date: date | None = None
    states_involved: list[str] = field(default_factory=list)
    lead_state: str | None = None
    target: str | None = None  # e.g., "Federal Government", "Corporation"
    case_type: str | None = None  # e.g., "Environmental", "Consumer Protection"
    status: str | None = None
    description: str | None = None
    docket_number: str | None = None
    source_url: str | None = None


@dataclass
class AGAmicusBrief:
    """An amicus brief filed by state attorneys general."""

    id: str
    case_name: str
    court: str
    filing_date: date | None = None
    states_involved: list[str] = field(default_factory=list)
    position: str | None = None  # What position the AGs took
    description: str | None = None
    source_url: str | None = None


class AGLitigationScraper:
    """Scraper for attorneysgeneral.org databases.

    Example:
        >>> scraper = AGLitigationScraper()
        >>> for lawsuit in scraper.get_federal_lawsuits():
        ...     print(f"{lawsuit.title}: {len(lawsuit.states_involved)} states")
    """

    BASE_URL = "https://attorneysgeneral.org"

    # Known database URLs from the site (corrected paths)
    DATABASES = {
        "federal_lawsuits": "/multistate-lawsuits-vs-the-federal-government/list-of-lawsuits-1980-present/",
        "scotus_amicus": "/amicus-briefs-u-s-supreme-court/multistate-amicus-briefs/",
        "lower_court_amicus": "/amicus-briefs-lower-courts-2/amicus-briefs-lower-courts/",
        "settlements": "/settlements-and-enforcement-actions/searchable-list-of-settlements-1980-present/",
        "letters": "/letters-and-formal-comments/searchable-list-of-multistate-letters-and-formal-comments-2017-present/",
        "ag_info": "/ag-office-information/information-on-current-ags/",
    }

    # State name to code mapping
    STATE_CODES = {
        "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
        "California": "CA", "Colorado": "CO", "Connecticut": "CT",
        "Delaware": "DE", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
        "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
        "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME",
        "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI",
        "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
        "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
        "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
        "New York": "NY", "North Carolina": "NC", "North Dakota": "ND",
        "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
        "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
        "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
        "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
        "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
        "Puerto Rico": "PR", "Guam": "GU", "Virgin Islands": "VI",
        "American Samoa": "AS", "Northern Mariana Islands": "MP",
    }

    def __init__(self, timeout: float = 30.0):
        """Initialize the scraper.

        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout
        self._client: httpx.Client | None = None

    def __enter__(self) -> "AGLitigationScraper":
        self._client = httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Civitas/1.0 (civic research; contact@projectcivitas.com)"
            },
        )
        return self

    def __exit__(self, *args) -> None:
        if self._client:
            self._client.close()

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            raise RuntimeError("Use AGLitigationScraper as context manager")
        return self._client

    def _get_page(self, path: str) -> BeautifulSoup:
        """Fetch and parse a page."""
        url = urljoin(self.BASE_URL, path)
        response = self.client.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def _parse_states(self, text: str) -> list[str]:
        """Extract state codes from a text listing states."""
        states = []
        for state_name, code in self.STATE_CODES.items():
            if state_name.lower() in text.lower():
                states.append(code)
        return sorted(set(states))

    def _parse_date(self, text: str) -> date | None:
        """Parse date from various formats."""
        if not text:
            return None
        text = text.strip()

        # Try various date formats
        formats = [
            "%B %d, %Y",  # January 15, 2025
            "%b %d, %Y",  # Jan 15, 2025
            "%m/%d/%Y",   # 01/15/2025
            "%Y-%m-%d",   # 2025-01-15
        ]

        for fmt in formats:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue

        return None

    def get_federal_lawsuits(self) -> Generator[AGLawsuit, None, None]:
        """Scrape multi-state lawsuits against the federal government.

        Yields:
            AGLawsuit objects for each lawsuit found.
        """
        soup = self._get_page(self.DATABASES["federal_lawsuits"])

        # The site uses various table/list formats
        # Try to find lawsuit entries
        entries = soup.find_all("article") or soup.find_all("div", class_=re.compile(r"lawsuit|case|entry"))

        if not entries:
            # Fall back to table rows
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")[1:]  # Skip header
                for i, row in enumerate(rows):
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        yield AGLawsuit(
                            id=f"fed-lawsuit-{i}",
                            title=cells[0].get_text(strip=True),
                            states_involved=self._parse_states(
                                cells[1].get_text() if len(cells) > 1 else ""
                            ),
                            filing_date=self._parse_date(
                                cells[2].get_text() if len(cells) > 2 else ""
                            ),
                            source_url=urljoin(
                                self.BASE_URL, self.DATABASES["federal_lawsuits"]
                            ),
                        )
        else:
            for i, entry in enumerate(entries):
                title_elem = entry.find(["h2", "h3", "h4", "a"])
                title = title_elem.get_text(strip=True) if title_elem else f"Case {i}"

                # Extract states from entry text
                text = entry.get_text()
                states = self._parse_states(text)

                yield AGLawsuit(
                    id=f"fed-lawsuit-{i}",
                    title=title,
                    states_involved=states,
                    description=entry.get_text(strip=True)[:500],
                    source_url=urljoin(
                        self.BASE_URL, self.DATABASES["federal_lawsuits"]
                    ),
                )

    def get_scotus_amicus(self) -> Generator[AGAmicusBrief, None, None]:
        """Scrape SCOTUS amicus briefs filed by state AGs.

        Yields:
            AGAmicusBrief objects.
        """
        soup = self._get_page(self.DATABASES["scotus_amicus"])

        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")[1:]
            for i, row in enumerate(rows):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    yield AGAmicusBrief(
                        id=f"scotus-amicus-{i}",
                        case_name=cells[0].get_text(strip=True),
                        court="U.S. Supreme Court",
                        states_involved=self._parse_states(
                            cells[1].get_text() if len(cells) > 1 else ""
                        ),
                        filing_date=self._parse_date(
                            cells[2].get_text() if len(cells) > 2 else ""
                        ),
                        source_url=urljoin(
                            self.BASE_URL, self.DATABASES["scotus_amicus"]
                        ),
                    )

    def get_current_ags(self) -> dict[str, dict]:
        """Get current state attorneys general info.

        Returns:
            Dictionary mapping state codes to AG information.
        """
        soup = self._get_page(self.DATABASES["ag_info"])

        ags = {}
        entries = soup.find_all("div", class_=re.compile(r"ag|attorney"))

        for entry in entries:
            name_elem = entry.find(["h2", "h3", "h4", "strong"])
            if name_elem:
                name = name_elem.get_text(strip=True)
                # Try to find state
                text = entry.get_text()
                for state_name, code in self.STATE_CODES.items():
                    if state_name in text:
                        ags[code] = {
                            "name": name,
                            "state": state_name,
                            "state_code": code,
                        }
                        break

        return ags

    def save_all(self, output_dir: Path | str) -> dict[str, int]:
        """Save all scraped data to JSON files.

        Args:
            output_dir: Directory to save data.

        Returns:
            Dictionary with counts of items saved.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        counts = {}
        errors = []

        # Federal lawsuits
        try:
            lawsuits = list(self.get_federal_lawsuits())
            counts["federal_lawsuits"] = len(lawsuits)
            with open(output_dir / "federal_lawsuits.json", "w") as f:
                json.dump(
                    [
                        {
                            "id": l.id,
                            "title": l.title,
                            "states": l.states_involved,
                            "filing_date": l.filing_date.isoformat() if l.filing_date else None,
                            "description": l.description,
                        }
                        for l in lawsuits
                    ],
                    f,
                    indent=2,
                )
        except Exception as e:
            errors.append(f"Federal lawsuits: {e}")
            counts["federal_lawsuits"] = 0

        # SCOTUS amicus
        try:
            briefs = list(self.get_scotus_amicus())
            counts["scotus_amicus"] = len(briefs)
            with open(output_dir / "scotus_amicus.json", "w") as f:
                json.dump(
                    [
                        {
                            "id": b.id,
                            "case_name": b.case_name,
                            "court": b.court,
                            "states": b.states_involved,
                            "filing_date": b.filing_date.isoformat() if b.filing_date else None,
                        }
                        for b in briefs
                    ],
                    f,
                    indent=2,
                )
        except Exception as e:
            errors.append(f"SCOTUS amicus: {e}")
            counts["scotus_amicus"] = 0

        # Current AGs
        try:
            ags = self.get_current_ags()
            counts["attorneys_general"] = len(ags)
            with open(output_dir / "current_ags.json", "w") as f:
                json.dump(ags, f, indent=2)
        except Exception as e:
            errors.append(f"Current AGs: {e}")
            counts["attorneys_general"] = 0

        if errors:
            counts["errors"] = errors

        return counts
