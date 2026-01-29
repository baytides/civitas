"""New York State Legislature scraper.

Uses the official Open Legislation API:
https://legislation.nysenate.gov/static/docs/html/index.html

This is an API-based scraper (no web scraping required).
Get a free API key at: https://legislation.nysenate.gov/

Environment:
    NY_OPENLEG_API_KEY: API key for Open Legislation
"""

import os
from collections.abc import Generator
from datetime import date

from .base import ScrapedBill, ScrapedLegislator, ScrapedVote, StateScraper


class NewYorkScraper(StateScraper):
    """Scraper for New York State Legislature using Open Legislation API.

    The Open Legislation API provides comprehensive access to:
    - Bills and resolutions
    - Legislators (senators and assembly members)
    - Votes and roll calls
    - Calendars and agendas

    Example:
        with NewYorkScraper() as scraper:
            for bill in scraper.get_bills(session="2025", limit=100):
                print(f"{bill.identifier}: {bill.title}")
    """

    STATE = "ny"
    STATE_NAME = "New York"
    BASE_URL = "https://legislation.nysenate.gov"
    API_BASE = "https://legislation.nysenate.gov/api/3"

    # Rate limit (API allows generous usage)
    REQUESTS_PER_MINUTE = 60

    def __init__(self, api_key: str | None = None, **kwargs):
        """Initialize the New York scraper.

        Args:
            api_key: Open Legislation API key (default: from NY_OPENLEG_API_KEY env)
            **kwargs: Passed to StateScraper
        """
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("NY_OPENLEG_API_KEY")
        if not self.api_key:
            raise ValueError(
                "NY_OPENLEG_API_KEY environment variable required. "
                "Get a free key at: https://legislation.nysenate.gov/"
            )

    def _api_url(self, endpoint: str, **params) -> str:
        """Build API URL with authentication.

        Args:
            endpoint: API endpoint path
            **params: Query parameters

        Returns:
            Full URL with API key
        """
        url = f"{self.API_BASE}/{endpoint}"
        params["key"] = self.api_key
        query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        return f"{url}?{query}"

    def get_sessions(self) -> list[str]:
        """Get list of available legislative sessions.

        NY sessions are two-year periods starting on odd years.
        Returns years like "2025" for 2025-2026 session.
        """
        # NY sessions run 2 years, starting odd years
        # API has data going back to 2009
        return [str(year) for year in range(2025, 2008, -2)]

    def get_bills(
        self,
        session: str,
        chamber: str | None = None,
        limit: int | None = None,
    ) -> Generator[ScrapedBill, None, None]:
        """Get bills from New York Legislature.

        Args:
            session: Session year (e.g., "2025")
            chamber: Optional filter ("upper" for Senate, "lower" for Assembly)
            limit: Maximum bills to return

        Yields:
            ScrapedBill objects
        """
        from rich.console import Console

        console = Console()
        console.print(f"[dim]Fetching New York bills for session {session}...[/dim]")

        # Map chamber to bill prefix filter
        prefix_filter = None
        if chamber == "upper":
            prefix_filter = "S"  # Senate bills
        elif chamber == "lower":
            prefix_filter = "A"  # Assembly bills

        offset = 0
        batch_size = 100  # API max per request
        count = 0

        while True:
            # Fetch bills page
            url = self._api_url(
                f"bills/{session}",
                limit=batch_size,
                offset=offset,
            )

            try:
                data = self.get_json(url)
            except Exception as e:
                console.print(f"[yellow]Error fetching bills: {e}[/yellow]")
                break

            if not data.get("success"):
                console.print(f"[yellow]API error: {data.get('message')}[/yellow]")
                break

            bills = data.get("result", {}).get("items", [])
            if not bills:
                break

            for bill_data in bills:
                # Apply chamber filter
                bill_id = bill_data.get("basePrintNo", "")
                if prefix_filter and not bill_id.startswith(prefix_filter):
                    continue

                bill = self._parse_bill(bill_data, session)
                if bill:
                    yield bill
                    count += 1

                    if limit and count >= limit:
                        return

            # Check if more pages
            total = data.get("result", {}).get("size", 0)
            offset += batch_size
            if offset >= total:
                break

        console.print(f"[dim]Fetched {count} bills from New York[/dim]")

    def get_bill(self, session: str, identifier: str) -> ScrapedBill | None:
        """Get a specific bill by identifier.

        Args:
            session: Session year
            identifier: Bill identifier (e.g., "S1234", "A5678")

        Returns:
            ScrapedBill or None if not found
        """
        # Clean identifier
        bill_id = identifier.upper().replace(" ", "")

        url = self._api_url(f"bills/{session}/{bill_id}")

        try:
            data = self.get_json(url)
        except Exception:
            return None

        if not data.get("success"):
            return None

        bill_data = data.get("result")
        if not bill_data:
            return None

        return self._parse_bill(bill_data, session, fetch_full_text=True)

    def _parse_bill(
        self,
        data: dict,
        session: str,
        fetch_full_text: bool = False,
    ) -> ScrapedBill | None:
        """Parse API bill data into ScrapedBill.

        Args:
            data: Bill data from API
            session: Session year
            fetch_full_text: Whether to fetch full bill text

        Returns:
            ScrapedBill or None
        """
        bill_id = data.get("basePrintNo", "")
        if not bill_id:
            return None

        # Determine chamber from bill prefix
        chamber = "upper" if bill_id.startswith("S") else "lower"

        # Determine bill type
        bill_type = "bill"
        if any(x in bill_id for x in ["R", "J", "K"]):
            bill_type = "resolution"

        # Get title and summary
        title = data.get("title", "")
        summary = data.get("summary", "")

        # Parse dates
        introduced_date = None
        last_action_date = None

        published = data.get("publishedDateTime")
        if published:
            introduced_date = self._parse_api_date(published)

        status_info = data.get("status", {})
        status_date = status_info.get("statusDate")
        if status_date:
            last_action_date = self._parse_api_date(status_date)

        # Get status
        status = status_info.get("statusDesc", "")
        is_enacted = "SIGNED_BY_GOV" in status.upper() or "CHAPTERED" in status.upper()

        # Parse sponsors
        sponsors = []
        sponsor_data = data.get("sponsor", {})
        if sponsor_data:
            member = sponsor_data.get("member", {})
            sponsors.append({
                "name": member.get("fullName", ""),
                "type": "primary",
                "chamber": chamber,
            })

        # Parse actions from milestones
        actions = []
        milestones = data.get("milestones", {}).get("items", [])
        for milestone in milestones:
            action_date = self._parse_api_date(milestone.get("date"))
            actions.append({
                "date": action_date.isoformat() if action_date else None,
                "action": milestone.get("statusDesc", ""),
                "chamber": milestone.get("chamber", "").lower(),
            })

        # Get subjects
        subjects = []
        program_info = data.get("programInfo", {})
        if program_info:
            subjects = [program_info.get("name", "")]

        # Build source URL
        source_url = f"{self.BASE_URL}/legislation/bills/{session}/{bill_id}"

        # Fetch full text if requested
        full_text = None
        if fetch_full_text:
            full_text = self._fetch_bill_text(session, bill_id)

        return ScrapedBill(
            identifier=bill_id,
            title=title[:500] if title else bill_id,
            session=session,
            chamber=chamber,
            state=self.STATE,
            bill_type=bill_type,
            summary=summary,
            full_text=full_text,
            subjects=subjects,
            sponsors=sponsors,
            actions=actions,
            source_url=source_url,
            introduced_date=introduced_date,
            last_action_date=last_action_date,
            is_enacted=is_enacted,
            status=status,
        )

    def _fetch_bill_text(self, session: str, bill_id: str) -> str | None:
        """Fetch full text of a bill.

        Args:
            session: Session year
            bill_id: Bill identifier

        Returns:
            Bill text or None
        """
        url = self._api_url(f"bills/{session}/{bill_id}/fullText")

        try:
            data = self.get_json(url)
            if data.get("success"):
                return data.get("result", {}).get("text")
        except Exception:
            pass

        return None

    def _parse_api_date(self, date_str: str | None) -> date | None:
        """Parse date from API format.

        Args:
            date_str: Date string (ISO format or similar)

        Returns:
            Parsed date or None
        """
        if not date_str:
            return None

        # Try ISO format first
        try:
            from datetime import datetime

            # Handle various formats
            for fmt in [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d",
            ]:
                try:
                    return datetime.strptime(date_str[:len(fmt.replace("%", "0"))], fmt).date()
                except ValueError:
                    continue
        except Exception:
            pass

        return self._parse_date(date_str)

    def get_legislators(
        self,
        chamber: str | None = None,
    ) -> Generator[ScrapedLegislator, None, None]:
        """Get current New York legislators.

        Args:
            chamber: Optional filter ("upper" for Senate, "lower" for Assembly)

        Yields:
            ScrapedLegislator objects
        """
        # Fetch senators
        if chamber is None or chamber == "upper":
            url = self._api_url("members/2025/senate")
            try:
                data = self.get_json(url)
                if data.get("success"):
                    for member in data.get("result", {}).get("items", []):
                        yield self._parse_legislator(member, "upper")
            except Exception:
                pass

        # Fetch assembly members
        if chamber is None or chamber == "lower":
            url = self._api_url("members/2025/assembly")
            try:
                data = self.get_json(url)
                if data.get("success"):
                    for member in data.get("result", {}).get("items", []):
                        yield self._parse_legislator(member, "lower")
            except Exception:
                pass

    def _parse_legislator(self, data: dict, chamber: str) -> ScrapedLegislator:
        """Parse API member data into ScrapedLegislator.

        Args:
            data: Member data from API
            chamber: Chamber ("upper" or "lower")

        Returns:
            ScrapedLegislator
        """
        return ScrapedLegislator(
            name=data.get("fullName", ""),
            chamber=chamber,
            district=str(data.get("districtCode", "")),
            state=self.STATE,
            party=data.get("partyCode", ""),
            email=data.get("email"),
            source_url=f"{self.BASE_URL}/legislation/members/{data.get('memberId', '')}",
        )

    def get_votes(
        self,
        session: str,
        bill_identifier: str | None = None,
    ) -> Generator[ScrapedVote, None, None]:
        """Get vote records.

        Args:
            session: Session year
            bill_identifier: Optional bill filter

        Yields:
            ScrapedVote objects
        """
        if bill_identifier:
            # Get votes for specific bill
            bill_id = bill_identifier.upper().replace(" ", "")
            url = self._api_url(f"bills/{session}/{bill_id}/votes")

            try:
                data = self.get_json(url)
                if data.get("success"):
                    for vote_data in data.get("result", {}).get("items", []):
                        yield self._parse_vote(vote_data, bill_id)
            except Exception:
                pass
        else:
            # Getting all votes requires iterating bills
            # This is expensive, so we skip for now
            raise NotImplementedError(
                "Getting all votes requires iterating bills. "
                "Use bill_identifier parameter or iterate bills yourself."
            )

    def _parse_vote(self, data: dict, bill_id: str) -> ScrapedVote:
        """Parse API vote data into ScrapedVote.

        Args:
            data: Vote data from API
            bill_id: Bill identifier

        Returns:
            ScrapedVote
        """
        vote_date = self._parse_api_date(data.get("voteDate"))

        # Parse vote counts
        member_votes = data.get("memberVotes", {}).get("items", {})
        yes_votes = [m.get("fullName", "") for m in member_votes.get("AYE", [])]
        no_votes = [m.get("fullName", "") for m in member_votes.get("NAY", [])]
        abstain_votes = [m.get("fullName", "") for m in member_votes.get("ABSTAIN", [])]
        absent_votes = [m.get("fullName", "") for m in member_votes.get("ABSENT", [])]

        # Determine result
        result = "pass" if len(yes_votes) > len(no_votes) else "fail"

        return ScrapedVote(
            bill_identifier=bill_id,
            motion=data.get("description", ""),
            date=vote_date,
            chamber=data.get("committee", {}).get("chamber", "").lower() or "upper",
            result=result,
            yes_count=len(yes_votes),
            no_count=len(no_votes),
            abstain_count=len(abstain_votes),
            absent_count=len(absent_votes),
            yes_votes=yes_votes,
            no_votes=no_votes,
            abstain_votes=abstain_votes,
            absent_votes=absent_votes,
        )
