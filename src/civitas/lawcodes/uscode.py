"""US Code client for fetching federal law.

Source: Office of the Law Revision Counsel (uscode.house.gov)
License: Public Domain

The US Code is the codification of general and permanent federal statutes.
It is divided into 54 titles organized by subject matter.
"""

import re
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

import httpx


@dataclass
class USCodeSection:
    """A section of the US Code."""

    title: int
    section: str
    heading: str
    text: str
    citations: list[str] = field(default_factory=list)
    source_notes: str | None = None
    effective_date: date | None = None


@dataclass
class USCodeTitle:
    """A title (volume) of the US Code."""

    number: int
    name: str
    is_positive_law: bool  # Positive law titles are the authoritative text
    last_updated: date | None = None
    sections: list[USCodeSection] = field(default_factory=list)


class USCodeClient:
    """Client for the US Code from House.gov.

    The US Code is available in multiple formats:
    - XML (USLM format) - structured, machine-readable
    - PDF - official print format
    - HTML - web display format

    Example:
        >>> client = USCodeClient()
        >>> # Get Title 18 (Crimes)
        >>> title = client.get_title(18)
        >>> print(f"{title.name}: {len(title.sections)} sections")
        >>> # Search for specific sections
        >>> for section in client.search("free speech"):
        ...     print(f"{section.title} USC {section.section}: {section.heading}")
    """

    # Base URLs for US Code
    BASE_URL = "https://uscode.house.gov"
    XML_URL = f"{BASE_URL}/download/download.shtml"

    # US Code titles and their names
    TITLES = {
        1: "General Provisions",
        2: "The Congress",
        3: "The President",
        4: "Flag and Seal, Seat of Government, and the States",
        5: "Government Organization and Employees",
        6: "Domestic Security",
        7: "Agriculture",
        8: "Aliens and Nationality",
        9: "Arbitration",
        10: "Armed Forces",
        11: "Bankruptcy",
        12: "Banks and Banking",
        13: "Census",
        14: "Coast Guard",
        15: "Commerce and Trade",
        16: "Conservation",
        17: "Copyrights",
        18: "Crimes and Criminal Procedure",
        19: "Customs Duties",
        20: "Education",
        21: "Food and Drugs",
        22: "Foreign Relations and Intercourse",
        23: "Highways",
        24: "Hospitals and Asylums",
        25: "Indians",
        26: "Internal Revenue Code",
        27: "Intoxicating Liquors",
        28: "Judiciary and Judicial Procedure",
        29: "Labor",
        30: "Mineral Lands and Mining",
        31: "Money and Finance",
        32: "National Guard",
        33: "Navigation and Navigable Waters",
        34: "Crime Control and Law Enforcement",
        35: "Patents",
        36: "Patriotic and National Observances",
        37: "Pay and Allowances of the Uniformed Services",
        38: "Veterans' Benefits",
        39: "Postal Service",
        40: "Public Buildings, Property, and Works",
        41: "Public Contracts",
        42: "The Public Health and Welfare",
        43: "Public Lands",
        44: "Public Printing and Documents",
        45: "Railroads",
        46: "Shipping",
        47: "Telecommunications",
        48: "Territories and Insular Possessions",
        49: "Transportation",
        50: "War and National Defense",
        51: "National and Commercial Space Programs",
        52: "Voting and Elections",
        53: "Reserved",
        54: "National Park Service and Related Programs",
    }

    # Titles enacted as positive law (authoritative text)
    POSITIVE_LAW_TITLES = {
        1,
        3,
        4,
        5,
        9,
        10,
        11,
        13,
        14,
        17,
        18,
        23,
        28,
        31,
        32,
        34,
        35,
        36,
        37,
        38,
        39,
        40,
        41,
        44,
        46,
        49,
        51,
        54,
    }

    def __init__(
        self,
        cache_dir: Path | str = "data/uscode",
        azure_client=None,
    ):
        """Initialize US Code client.

        Args:
            cache_dir: Directory for caching downloaded files
            azure_client: Optional AzureStorageClient for cloud storage
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.azure = azure_client
        self._client = httpx.Client(
            timeout=60.0,
            follow_redirects=True,
            headers={"User-Agent": "Civitas/1.0 (civic data project)"},
        )

    def list_titles(self) -> list[dict]:
        """List all US Code titles.

        Returns:
            List of title info dictionaries
        """
        return [
            {
                "number": num,
                "name": name,
                "is_positive_law": num in self.POSITIVE_LAW_TITLES,
            }
            for num, name in sorted(self.TITLES.items())
        ]

    def get_constitution(self) -> str:
        """Get the US Constitution text.

        Returns:
            Full text of the US Constitution
        """
        # The Constitution is available from the Government Publishing Office
        constitution_url = (
            "https://www.govinfo.gov/content/pkg/CDOC-110hdoc50/html/CDOC-110hdoc50.htm"
        )

        try:
            response = self._client.get(constitution_url)
            response.raise_for_status()

            # Parse HTML and extract text
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "lxml")

            # Remove script and style elements
            for element in soup(["script", "style"]):
                element.decompose()

            # Get text
            text = soup.get_text(separator="\n")

            # Clean up whitespace
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            return "\n".join(lines)

        except Exception:
            # Fallback: return basic constitution text
            return self._get_constitution_fallback()

    def _get_constitution_fallback(self) -> str:
        """Fallback Constitution text if scraping fails."""
        return """
