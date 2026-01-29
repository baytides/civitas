"""Client for Supreme Court opinions with Azure storage.

Scrapes slip opinions from supremecourt.gov and stores them in Azure.

Credits: Inspired by Free Law Project's court scraping infrastructure.
"""

import re
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from .models import SCOTUSListingItem, SCOTUSOpinion, SCOTUSTranscript


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
    ORDERS_URL = f"{BASE_URL}/opinions/relatingtoorders"

    # Available terms on supremecourt.gov (back to 2010)
    AVAILABLE_TERMS = [str(i) for i in range(25, 9, -1)]  # 25 down to 10

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

        # Find the opinions table (layout varies)
        table = soup.find("table", class_="table") or soup.find("table")
        if not table:
            return []

        date_pattern = re.compile(r"\d{1,2}/\d{1,2}/\d{2}")

        for row in table.find_all("tr")[1:]:  # Skip header
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            # Determine date/docket columns dynamically
            date_idx = None
            for i, cell in enumerate(cells):
                if date_pattern.search(cell.get_text(strip=True)):
                    date_idx = i
                    break
            if date_idx is None or date_idx + 1 >= len(cells):
                continue

            date_str = cells[date_idx].get_text(strip=True)
            docket = cells[date_idx + 1].get_text(strip=True)

            pdf_link = None
            case_name = None
            for cell in cells:
                link = cell.find("a")
                if link and link.get("href", "").endswith(".pdf"):
                    pdf_link = link
                    case_name = link.get_text(strip=True)
                    break

            if not pdf_link:
                continue

            try:
                decision_date = datetime.strptime(date_str, "%m/%d/%y").date()
            except ValueError:
                continue

            pdf_href = pdf_link.get("href", "")
            if not pdf_href.startswith("http"):
                pdf_href = self.BASE_URL + pdf_href

            opinions.append(
                SCOTUSListingItem(
                    case_name=case_name,
                    docket_number=docket,
                    decision_date=decision_date,
                    pdf_url=pdf_href,
                    term=term,
                )
            )

        return opinions

    def list_orders_opinions(self, term: str) -> list[SCOTUSListingItem]:
        """List opinions relating to orders for a term.

        Args:
            term: Term identifier (e.g., "24" for October 2024)

        Returns:
            List of SCOTUSListingItem objects
        """
        url = f"{self.ORDERS_URL}/{term}"
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except Exception:
            return []  # Some terms may not have orders opinions

        soup = BeautifulSoup(response.text, "lxml")
        opinions = []

        table = soup.find("table", class_="table") or soup.find("table")
        if not table:
            return []

        date_pattern = re.compile(r"\d{1,2}/\d{1,2}/\d{2}")

        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            date_idx = None
            for i, cell in enumerate(cells):
                if date_pattern.search(cell.get_text(strip=True)):
                    date_idx = i
                    break
            if date_idx is None or date_idx + 1 >= len(cells):
                continue

            date_str = cells[date_idx].get_text(strip=True)
            docket = cells[date_idx + 1].get_text(strip=True)

            pdf_link = None
            case_name = None
            for cell in cells:
                link = cell.find("a")
                if link and link.get("href", "").endswith(".pdf"):
                    pdf_link = link
                    case_name = link.get_text(strip=True)
                    break

            if not pdf_link:
                continue

            try:
                decision_date = datetime.strptime(date_str, "%m/%d/%y").date()
            except ValueError:
                continue

            pdf_href = pdf_link.get("href", "")
            if not pdf_href.startswith("http"):
                pdf_href = self.BASE_URL + pdf_href

            opinions.append(
                SCOTUSListingItem(
                    case_name=case_name,
                    docket_number=docket,
                    decision_date=decision_date,
                    pdf_url=pdf_href,
                    term=term,
                    opinion_type="order",
                )
            )

        return opinions

    def download_opinion(
        self,
        opinion: SCOTUSListingItem,
    ) -> tuple[Path, str | None]:
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
        azure_url: str | None,
    ) -> SCOTUSOpinion | None:
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

        authors = self._extract_authors(full_text)

        return SCOTUSOpinion(
            citation=citation,
            case_name=item.case_name,
            docket_number=item.docket_number,
            decision_date=item.decision_date,
            term=item.term,
            holding=holding,
            syllabus=syllabus,
            majority_opinion=full_text,  # Store full text for now
            majority_author=authors.get("majority_author"),
            majority_authors=authors.get("majority_authors", []),
            dissent_authors=authors.get("dissent_authors", []),
            concurrence_authors=authors.get("concurrence_authors", []),
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

    def _extract_holding(self, text: str) -> str | None:
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

    def _extract_syllabus(self, text: str) -> str | None:
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

    def _extract_authors(self, text: str) -> dict:
        """Extract opinion author names from text."""
        authors: dict[str, list[str] | str | None] = {
            "majority_authors": [],
            "dissent_authors": [],
            "concurrence_authors": [],
            "majority_author": None,
        }

        majority_patterns = [
            r"(CHIEF JUSTICE|JUSTICE)\s+([A-Z][A-Z'\.\-]+)\s+delivered the opinion of the Court",
            r"(CHIEF JUSTICE|JUSTICE)\s+([A-Z][A-Z'\.\-]+)\s+delivered the opinion",
        ]
        dissent_patterns = [
            r"(JUSTICE|CHIEF JUSTICE)\s+([A-Z][A-Z'\.\-]+)\s+filed a dissenting opinion",
            r"(JUSTICE|CHIEF JUSTICE)\s+([A-Z][A-Z'\.\-]+)\s+dissenting",
        ]
        concurrence_patterns = [
            r"(JUSTICE|CHIEF JUSTICE)\s+([A-Z][A-Z'\.\-]+)\s+filed a concurring opinion",
            r"(JUSTICE|CHIEF JUSTICE)\s+([A-Z][A-Z'\.\-]+)\s+concurring",
        ]

        def extract_first(patterns: list[str]) -> list[str]:
            found: list[str] = []
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    found.append(match.group(2).title())
                    break
            return found

        def extract_all(patterns: list[str]) -> list[str]:
            found: list[str] = []
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    found.append(match.group(2).title())
            return list(dict.fromkeys(found))

        majority = extract_first(majority_patterns)
        dissent = extract_all(dissent_patterns)
        concurrence = extract_all(concurrence_patterns)

        authors["majority_authors"] = majority
        authors["dissent_authors"] = dissent
        authors["concurrence_authors"] = concurrence
        authors["majority_author"] = majority[0] if majority else None

        return authors

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

    # =========================================================================
    # Oral Argument Transcripts
    # =========================================================================

    TRANSCRIPTS_URL = f"{BASE_URL}/oral_arguments/argument_transcript"

    def list_transcripts(self, term: str) -> list[SCOTUSTranscript]:
        """List oral argument transcripts for a term.

        Args:
            term: Term identifier (e.g., "24" for October 2024)

        Returns:
            List of SCOTUSTranscript objects
        """
        url = f"{self.TRANSCRIPTS_URL}/{term}"
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except Exception:
            return []

        soup = BeautifulSoup(response.text, "lxml")
        transcripts = []

        # Find all case links with PDF transcripts
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if not href.endswith(".pdf"):
                continue
            if "/argument_transcript/" not in href:
                continue

            case_name = link.get_text(strip=True)
            if not case_name:
                continue

            # Extract docket number from href (e.g., "24-813_5426.pdf")
            docket_match = re.search(r"(\d+-\d+)", href)
            docket = docket_match.group(1) if docket_match else ""

            # Find argument date from nearby text
            parent = link.find_parent("tr") or link.find_parent("div")
            date_text = parent.get_text() if parent else ""
            date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{2})", date_text)

            if date_match:
                try:
                    arg_date = datetime.strptime(date_match.group(1), "%m/%d/%y").date()
                except ValueError:
                    arg_date = None
            else:
                arg_date = None

            pdf_url = href if href.startswith("http") else self.BASE_URL + href

            transcripts.append(
                SCOTUSTranscript(
                    case_name=case_name,
                    docket_number=docket,
                    argument_date=arg_date or datetime.now().date(),
                    pdf_url=pdf_url,
                    term=term,
                )
            )

        return transcripts

    def download_transcript(
        self, transcript: SCOTUSTranscript
    ) -> tuple[Path, str | None]:
        """Download a transcript PDF and extract text.

        Args:
            transcript: SCOTUSTranscript object

        Returns:
            Tuple of (local_path, azure_url)
        """
        safe_docket = transcript.docket_number.replace(" ", "_").replace("/", "-")
        filename = f"transcript_{transcript.term}_{safe_docket}.pdf"
        filepath = self.data_dir / filename

        if not filepath.exists():
            response = self._client.get(transcript.pdf_url)
            response.raise_for_status()
            filepath.write_bytes(response.content)

        # Upload to Azure if configured
        azure_url = None
        if self.azure:
            with open(filepath, "rb") as f:
                azure_url = self.azure.upload_document(
                    f,
                    "transcript",
                    "scotus",
                    f"{transcript.term}_{safe_docket}",
                    "pdf",
                )

        return filepath, azure_url

    def get_transcripts_for_term(
        self, term: str
    ) -> Generator[SCOTUSTranscript, None, None]:
        """Fetch and parse all transcripts for a term.

        Args:
            term: Term identifier

        Yields:
            SCOTUSTranscript objects with parsed content
        """

        for item in self.list_transcripts(term):
            try:
                pdf_path, azure_url = self.download_transcript(item)
                text = self._extract_transcript_text(pdf_path)

                yield SCOTUSTranscript(
                    case_name=item.case_name,
                    docket_number=item.docket_number,
                    argument_date=item.argument_date,
                    pdf_url=item.pdf_url,
                    term=term,
                    transcript_text=text,
                    azure_url=azure_url,
                )
            except Exception as e:
                print(f"Error processing transcript {item.docket_number}: {e}")
                continue

    def _extract_transcript_text(self, pdf_path: Path) -> str | None:
        """Extract text from transcript PDF."""
        try:
            import pdfplumber
        except ImportError:
            return None

        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        return "\n".join(text_parts) if text_parts else None

    # =========================================================================
    # Comprehensive Scraping
    # =========================================================================

    def get_all_opinions_for_terms(
        self,
        terms: list[str] | None = None,
        include_orders: bool = True,
    ) -> Generator[SCOTUSOpinion, None, None]:
        """Get all opinions across multiple terms.

        Args:
            terms: List of terms to scrape (defaults to all available)
            include_orders: Whether to include opinions relating to orders

        Yields:
            SCOTUSOpinion objects
        """
        terms = terms or self.AVAILABLE_TERMS

        for term in terms:
            print(f"  Scraping term {term}...")

            # Slip opinions
            for opinion in self.get_opinions_for_term(term):
                yield opinion

            # Orders opinions
            if include_orders:
                for item in self.list_orders_opinions(term):
                    try:
                        pdf_path, azure_url = self.download_opinion(item)
                        opinion = self._parse_opinion_pdf(pdf_path, item, azure_url)
                        if opinion:
                            yield opinion
                    except Exception as e:
                        print(f"Error processing order opinion {item.docket_number}: {e}")
                        continue

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
