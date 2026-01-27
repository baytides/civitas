"""California Legislature scraper.

Uses the California Legislature's official data downloads from:
https://downloads.leginfo.legislature.ca.gov/

This is a wrapper around the existing civitas.california client that
provides a consistent scraper interface.

Note: California provides excellent structured data downloads, so we
use those instead of web scraping.

Credits:
- California Legislature data is public domain
"""

from collections.abc import Generator

from .base import ScrapedBill, ScrapedLegislator, StateScraper


class CaliforniaScraper(StateScraper):
    """Scraper for California Legislature using official data downloads.

    California provides comprehensive data downloads at:
    https://downloads.leginfo.legislature.ca.gov/

    This scraper uses those downloads rather than web scraping,
    providing more reliable and complete data.

    Example:
        with CaliforniaScraper() as scraper:
            for bill in scraper.get_bills(session="2023"):
                print(f"{bill.identifier}: {bill.title}")
    """

    STATE = "ca"
    STATE_NAME = "California"
    BASE_URL = "https://leginfo.legislature.ca.gov"
    DOWNLOADS_URL = "https://downloads.leginfo.legislature.ca.gov"

    # Rate limit (generous since we use downloads)
    REQUESTS_PER_MINUTE = 60

    # Bill type prefixes
    BILL_TYPES = {
        "AB": ("bill", "lower"),      # Assembly Bill
        "SB": ("bill", "upper"),      # Senate Bill
        "ACR": ("resolution", "lower"),  # Assembly Concurrent Resolution
        "SCR": ("resolution", "upper"),  # Senate Concurrent Resolution
        "AJR": ("resolution", "lower"),  # Assembly Joint Resolution
        "SJR": ("resolution", "upper"),  # Senate Joint Resolution
        "AR": ("resolution", "lower"),   # Assembly Resolution
        "SR": ("resolution", "upper"),   # Senate Resolution
        "ACA": ("constitutional_amendment", "lower"),
        "SCA": ("constitutional_amendment", "upper"),
    }

    def __init__(self, data_dir: str | None = None, **kwargs):
        """Initialize the California scraper.

        Args:
            data_dir: Directory to store downloaded data (default: data/california)
            **kwargs: Passed to StateScraper
        """
        super().__init__(**kwargs)
        self._data_dir = data_dir
        self._ca_client = None

    def _get_ca_client(self):
        """Get or create the California data client."""
        if self._ca_client is None:
            from pathlib import Path

            from civitas.california import CaliforniaClient

            data_dir = Path(self._data_dir) if self._data_dir else None
            self._ca_client = CaliforniaClient(data_dir=data_dir)
        return self._ca_client

    def get_sessions(self) -> list[str]:
        """Get list of available legislative sessions.

        Returns session years like "2023" for 2023-2024 session.
        """
        # California sessions run for 2 years, starting odd years
        # Available data goes back to 1989
        return [str(year) for year in range(2025, 1988, -2)]

    def get_bills(
        self,
        session: str,
        chamber: str | None = None,
        limit: int | None = None,
    ) -> Generator[ScrapedBill, None, None]:
        """Get bills from California Legislature data downloads.

        Args:
            session: Session year (e.g., "2023" for 2023-2024)
            chamber: Optional filter ("upper" for Senate, "lower" for Assembly)
            limit: Maximum bills to return

        Yields:
            ScrapedBill objects
        """
        from rich.console import Console

        console = Console()
        console.print(f"[dim]Downloading California data for session {session}...[/dim]")

        client = self._get_ca_client()
        count = 0

        try:
            # Download and parse the session data
            for bill in client.iter_bills(int(session)):
                # Apply chamber filter
                bill_type = bill.measure_type.upper() if bill.measure_type else ""
                if bill_type not in self.BILL_TYPES:
                    continue

                _, bill_chamber = self.BILL_TYPES[bill_type]
                if chamber and bill_chamber != chamber:
                    continue

                # Convert to ScrapedBill
                identifier = f"{bill_type} {bill.measure_num}"

                # Get bill version for title/subject
                title = ""
                summary = None
                subjects = []

                for version in client.iter_bill_versions(int(session)):
                    if version.bill_id == bill.bill_id:
                        title = version.subject or ""
                        break

                # Determine if enacted
                is_enacted = False
                if bill.chapter_num and bill.chapter_year:
                    is_enacted = True

                yield ScrapedBill(
                    identifier=identifier,
                    title=title[:500] if title else identifier,
                    session=session,
                    chamber=bill_chamber,
                    state=self.STATE,
                    bill_type=self.BILL_TYPES[bill_type][0],
                    summary=summary,
                    subjects=subjects,
                    source_url=f"{self.BASE_URL}/faces/billNavClient.xhtml?bill_id={session}0{bill_type}{bill.measure_num}",
                    is_enacted=is_enacted,
                    status=bill.current_status,
                )

                count += 1
                if limit and count >= limit:
                    break

        except Exception as e:
            console.print(f"[yellow]Error reading California data: {e}[/yellow]")
            console.print(
                "[dim]Tip: Use 'civitas ingest california <year>' for full ingestion[/dim]"
            )

    def get_bill(self, session: str, identifier: str) -> ScrapedBill | None:
        """Get a specific bill by identifier.

        Args:
            session: Session year
            identifier: Bill identifier (e.g., "AB 123")

        Returns:
            ScrapedBill or None if not found
        """
        # Parse identifier
        import re

        match = re.match(r"([A-Z]+)\s*(\d+)", identifier.upper())
        if not match:
            return None

        bill_type = match.group(1)
        bill_num = int(match.group(2))

        if bill_type not in self.BILL_TYPES:
            return None

        client = self._get_ca_client()

        for bill in client.iter_bills(int(session)):
            if (
                bill.measure_type
                and bill.measure_type.upper() == bill_type
                and bill.measure_num == bill_num
            ):
                # Get version for title
                title = ""
                for version in client.iter_bill_versions(int(session)):
                    if version.bill_id == bill.bill_id:
                        title = version.subject or ""
                        break

                _, bill_chamber = self.BILL_TYPES[bill_type]
                is_enacted = bool(bill.chapter_num and bill.chapter_year)

                return ScrapedBill(
                    identifier=identifier.upper(),
                    title=title[:500] if title else identifier,
                    session=session,
                    chamber=bill_chamber,
                    state=self.STATE,
                    bill_type=self.BILL_TYPES[bill_type][0],
                    source_url=f"{self.BASE_URL}/faces/billNavClient.xhtml?bill_id={session}0{bill_type}{bill_num}",
                    is_enacted=is_enacted,
                    status=bill.current_status,
                )

        return None

    def get_legislators(
        self,
        chamber: str | None = None,
    ) -> Generator[ScrapedLegislator, None, None]:
        """Get current California legislators.

        Uses the California data downloads for legislator information.
        """
        client = self._get_ca_client()

        # Get most recent session
        current_year = 2025 if 2025 % 2 == 1 else 2024

        for legislator in client.iter_legislators(current_year):
            # Determine chamber from house field
            leg_chamber = "lower" if legislator.house == "A" else "upper"

            if chamber and leg_chamber != chamber:
                continue

            # Map party
            party = None
            if legislator.party:
                party_lower = legislator.party.lower()
                if "democrat" in party_lower:
                    party = "D"
                elif "republican" in party_lower:
                    party = "R"
                else:
                    party = "I"

            yield ScrapedLegislator(
                name=legislator.name,
                chamber=leg_chamber,
                district=str(legislator.district) if legislator.district else "",
                state=self.STATE,
                party=party,
            )
