"""Historical SCOTUS data scraper using Court Listener API.

Fetches comprehensive Supreme Court case data from 1789-present using
the Court Listener API (Free Law Project).

This provides much richer historical data than supremecourt.gov's
slip opinions (which only go back to ~2010).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from civitas.courts.client import CourtListenerClient
from civitas.db.models import CourtCase, Justice, JusticeOpinion


@dataclass
class ScrapingStats:
    """Statistics for a scraping run."""

    cases_fetched: int = 0
    cases_inserted: int = 0
    cases_updated: int = 0
    opinions_linked: int = 0
    errors: int = 0
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class HistoricalSCOTUSScraper:
    """Scrapes historical SCOTUS data from Court Listener.

    Court Listener has comprehensive SCOTUS data going back to 1789,
    with proper author attribution, opinion types, and vote counts.

    Example:
        >>> from civitas.db.models import get_engine
        >>> from sqlalchemy.orm import Session
        >>> engine = get_engine("civitas.db")
        >>> with Session(engine) as session:
        ...     scraper = HistoricalSCOTUSScraper(session)
        ...     stats = scraper.scrape_year_range(1950, 2025)
        ...     print(f"Fetched {stats.cases_fetched} cases")
    """

    # Common last name variations for justice matching
    JUSTICE_NAME_ALIASES = {
        "jr.": "",
        "jr": "",
        "sr.": "",
        "sr": "",
        "iii": "",
        "ii": "",
    }

    def __init__(
        self,
        session: Session,
        api_token: str | None = None,
        rate_limit_delay: float = 0.5,
        verbose: bool = True,
    ):
        """Initialize the historical scraper.

        Args:
            session: SQLAlchemy session for database operations
            api_token: Optional Court Listener API token for higher rate limits
            rate_limit_delay: Seconds to wait between API calls
            verbose: Print progress updates
        """
        self.session = session
        self.client = CourtListenerClient(api_token=api_token)
        self.rate_limit_delay = rate_limit_delay
        self.verbose = verbose

        # Cache justice data for linking
        self._justice_cache: dict[str, int] = {}
        self._load_justice_cache()

    def _load_justice_cache(self) -> None:
        """Load justice last names to IDs for efficient linking."""
        justices = self.session.query(Justice).all()
        for justice in justices:
            # Store by last name (lowercase)
            self._justice_cache[justice.last_name.lower()] = justice.id
            # Also store by full name
            self._justice_cache[justice.name.lower()] = justice.id

    def _normalize_author_name(self, name: str | None) -> str | None:
        """Normalize justice name for matching."""
        if not name:
            return None

        # Convert to lowercase
        name = name.lower().strip()

        # Remove common suffixes
        for suffix, replacement in self.JUSTICE_NAME_ALIASES.items():
            name = name.replace(suffix, replacement)

        # Clean up whitespace
        name = " ".join(name.split())

        return name

    def _extract_last_name(self, full_name: str | None) -> str | None:
        """Extract last name from a full justice name."""
        if not full_name:
            return None

        normalized = self._normalize_author_name(full_name)
        if not normalized:
            return None

        # Split and take last word (usually last name)
        parts = normalized.split()
        if parts:
            return parts[-1]
        return None

    def _find_justice_id(self, author_name: str | None) -> int | None:
        """Find justice ID from author name."""
        if not author_name:
            return None

        # Try full name first
        normalized = self._normalize_author_name(author_name)
        if normalized and normalized in self._justice_cache:
            return self._justice_cache[normalized]

        # Try last name
        last_name = self._extract_last_name(author_name)
        if last_name and last_name in self._justice_cache:
            return self._justice_cache[last_name]

        return None

    def _parse_vote_count(self, case_name: str) -> tuple[int | None, int | None]:
        """Try to extract vote count from case name or return None."""
        # Court Listener sometimes includes vote in case name like "(5-4)"
        match = re.search(r"\((\d+)-(\d+)\)", case_name)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None, None

    def _extract_authors_from_text(self, text: str | None) -> dict[str, list[str]]:
        """Extract author names from opinion text."""
        if not text:
            return {"majority": [], "dissent": [], "concurrence": []}

        authors: dict[str, list[str]] = {
            "majority": [],
            "dissent": [],
            "concurrence": [],
        }

        # Patterns for different opinion types
        majority_patterns = [
            r"(?:CHIEF\s+)?JUSTICE\s+([A-Z][A-Z'\.\-]+)\s+delivered\s+the\s+opinion",
            r"Opinion\s+of\s+(?:the\s+)?(?:CHIEF\s+)?JUSTICE\s+([A-Z][A-Z'\.\-]+)",
        ]
        dissent_patterns = [
            r"(?:CHIEF\s+)?JUSTICE\s+([A-Z][A-Z'\.\-]+)\s+(?:filed\s+a\s+)?dissent",
            r"([A-Z][A-Z'\.\-]+),\s+J\.,\s+dissenting",
        ]
        concurrence_patterns = [
            r"(?:CHIEF\s+)?JUSTICE\s+([A-Z][A-Z'\.\-]+)\s+(?:filed\s+a\s+)?concur",
            r"([A-Z][A-Z'\.\-]+),\s+J\.,\s+concurring",
        ]

        for pattern in majority_patterns:
            for match in re.finditer(pattern, text[:5000], re.IGNORECASE):
                name = match.group(1).title()
                if name not in authors["majority"]:
                    authors["majority"].append(name)

        for pattern in dissent_patterns:
            for match in re.finditer(pattern, text[:10000], re.IGNORECASE):
                name = match.group(1).title()
                if name not in authors["dissent"]:
                    authors["dissent"].append(name)

        for pattern in concurrence_patterns:
            for match in re.finditer(pattern, text[:10000], re.IGNORECASE):
                name = match.group(1).title()
                if name not in authors["concurrence"]:
                    authors["concurrence"].append(name)

        return authors

    def scrape_date_range(
        self,
        start_date: date,
        end_date: date,
        batch_size: int = 100,
    ) -> ScrapingStats:
        """Scrape SCOTUS cases within a date range.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            batch_size: Number of cases to fetch per API call

        Returns:
            ScrapingStats with counts
        """
        stats = ScrapingStats(start_time=datetime.now(UTC))

        if self.verbose:
            print(f"Scraping SCOTUS cases from {start_date} to {end_date}...")

        try:
            for opinion in self.client.get_opinions(
                court="scotus",
                filed_after=start_date,
                filed_before=end_date,
                limit=None,  # Get all
                page_size=batch_size,
            ):
                stats.cases_fetched += 1

                try:
                    result = self._process_opinion(opinion)
                    if result == "inserted":
                        stats.cases_inserted += 1
                    elif result == "updated":
                        stats.cases_updated += 1

                    # Commit periodically
                    if stats.cases_fetched % 100 == 0:
                        self.session.commit()
                        if self.verbose:
                            print(
                                f"  Progress: {stats.cases_fetched} fetched, "
                                f"{stats.cases_inserted} inserted, "
                                f"{stats.cases_updated} updated"
                            )

                except Exception as e:
                    stats.errors += 1
                    if self.verbose:
                        print(f"  Error processing {opinion.case_name}: {e}")
                    continue

                # Rate limiting
                time.sleep(self.rate_limit_delay)

            # Final commit
            self.session.commit()

        except Exception as e:
            if self.verbose:
                print(f"Scraping error: {e}")
            stats.errors += 1

        stats.end_time = datetime.now(UTC)

        if self.verbose:
            print(
                f"\nCompleted: {stats.cases_fetched} fetched, "
                f"{stats.cases_inserted} inserted, "
                f"{stats.cases_updated} updated, "
                f"{stats.errors} errors "
                f"({stats.duration_seconds:.1f}s)"
            )

        return stats

    def scrape_year_range(
        self,
        start_year: int,
        end_year: int,
        batch_size: int = 100,
    ) -> ScrapingStats:
        """Scrape SCOTUS cases for a range of years.

        Args:
            start_year: Starting year (e.g., 1789)
            end_year: Ending year (e.g., 2025)
            batch_size: Number of cases to fetch per API call

        Returns:
            Combined ScrapingStats for all years
        """
        total_stats = ScrapingStats(start_time=datetime.now(UTC))

        for year in range(start_year, end_year + 1):
            if self.verbose:
                print(f"\n--- Year {year} ---")

            year_start = date(year, 1, 1)
            year_end = date(year, 12, 31)

            # Don't go past today
            if year_end > date.today():
                year_end = date.today()

            year_stats = self.scrape_date_range(
                start_date=year_start,
                end_date=year_end,
                batch_size=batch_size,
            )

            total_stats.cases_fetched += year_stats.cases_fetched
            total_stats.cases_inserted += year_stats.cases_inserted
            total_stats.cases_updated += year_stats.cases_updated
            total_stats.errors += year_stats.errors

        total_stats.end_time = datetime.now(UTC)
        return total_stats

    def scrape_recent(self, days: int = 365, batch_size: int = 100) -> ScrapingStats:
        """Scrape recent SCOTUS cases.

        Args:
            days: Number of days to look back
            batch_size: Number of cases to fetch per API call

        Returns:
            ScrapingStats
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        return self.scrape_date_range(start_date, end_date, batch_size)

    def scrape_all_historical(self, batch_size: int = 100) -> ScrapingStats:
        """Scrape all historical SCOTUS cases from 1789 to present.

        This is a long-running operation. Consider running in batches
        or as a background job.

        Args:
            batch_size: Number of cases to fetch per API call

        Returns:
            ScrapingStats for entire run
        """
        return self.scrape_year_range(1789, date.today().year, batch_size)

    def _process_opinion(self, opinion) -> str:
        """Process a single opinion from Court Listener.

        Args:
            opinion: CourtListenerOpinion object

        Returns:
            "inserted", "updated", or "skipped"
        """
        # Check if case already exists by citation or case_id
        existing = None
        if opinion.citation:
            existing = (
                self.session.query(CourtCase)
                .filter(
                    CourtCase.court == "scotus",
                    CourtCase.citation == opinion.citation,
                )
                .first()
            )

        if not existing and opinion.id:
            existing = (
                self.session.query(CourtCase)
                .filter(
                    CourtCase.court == "scotus",
                    CourtCase.source_id == f"cl-{opinion.id}",
                )
                .first()
            )

        # Extract authors from text if available
        authors = self._extract_authors_from_text(opinion.plain_text)

        # Primary author from Court Listener metadata or extracted
        majority_author = opinion.author
        if not majority_author and authors["majority"]:
            majority_author = authors["majority"][0]

        # Parse vote count if embedded in case name
        vote_maj, vote_dis = self._parse_vote_count(opinion.case_name)

        # Clean case name (remove vote count if present)
        case_name = re.sub(r"\s*\(\d+-\d+\)\s*$", "", opinion.case_name)

        if existing:
            # Update existing record with richer data
            updated = False

            if not existing.majority_author and majority_author:
                existing.majority_author = majority_author
                updated = True

            if opinion.plain_text and (
                not existing.majority_opinion
                or len(opinion.plain_text) > len(existing.majority_opinion or "")
            ):
                existing.majority_opinion = opinion.plain_text
                updated = True

            if vote_maj and not existing.vote_majority:
                existing.vote_majority = vote_maj
                existing.vote_dissent = vote_dis
                updated = True

            if updated:
                existing.updated_at = datetime.now(UTC)
                # Link opinions to justices
                self._link_opinions_to_case(
                    existing.id, majority_author, authors, opinion.opinion_type
                )
                return "updated"

            return "skipped"

        # Create new case
        court_case = CourtCase(
            citation=opinion.citation or f"cl-{opinion.id}",
            case_name=case_name,
            docket_number=None,  # Court Listener doesn't always have this
            court_level="scotus",
            court="scotus",
            court_name="Supreme Court of the United States",
            decision_date=opinion.date_created,
            vote_majority=vote_maj,
            vote_dissent=vote_dis,
            majority_author=majority_author,
            majority_opinion=opinion.plain_text,
            source_url=(
                f"https://www.courtlistener.com{opinion.absolute_url}"
                if opinion.absolute_url
                else None
            ),
            source_id=f"cl-{opinion.id}",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        self.session.add(court_case)
        self.session.flush()  # Get the ID

        # Link opinions to justices
        self._link_opinions_to_case(court_case.id, majority_author, authors, opinion.opinion_type)

        return "inserted"

    def _link_opinions_to_case(
        self,
        case_id: int,
        majority_author: str | None,
        authors: dict[str, list[str]],
        opinion_type: str,
    ) -> int:
        """Create JusticeOpinion records linking justices to case.

        Returns:
            Number of opinion links created
        """
        linked = 0

        # Link majority author
        if majority_author:
            justice_id = self._find_justice_id(majority_author)
            if self._create_opinion_link(case_id, justice_id, majority_author, "majority"):
                linked += 1

        # Link dissenting justices
        for author in authors.get("dissent", []):
            justice_id = self._find_justice_id(author)
            if self._create_opinion_link(case_id, justice_id, author, "dissent"):
                linked += 1

        # Link concurring justices
        for author in authors.get("concurrence", []):
            justice_id = self._find_justice_id(author)
            if self._create_opinion_link(case_id, justice_id, author, "concurrence"):
                linked += 1

        return linked

    def _create_opinion_link(
        self,
        case_id: int,
        justice_id: int | None,
        author_name: str,
        opinion_type: str,
    ) -> bool:
        """Create a JusticeOpinion link if it doesn't exist.

        Returns:
            True if created, False if already exists
        """
        # Check for existing link
        existing = (
            self.session.query(JusticeOpinion)
            .filter(
                JusticeOpinion.court_case_id == case_id,
                JusticeOpinion.author_name == author_name,
                JusticeOpinion.opinion_type == opinion_type,
            )
            .first()
        )

        if existing:
            # Update justice_id if we now have it
            if not existing.justice_id and justice_id:
                existing.justice_id = justice_id
            return False

        # Create new link
        opinion = JusticeOpinion(
            court_case_id=case_id,
            justice_id=justice_id,
            author_name=author_name,
            opinion_type=opinion_type,
            created_at=datetime.now(UTC),
        )
        self.session.add(opinion)
        return True

    def link_unlinked_opinions(self) -> int:
        """Link existing JusticeOpinion records to Justice records.

        Call this after adding new justices to update historical links.

        Returns:
            Number of opinions linked
        """
        # Reload cache in case new justices were added
        self._load_justice_cache()

        unlinked = (
            self.session.query(JusticeOpinion).filter(JusticeOpinion.justice_id.is_(None)).all()
        )

        linked = 0
        for opinion in unlinked:
            justice_id = self._find_justice_id(opinion.author_name)
            if justice_id:
                opinion.justice_id = justice_id
                linked += 1

        if linked:
            self.session.commit()

        if self.verbose:
            print(f"Linked {linked} of {len(unlinked)} unlinked opinions")

        return linked

    def get_stats(self) -> dict:
        """Get current database statistics for SCOTUS data.

        Returns:
            Dict with counts
        """
        total_cases = (
            self.session.query(CourtCase).filter(CourtCase.court_level == "scotus").count()
        )

        with_author = (
            self.session.query(CourtCase)
            .filter(
                CourtCase.court_level == "scotus",
                CourtCase.majority_author.isnot(None),
            )
            .count()
        )

        total_opinions = self.session.query(JusticeOpinion).count()
        linked_opinions = (
            self.session.query(JusticeOpinion).filter(JusticeOpinion.justice_id.isnot(None)).count()
        )

        # Date range
        oldest = (
            self.session.query(CourtCase)
            .filter(
                CourtCase.court_level == "scotus",
                CourtCase.decision_date.isnot(None),
            )
            .order_by(CourtCase.decision_date.asc())
            .first()
        )

        newest = (
            self.session.query(CourtCase)
            .filter(
                CourtCase.court_level == "scotus",
                CourtCase.decision_date.isnot(None),
            )
            .order_by(CourtCase.decision_date.desc())
            .first()
        )

        return {
            "total_scotus_cases": total_cases,
            "cases_with_author": with_author,
            "total_justice_opinions": total_opinions,
            "linked_justice_opinions": linked_opinions,
            "oldest_case_date": oldest.decision_date if oldest else None,
            "newest_case_date": newest.decision_date if newest else None,
        }

    def close(self):
        """Close the Court Listener client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