THE CONSTITUTION OF THE UNITED STATES

PREAMBLE

We the People of the United States, in Order to form a more perfect Union,
establish Justice, insure domestic Tranquility, provide for the common defence,
promote the general Welfare, and secure the Blessings of Liberty to ourselves
and our Posterity, do ordain and establish this Constitution for the United
States of America.

[Full text available at: https://constitution.congress.gov/constitution/]
"""

    def get_title_xml_url(self, title_number: int) -> str:
        """Get the XML download URL for a title.

        Args:
            title_number: US Code title number

        Returns:
            URL to download the title XML
        """
        # Format: usc01.xml, usc02.xml, etc.
        return f"{self.BASE_URL}/download/releasePoints/us/pl/118/usc{title_number:02d}.xml"

    def download_title_xml(self, title_number: int) -> Path:
        """Download title XML and cache locally.

        Args:
            title_number: US Code title number

        Returns:
            Path to downloaded XML file
        """
        cache_file = self.cache_dir / f"usc{title_number:02d}.xml"

        if cache_file.exists():
            return cache_file

        url = self.get_title_xml_url(title_number)
        response = self._client.get(url)
        response.raise_for_status()

        cache_file.write_bytes(response.content)

        # Also store in Azure if configured
        if self.azure:
            self.azure.upload_document(
                response.content,
                "law_code",
                "uscode",
                f"title_{title_number:02d}",
                "xml",
            )

        return cache_file

    def get_title(self, title_number: int) -> USCodeTitle:
        """Get a US Code title with all sections.

        Args:
            title_number: US Code title number

        Returns:
            USCodeTitle object with parsed sections
        """
        if title_number not in self.TITLES:
            raise ValueError(f"Invalid title number: {title_number}")

        title = USCodeTitle(
            number=title_number,
            name=self.TITLES[title_number],
            is_positive_law=title_number in self.POSITIVE_LAW_TITLES,
        )

        try:
            xml_file = self.download_title_xml(title_number)
            title.sections = list(self._parse_title_xml(xml_file, title_number))
        except Exception:
            # If XML download fails, return empty sections
            pass

        return title

    def _parse_title_xml(
        self, xml_file: Path, title_number: int
    ) -> Generator[USCodeSection, None, None]:
        """Parse US Code XML file (USLM format).

        Args:
            xml_file: Path to XML file
            title_number: Title number for context

        Yields:
            USCodeSection objects
        """
        try:
            tree = ElementTree.parse(xml_file)
            root = tree.getroot()

            # USLM namespace
            ns = {"uslm": "http://xml.house.gov/schemas/uslm/1.0"}

            # Find all sections
            for section in root.findall(".//uslm:section", ns):
                identifier = section.get("identifier", "")

                # Extract section number from identifier (e.g., "/us/usc/t18/s1" -> "1")
                match = re.search(r"/s([\d\w\-]+)$", identifier)
                section_num = match.group(1) if match else identifier

                # Get heading
                heading_elem = section.find("uslm:heading", ns)
                heading = heading_elem.text if heading_elem is not None else ""

                # Get text content
                text_parts = []
                for content in section.findall(".//uslm:content", ns):
                    if content.text:
                        text_parts.append(content.text)

                yield USCodeSection(
                    title=title_number,
                    section=section_num,
                    heading=heading or "",
                    text="\n".join(text_parts),
                )

        except ElementTree.ParseError:
            # If XML parsing fails, yield nothing
            pass

    def search(
        self,
        query: str,
        titles: list[int] | None = None,
        limit: int = 50,
    ) -> list[USCodeSection]:
        """Search US Code sections by keyword.

        Args:
            query: Search query
            titles: Limit to specific titles (default: all)
            limit: Maximum results

        Returns:
            List of matching sections
        """
        results = []
        query_lower = query.lower()
        search_titles = titles or list(self.TITLES.keys())

        for title_num in search_titles:
            try:
                title = self.get_title(title_num)
                for section in title.sections:
                    if (
                        query_lower in section.heading.lower()
                        or query_lower in section.text.lower()
                    ):
                        results.append(section)
                        if len(results) >= limit:
                            return results
            except Exception:
                continue

        return results

    def get_section(self, title: int, section: str) -> USCodeSection | None:
        """Get a specific section of the US Code.

        Args:
            title: Title number
            section: Section number/identifier

        Returns:
            USCodeSection or None if not found
        """
        title_obj = self.get_title(title)
        for sec in title_obj.sections:
            if sec.section == section:
                return sec
        return None

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
