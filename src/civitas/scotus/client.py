"""Client for Supreme Court opinions with Azure storage.

Scrapes slip opinions from supremecourt.gov and stores them in Azure.

Credits: Inspired by Free Law Project's court scraping infrastructure.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

import httpx
from bs4 import BeautifulSoup

from .models import SCOTUSListingItem, SCOTUSOpinion


class SCOTUSClient:
    """Client for scraping Supreme Court slip opinions.

    Fetches opinions from supremecourt.gov, extracts text using
    pdfplumber, and optionally stores in Azure Blob Storage.

    Example:
        >>> client = SCOTUSClient()
        >>> for opinion in client.get_opinions_for_term("24"):
        ...     print(f"{opinion.case_name}: {opinion.holding[:100]}...")
    """

    BASE_URL = "https://www.supremecourt.gov"
    OPINIONS_URL = f"{BASE_URL}/opinions/slipopinion"

    def __init__(
        self,
        data_dir: Path | str = "data/scotus",
        azure_client=None,
    ):
        """Initialize SCOTUS client.

        Args:
            data_dir: Local directory for caching PDFs
            azure_client: Optional AzureStorageClient for cloud storage
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.azure = azure_client
        self._client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "Civitas/1.0 (civic data project)"},
        )

    def list_terms(self) -> list[str]:
        """List available terms.

        Terms are numbered by the last two digits of the starting year.
        E.g., "24" = October 2024 term.

        Returns:
            List of term identifiers, most recent first
        """
        # Terms go back to ~2010 on the website
        current_year = datetime.now().year
        start_term = current_year - 2000  # e.g., 2024 -> 24

        return [str(i) for i in range(start_term, 9, -1)]

    def list_opinions(self, term: str) -> list[SCOTUSListingItem]:
        """List all opinions for a term.

        Args:
            term: Term identifier (e.g., "24" for October 2024)

        Returns:
            List of SCOTUSListingItem objects
        """
        url = f"{self.OPINIONS_URL}/{term}"
        response = self._client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        opinions = []

        # Find the opinions table
        table = soup.find("table", class_="table")
        if not table:
            return []

        for row in table.find_all("tr")[1:]:  # Skip header
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            date_str = cells[0].get_text(strip=True)
            docket = cells[1].get_text(strip=True)
            case_name = cells[2].get_text(strip=True)
            pdf_link = cells[3].find("a")

            if not pdf_link:
                continue

            try:
                decision_date = datetime.strptime(date_str, "%m/%d/%y").date()
            except ValueError:
                continue

            pdf_href = pdf_link.get("href", "")
            if not pdf_href.startswith("http"):
                pdf_href = self.BASE_URL + pdf_href

            opinions.append(SCOTUSListingItem(
                case_name=case_name,
                docket_number=docket,
                decision_date=decision_date,
                pdf_url=pdf_href,
                term=term,
            ))

        return opinions

    def download_opinion(
        self,
        opinion: SCOTUSListingItem,
    ) -> tuple[Path, Optional[str]]:
        """Download opinion PDF.

        Args:
            opinion: Opinion listing item

        Returns:
            Tuple of (local_path, azure_url)
        """
        # Create filename from docket number
        safe_docket = opinion.docket_number.replace(" ", "_").replace("/", "-")
        filename = f"{opinion.term}_{safe_docket}.pdf"
        filepath = self.data_dir / filename

        # Download if not cached
        if not filepath.exists():
            response = self._client.get(opinion.pdf_url)
            response.raise_for_status()
            filepath.write_bytes(response.content)

        # Upload to Azure if configured
        azure_url = None
        if self.azure:
            with open(filepath, "rb") as f:
                azure_url = self.azure.upload_document(
                    f,
                    "opinion",
                    "scotus",
                    f"{opinion.term}_{safe_docket}",
                    "pdf",
                )

        return filepath, azure_url

    def get_opinions_for_term(
        self,
        term: str,
    ) -> Generator[SCOTUSOpinion, None, None]:
        """Fetch and parse all opinions for a term.

        Args:
            term: Term identifier

        Yields:
            SCOTUSOpinion objects with parsed content
        """
        for item in self.list_opinions(term):
            try:
                pdf_path, azure_url = self.download_opinion(item)
                opinion = self._parse_opinion_pdf(pdf_path, item, azure_url)
                if opinion:
                    yield opinion
            except Exception as e:
                # Log error but continue with other opinions
                print(f"Error processing {item.docket_number}: {e}")
                continue

    def _parse_opinion_pdf(
        self,
        pdf_path: Path,
        item: SCOTUSListingItem,
        azure_url: Optional[str],
    ) -> Optional[SCOTUSOpinion]:
        """Parse a SCOTUS opinion PDF.

        Args:
            pdf_path: Path to PDF file
            item: Opinion listing item
            azure_url: Azure URL if uploaded

        Returns:
            Parsed SCOTUSOpinion or None if parsing fails
        """
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber not installed. pip install pdfplumber")

        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        full_text = "\n".join(text_parts)

        if not full_text.strip():
            return None

        # Extract citation (e.g., "598 U.S. 651")
        citation = self._extract_citation(full_text, item)

        # Extract holding from syllabus
        holding = self._extract_holding(full_text)

        # Extract syllabus
        syllabus = self._extract_syllabus(full_text)

        return SCOTUSOpinion(
            citation=citation,
            case_name=item.case_name,
            docket_number=item.docket_number,
            decision_date=item.decision_date,
            term=item.term,
            holding=holding,
            syllabus=syllabus,
            majority_opinion=full_text,  # Store full text for now
            pdf_url=item.pdf_url,
            azure_url=azure_url,
        )

    def _extract_citation(self, text: str, item: SCOTUSListingItem) -> str:
        """Extract official citation from opinion text."""
        # Look for U.S. Reports citation
        citation_match = re.search(
            r"(\d+)\s+U\.?\s*S\.?\s+(\d+)",
            text[:2000],
        )

        if citation_match:
            return f"{citation_match.group(1)} U.S. {citation_match.group(2)}"

        # Fall back to slip opinion citation
        return f"slip-{item.term}-{item.docket_number}"

    def _extract_holding(self, text: str) -> Optional[str]:
        """Extract the holding from the syllabus."""
        # Look for "Held:" section
        held_match = re.search(
            r"Held:?\s*(.+?)(?:(?:JUSTICE|Chief Justice|The judgment|Reversed|Affirmed))",
            text,
            re.DOTALL | re.IGNORECASE,
        )

        if held_match:
            holding = held_match.group(1).strip()
            # Limit length
            if len(holding) > 2000:
                holding = holding[:2000] + "..."
            return holding

        return None

    def _extract_syllabus(self, text: str) -> Optional[str]:
        """Extract the syllabus section."""
        # Syllabus typically appears before the opinion
        syllabus_match = re.search(
            r"Syllabus\s*\n(.+?)(?:Opinion of|OPINION OF|Justice\s+[A-Z])",
            text,
            re.DOTALL | re.IGNORECASE,
        )

        if syllabus_match:
            syllabus = syllabus_match.group(1).strip()
            if len(syllabus) > 5000:
                syllabus = syllabus[:5000] + "..."
            return syllabus

        return None

    def get_recent_opinions(
        self,
        limit: int = 20,
    ) -> Generator[SCOTUSOpinion, None, None]:
        """Get most recent opinions across recent terms.

        Args:
            limit: Maximum number of opinions to return

        Yields:
            SCOTUSOpinion objects
        """
        count = 0
        for term in self.list_terms()[:3]:  # Check last 3 terms
            for opinion in self.get_opinions_for_term(term):
                yield opinion
                count += 1
                if count >= limit:
                    return

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
