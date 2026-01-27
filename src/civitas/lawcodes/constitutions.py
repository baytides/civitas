"""State Constitution scrapers.

Sources: Official state legislature and archive websites (Public Domain)

Each state maintains its own constitution, often available through:
- State legislature websites
- State archive offices
- Law revision commissions
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import httpx

# State codes using the 'us' library
try:
    import us
    STATES = {s.abbr: s.name for s in us.states.STATES}
    STATES.update({s.abbr: s.name for s in us.states.TERRITORIES})
except ImportError:
    # Fallback if us library not installed
    STATES = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
        "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
        "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
        "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
        "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
        "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
        "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
        "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
        "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
        "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
        "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
        "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
        "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
        "PR": "Puerto Rico", "GU": "Guam", "VI": "Virgin Islands",
        "AS": "American Samoa", "MP": "Northern Mariana Islands",
    }


@dataclass
class ConstitutionArticle:
    """An article of a constitution."""

    number: int | str
    title: str
    text: str
    sections: list[dict] = field(default_factory=list)


@dataclass
class StateConstitution:
    """A state constitution."""

    state_code: str
    state_name: str
    ratification_date: date | None = None
    current_version_date: date | None = None
    preamble: str = ""
    articles: list[ConstitutionArticle] = field(default_factory=list)
    full_text: str = ""
    source_url: str | None = None
    amendments_count: int = 0


class ConstitutionClient:
    """Client for fetching state constitutions.

    Scrapes official state sources for constitution text.
    All state constitutions are public domain.

    Example:
        >>> client = ConstitutionClient()
        >>> ca_const = client.get_state_constitution("CA")
        >>> print(f"California Constitution has {len(ca_const.articles)} articles")
        >>> # Search across all states
        >>> for result in client.search("free speech", limit=10):
        ...     print(f"{result['state']}: {result['excerpt']}")
    """

    # Known URLs for state constitutions
    # These point to official government sources
    CONSTITUTION_URLS = {
        "AL": "https://alisondb.legislature.state.al.us/alison/codeofalabama/constitution/1901/toc.htm",
        "AK": "https://ltgov.alaska.gov/information/alaskas-constitution/",
        "AZ": "https://www.azleg.gov/constitution/",
        "AR": "https://www.arkleg.state.ar.us/Home/FTPDoc?path=%2FAssembly%2F2023%2F2023R%2FPublications%2FArkansas+Constitution.pdf",
        "CA": "https://leginfo.legislature.ca.gov/faces/codesTOCSelected.xhtml?tocCode=CONS",
        "CO": "https://leg.colorado.gov/colorado-constitution",
        "CT": "https://www.cga.ct.gov/asp/content/constitutions/CTConstitution.htm",
        "DE": "https://delcode.delaware.gov/constitution/index.html",
        "FL": "https://www.flsenate.gov/Laws/Constitution",
        "GA": "https://law.justia.com/constitution/georgia/",
        "HI": "https://www.capitol.hawaii.gov/hrscurrent/Vol01_Cons/",
        "ID": "https://legislature.idaho.gov/statutesrules/idconst/",
        "IL": "https://www.ilga.gov/commission/lrb/conent.htm",
        "IN": "https://www.in.gov/history/about-indiana-history-and-trivia/explore-indiana-history-by-topic/indiana-documents/constitution/",
        "IA": "https://www.legis.iowa.gov/law/constitutional",
        "KS": "https://kslib.info/405/Kansas-Constitution",
        "KY": "https://apps.legislature.ky.gov/law/constitution",
        "LA": "https://www.legis.la.gov/legis/laws_toc.aspx?folder=75",
        "ME": "https://legislature.maine.gov/ros/LawsOfMaine/constitution",
        "MD": "https://msa.maryland.gov/msa/mdmanual/43const/html/const.html",
        "MA": "https://malegislature.gov/laws/constitution",
        "MI": "https://www.legislature.mi.gov/Publications/Constitution",
        "MN": "https://www.revisor.mn.gov/constitution/",
        "MS": "https://law.justia.com/constitution/mississippi/",
        "MO": "https://revisor.mo.gov/main/OneSection.aspx?section=Const",
        "MT": "https://leg.mt.gov/content/Committees/Interim/2013-2014/State-Administration-and-Veterans-Affairs/Meetings/November-2013/Constitution.pdf",
        "NE": "https://nebraskalegislature.gov/laws/articles.php?article=constitution",
        "NV": "https://www.leg.state.nv.us/const/nvconst.html",
        "NH": "https://www.nh.gov/glance/constitution.htm",
        "NJ": "https://www.nj.gov/state/archives/docconst1947.html",
        "NM": "https://nmonesource.com/nmos/c/en/navigate",
        "NY": "https://www.dos.ny.gov/info/constitution.htm",
        "NC": "https://www.ncleg.gov/Laws/Constitution",
        "ND": "https://www.ndlegis.gov/constitution",
        "OH": "https://www.ohioconstitution.org/",
        "OK": "https://www.oscn.net/applications/oscn/Index.asp?ftdb=STOKST&level=1",
        "OR": "https://www.oregonlegislature.gov/bills_laws/Pages/OrConst.aspx",
        "PA": "https://www.legis.state.pa.us/cfdocs/legis/LI/consCheck.cfm",
        "RI": "https://www.rilin.state.ri.us/riconstitution/",
        "SC": "https://www.scstatehouse.gov/scconstitution/scconstitution.php",
        "SD": "https://sdlegislature.gov/Statutes/Constitution",
        "TN": "https://www.capitol.tn.gov/about/docs/TN-Constitution.pdf",
        "TX": "https://statutes.capitol.texas.gov/docs/cn/htm/cn.1.htm",
        "UT": "https://le.utah.gov/xcode/ArticleI/C1.html",
        "VT": "https://legislature.vermont.gov/statutes/constitution-of-the-state-of-vermont",
        "VA": "https://law.lis.virginia.gov/constitution/",
        "WA": "https://leg.wa.gov/CodeReviser/Pages/WAConstitution.aspx",
        "WV": "https://www.wvlegislature.gov/WVCODE/WV_CON.cfm",
        "WI": "https://docs.legis.wisconsin.gov/constitution",
        "WY": "https://wyoleg.gov/StateConstitution.aspx",
        "DC": "https://code.dccouncil.gov/us/dc/council/code/titles/1",
        "PR": "https://www.oslpr.org/v2/Constitucion.aspx",
    }

    def __init__(
        self,
        cache_dir: Path | str = "data/constitutions",
        azure_client=None,
    ):
        """Initialize Constitution client.

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

    def list_states(self) -> list[dict]:
        """List all states with constitution availability.

        Returns:
            List of state info dictionaries
        """
        return [
            {
                "code": code,
                "name": name,
                "has_url": code in self.CONSTITUTION_URLS,
            }
            for code, name in sorted(STATES.items())
        ]

    def get_state_constitution(self, state_code: str) -> StateConstitution:
        """Get a state constitution.

        Args:
            state_code: Two-letter state code (e.g., "CA")

        Returns:
            StateConstitution object
        """
        state_code = state_code.upper()
        if state_code not in STATES:
            raise ValueError(f"Unknown state code: {state_code}")

        constitution = StateConstitution(
            state_code=state_code,
            state_name=STATES[state_code],
            source_url=self.CONSTITUTION_URLS.get(state_code),
        )

        # Try to fetch and parse the constitution
        if state_code in self.CONSTITUTION_URLS:
            try:
                constitution = self._fetch_constitution(state_code, constitution)
            except Exception:
                # Return basic constitution object if fetch fails
                pass

        return constitution

    def _fetch_constitution(
        self, state_code: str, constitution: StateConstitution
    ) -> StateConstitution:
        """Fetch and parse a state constitution from its URL.

        Different states have different formats, so this uses
        state-specific parsing where needed.
        """
        url = self.CONSTITUTION_URLS.get(state_code)
        if not url:
            return constitution

        # Check cache first
        cache_file = self.cache_dir / f"{state_code.lower()}_constitution.txt"
        if cache_file.exists():
            constitution.full_text = cache_file.read_text()
            return constitution

        try:
            response = self._client.get(url)
            response.raise_for_status()

            # Parse based on content type
            content_type = response.headers.get("content-type", "")

            if "pdf" in content_type or url.endswith(".pdf"):
                # Handle PDF constitutions
                constitution.full_text = f"[PDF constitution available at: {url}]"
            else:
                # Parse HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "lxml")

                # Remove scripts and styles
                for elem in soup(["script", "style", "nav", "header", "footer"]):
                    elem.decompose()

                # Extract text
                text = soup.get_text(separator="\n")
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                constitution.full_text = "\n".join(lines)

            # Cache the result
            if constitution.full_text and not constitution.full_text.startswith("[PDF"):
                cache_file.write_text(constitution.full_text)

            # Store in Azure if configured
            if self.azure and constitution.full_text:
                self.azure.upload_document(
                    constitution.full_text.encode("utf-8"),
                    "constitution",
                    "state",
                    state_code.lower(),
                    "txt",
                )

        except Exception:
            pass

        return constitution

    def get_us_constitution(self) -> str:
        """Get the US Constitution text.

        Convenience method that delegates to USCodeClient.
        """
        from .uscode import USCodeClient

        with USCodeClient(cache_dir=self.cache_dir.parent / "uscode") as client:
            return client.get_constitution()

    def search(
        self,
        query: str,
        states: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Search across state constitutions.

        Args:
            query: Search query
            states: Limit to specific states (default: all)
            limit: Maximum results

        Returns:
            List of search results with state and excerpt
        """
        results = []
        query_lower = query.lower()
        search_states = states or list(STATES.keys())

        for state_code in search_states:
            try:
                const = self.get_state_constitution(state_code)
                if const.full_text and query_lower in const.full_text.lower():
                    # Find excerpt around match
                    idx = const.full_text.lower().find(query_lower)
                    start = max(0, idx - 100)
                    end = min(len(const.full_text), idx + len(query) + 100)
                    excerpt = const.full_text[start:end]

                    results.append({
                        "state_code": state_code,
                        "state_name": const.state_name,
                        "excerpt": f"...{excerpt}...",
                        "source_url": const.source_url,
                    })

                    if len(results) >= limit:
                        return results

            except Exception:
                continue

        return results

    def download_all(self, progress_callback=None) -> dict[str, bool]:
        """Download all state constitutions.

        Args:
            progress_callback: Optional callback(state_code, success)

        Returns:
            Dictionary of state_code -> success status
        """
        results = {}

        for state_code in STATES.keys():
            try:
                const = self.get_state_constitution(state_code)
                success = bool(const.full_text)
                results[state_code] = success

                if progress_callback:
                    progress_callback(state_code, success)

            except Exception:
                results[state_code] = False
                if progress_callback:
                    progress_callback(state_code, False)

        return results

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
