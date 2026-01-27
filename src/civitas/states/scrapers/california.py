"""California Legislature scraper.

Scrapes bills and legislators directly from:
- leginfo.legislature.ca.gov (official legislature site)
- downloads.leginfo.legislature.ca.gov (data exports)

This bypasses OpenStates API limits by scraping directly.

Credits:
- Inspired by OpenStates California scraper (GPL-3.0)
- California Legislature data is public domain
"""

import re
from collections.abc import Generator
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import ScrapedBill, ScrapedLegislator, ScrapedVote, StateScraper


class CaliforniaScraper(StateScraper):
    """Scraper for California Legislature (leginfo.legislature.ca.gov).

    California provides excellent data access through their website,
    including XML exports and structured APIs.

    Example:
        with CaliforniaScraper() as scraper:
            for bill in scraper.get_bills(session="2023"):
                print(f"{bill.identifier}: {bill.title}")
    """

    STATE = "ca"
    STATE_NAME = "California"
    BASE_URL = "https://leginfo.legislature.ca.gov"
    DOWNLOADS_URL = "https://downloads.leginfo.legislature.ca.gov"

    # Rate limit to be respectful to the server
    REQUESTS_PER_MINUTE = 30

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

    def get_sessions(self) -> list[str]:
        """Get list of available legislative sessions.

        California uses session years like "20232024" for 2023-2024.
        """
        # Scrape sessions from the legislature website
        soup = self.get_soup(f"{self.BASE_URL}/faces/home.xhtml")

        sessions = []
        # Look for session selector
        select = soup.find("select", {"id": lambda x: x and "session" in x.lower()})
        if select:
            for option in select.find_all("option"):
                value = option.get("value", "")
                if value and value.isdigit():
                    sessions.append(value)

        # Fall back to known recent sessions if scraping fails
        if not sessions:
            sessions = [
                "20252026",
                "20232024",
                "20212022",
                "20192020",
                "20172018",
            ]

        return sessions

    def get_bills(
        self,
        session: str,
        chamber: str | None = None,
        limit: int | None = None,
    ) -> Generator[ScrapedBill, None, None]:
        """Scrape bills from California Legislature.

        Args:
            session: Session identifier (e.g., "20232024" for 2023-2024)
            chamber: Optional filter ("upper" for Senate, "lower" for Assembly)
            limit: Maximum bills to return

        Yields:
            ScrapedBill objects
        """
        count = 0

        # Determine which bill types to scrape
        bill_types = []
        for prefix, (_, bill_chamber) in self.BILL_TYPES.items():
            if chamber is None or bill_chamber == chamber:
                bill_types.append(prefix)

        for bill_type in bill_types:
            if limit and count >= limit:
                break

            # Get bill list for this type
            for bill in self._scrape_bill_list(session, bill_type):
                if limit and count >= limit:
                    break

                yield bill
                count += 1

    def _scrape_bill_list(
        self,
        session: str,
        bill_type: str,
    ) -> Generator[ScrapedBill, None, None]:
        """Scrape list of bills of a specific type."""
        # California provides a JSON API for bill listing
        list_url = f"{self.BASE_URL}/faces/billSearchClient.xhtml"

        params = {
            "session_year": session,
            "bill_number": "",
            "house": "Both",
            "author": "All",
            "lawCode": "All",
            "keyword": "",
            "bill_type": bill_type,
        }

        try:
            soup = self.get_soup(list_url, params=params)

            # Find bill links in results
            bill_links = soup.find_all("a", href=re.compile(r"billNavClient"))

            for link in bill_links:
                bill_text = link.get_text(strip=True)
                # Extract bill number (e.g., "AB 123")
                match = re.search(r"([A-Z]+)\s*(\d+)", bill_text)
                if not match:
                    continue

                prefix = match.group(1)
                number = match.group(2)
                identifier = f"{prefix} {number}"

                # Get full bill details
                bill = self.get_bill(session, identifier)
                if bill:
                    yield bill

        except Exception as e:
            # Fall back to direct URL pattern
            from rich.console import Console
            Console().print(f"[yellow]Bill list error: {e}, trying direct scrape[/yellow]")
            yield from self._scrape_bills_direct(session, bill_type)

    def _scrape_bills_direct(
        self,
        session: str,
        bill_type: str,
    ) -> Generator[ScrapedBill, None, None]:
        """Fallback: scrape bills by iterating through bill numbers."""
        # Try bill numbers 1-999
        for num in range(1, 1000):
            identifier = f"{bill_type} {num}"
            bill = self.get_bill(session, identifier)
            if bill:
                yield bill
            # Stop after 10 consecutive misses (we've reached the end)
            # (This is a simple heuristic)

    def get_bill(self, session: str, identifier: str) -> ScrapedBill | None:
        """Get detailed information for a specific bill.

        Args:
            session: Session identifier
            identifier: Bill identifier (e.g., "AB 123")

        Returns:
            ScrapedBill with full details, or None if not found
        """
        # Parse identifier
        match = re.match(r"([A-Z]+)\s*(\d+)", identifier.upper())
        if not match:
            return None

        prefix = match.group(1)
        number = match.group(2)

        if prefix not in self.BILL_TYPES:
            return None

        bill_type, chamber = self.BILL_TYPES[prefix]

        # Build bill URL
        bill_url = (
            f"{self.BASE_URL}/faces/billNavClient.xhtml"
            f"?bill_id={session}0{prefix}{number}"
        )

        try:
            soup = self.get_soup(bill_url)

            # Extract title
            title_elem = soup.find("span", {"id": re.compile(r"title")})
            title = title_elem.get_text(strip=True) if title_elem else ""

            if not title:
                return None  # Bill doesn't exist

            # Extract summary/digest
            summary_elem = soup.find("div", {"id": re.compile(r"digestText|summary")})
            summary = summary_elem.get_text(strip=True) if summary_elem else None

            # Extract status
            status_elem = soup.find("span", {"id": re.compile(r"statusTitle|status")})
            status = status_elem.get_text(strip=True) if status_elem else None

            # Check if enacted
            is_enacted = False
            if status and any(x in status.lower() for x in ["chaptered", "enacted"]):
                is_enacted = True

            # Extract sponsors
            sponsors = []
            author_elem = soup.find("a", {"id": re.compile(r"author")})
            if author_elem:
                sponsors.append({
                    "name": author_elem.get_text(strip=True),
                    "type": "primary",
                })

            # Extract actions
            actions = self._parse_actions(soup)

            # Get dates from actions
            introduced_date = None
            last_action_date = None
            if actions:
                introduced_date = actions[-1].get("date")  # First action
                last_action_date = actions[0].get("date")  # Most recent

            # Extract subjects/topics
            subjects = []
            subject_elems = soup.find_all("a", {"id": re.compile(r"subject|topic")})
            for elem in subject_elems:
                text = elem.get_text(strip=True)
                if text:
                    subjects.append(text)

            return ScrapedBill(
                identifier=f"{prefix} {number}",
                title=title,
                session=session,
                chamber=chamber,
                state=self.STATE,
                bill_type=bill_type,
                summary=summary,
                subjects=subjects,
                sponsors=sponsors,
                actions=actions,
                source_url=bill_url,
                introduced_date=introduced_date,
                last_action_date=last_action_date,
                is_enacted=is_enacted,
                status=status,
            )

        except Exception:
            return None

    def _parse_actions(self, soup: BeautifulSoup) -> list[dict]:
        """Parse bill actions from the page."""
        actions = []

        # Look for action table
        action_table = soup.find("table", {"id": re.compile(r"action|history")})
        if not action_table:
            return actions

        for row in action_table.find_all("tr")[1:]:  # Skip header
            cells = row.find_all("td")
            if len(cells) >= 2:
                date_text = cells[0].get_text(strip=True)
                action_text = cells[1].get_text(strip=True)

                action_date = self._parse_date(date_text)

                actions.append({
                    "date": action_date,
                    "text": action_text,
                    "chamber": self._guess_action_chamber(action_text),
                })

        return actions

    def _guess_action_chamber(self, action_text: str) -> str | None:
        """Guess chamber from action text."""
        text_lower = action_text.lower()
        if "assembly" in text_lower:
            return "lower"
        elif "senate" in text_lower:
            return "upper"
        return None

    def get_legislators(
        self,
        chamber: str | None = None,
    ) -> Generator[ScrapedLegislator, None, None]:
        """Scrape current California legislators.

        Args:
            chamber: Optional filter ("upper" for Senate, "lower" for Assembly)

        Yields:
            ScrapedLegislator objects
        """
        if chamber is None or chamber == "lower":
            yield from self._scrape_assembly_members()
        if chamber is None or chamber == "upper":
            yield from self._scrape_senate_members()

    def _scrape_assembly_members(self) -> Generator[ScrapedLegislator, None, None]:
        """Scrape California Assembly members."""
        url = "https://www.assembly.ca.gov/assemblymembers"

        try:
            soup = self.get_soup(url)

            # Find member cards/rows
            members = soup.find_all("div", class_=re.compile(r"member"))

            for member in members:
                name_elem = member.find("a", class_=re.compile(r"name"))
                if not name_elem:
                    continue

                name = name_elem.get_text(strip=True)

                # Extract district
                district_elem = member.find("span", class_=re.compile(r"district"))
                district = ""
                if district_elem:
                    district_text = district_elem.get_text(strip=True)
                    match = re.search(r"(\d+)", district_text)
                    if match:
                        district = match.group(1)

                # Extract party
                party = None
                party_elem = member.find("span", class_=re.compile(r"party"))
                if party_elem:
                    party_text = party_elem.get_text(strip=True).lower()
                    if "democrat" in party_text:
                        party = "D"
                    elif "republican" in party_text:
                        party = "R"
                    else:
                        party = "I"

                # Extract photo
                photo_elem = member.find("img")
                photo_url = photo_elem.get("src") if photo_elem else None
                if photo_url and not photo_url.startswith("http"):
                    photo_url = urljoin(url, photo_url)

                yield ScrapedLegislator(
                    name=name,
                    chamber="lower",
                    district=district,
                    state=self.STATE,
                    party=party,
                    photo_url=photo_url,
                    source_url=url,
                )

        except Exception as e:
            from rich.console import Console
            Console().print(f"[yellow]Error scraping Assembly: {e}[/yellow]")

    def _scrape_senate_members(self) -> Generator[ScrapedLegislator, None, None]:
        """Scrape California Senate members."""
        url = "https://www.senate.ca.gov/senators"

        try:
            soup = self.get_soup(url)

            # Find member listings
            members = soup.find_all("div", class_=re.compile(r"senator|member"))

            for member in members:
                name_elem = member.find("a")
                if not name_elem:
                    continue

                name = name_elem.get_text(strip=True)
                if not name or len(name) < 3:
                    continue

                # Extract district
                district = ""
                district_elem = member.find(string=re.compile(r"District\s*\d+"))
                if district_elem:
                    match = re.search(r"District\s*(\d+)", str(district_elem))
                    if match:
                        district = match.group(1)

                # Extract party from text or class
                party = None
                text = member.get_text().lower()
                if "(d)" in text or "democrat" in text:
                    party = "D"
                elif "(r)" in text or "republican" in text:
                    party = "R"

                yield ScrapedLegislator(
                    name=name,
                    chamber="upper",
                    district=district,
                    state=self.STATE,
                    party=party,
                    source_url=url,
                )

        except Exception as e:
            from rich.console import Console
            Console().print(f"[yellow]Error scraping Senate: {e}[/yellow]")

    def get_votes(
        self,
        session: str,
        bill_identifier: str | None = None,
    ) -> Generator[ScrapedVote, None, None]:
        """Scrape vote records for California bills.

        Args:
            session: Session identifier
            bill_identifier: Optional bill filter

        Yields:
            ScrapedVote objects
        """
        # If specific bill, get votes from bill page
        if bill_identifier:
            bill = self.get_bill(session, bill_identifier)
            if bill:
                yield from self._get_bill_votes(session, bill_identifier)
        else:
            # Would need to iterate through all bills
            raise NotImplementedError(
                "Bulk vote scraping requires iterating through bills. "
                "Use bill_identifier parameter for specific bill votes."
            )

    def _get_bill_votes(
        self,
        session: str,
        identifier: str,
    ) -> Generator[ScrapedVote, None, None]:
        """Get votes for a specific bill."""
        match = re.match(r"([A-Z]+)\s*(\d+)", identifier.upper())
        if not match:
            return

        prefix = match.group(1)
        number = match.group(2)

        # Build votes URL
        votes_url = (
            f"{self.BASE_URL}/faces/billVotesClient.xhtml"
            f"?bill_id={session}0{prefix}{number}"
        )

        try:
            soup = self.get_soup(votes_url)

            # Find vote tables
            vote_tables = soup.find_all("table", class_=re.compile(r"vote"))

            for table in vote_tables:
                # Parse vote header
                header = table.find_previous(["h3", "h4", "th"])
                if not header:
                    continue

                header_text = header.get_text(strip=True)

                # Extract date
                date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", header_text)
                vote_date = self._parse_date(date_match.group(1)) if date_match else None

                # Determine chamber
                chamber = "lower" if "assembly" in header_text.lower() else "upper"

                # Parse vote counts
                yes_count = 0
                no_count = 0
                abstain_count = 0

                counts_row = table.find("tr", class_=re.compile(r"count|total"))
                if counts_row:
                    cells = counts_row.find_all("td")
                    for cell in cells:
                        text = cell.get_text(strip=True).lower()
                        if "aye" in text or "yes" in text:
                            match = re.search(r"(\d+)", text)
                            if match:
                                yes_count = int(match.group(1))
                        elif "no" in text:
                            match = re.search(r"(\d+)", text)
                            if match:
                                no_count = int(match.group(1))

                # Determine result
                result = "pass" if yes_count > no_count else "fail"

                yield ScrapedVote(
                    bill_identifier=identifier,
                    motion=header_text,
                    date=vote_date,
                    chamber=chamber,
                    result=result,
                    yes_count=yes_count,
                    no_count=no_count,
                    abstain_count=abstain_count,
                    source_url=votes_url,
                )

        except Exception:
            pass
