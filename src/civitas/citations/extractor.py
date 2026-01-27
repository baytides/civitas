"""Citation extraction using eyecite (Free Law Project).

Credits: eyecite by Free Law Project (BSD-2-Clause)
https://github.com/freelawproject/eyecite

Supports extracting:
- Full case citations (e.g., "410 U.S. 113")
- Short case citations (e.g., "Roe, 410 U.S. at 153")
- Supra citations (e.g., "Smith, supra")
- Id. citations (e.g., "Id. at 156")
- Statutory citations (e.g., "42 U.S.C. § 1983")
"""

from dataclasses import dataclass
from importlib.util import find_spec


@dataclass
class ExtractedCitation:
    """A citation extracted from text."""

    raw_text: str
    citation_type: str  # "full", "short", "supra", "id", "statute"

    # Case citation fields
    reporter: str | None = None
    volume: int | None = None
    page: int | None = None
    year: int | None = None
    court: str | None = None

    # Position in source text
    span: tuple[int, int] | None = None

    # Normalized citation string
    normalized: str | None = None


class CitationExtractor:
    """Extract legal citations from text using eyecite.

    Credits: eyecite by Free Law Project (BSD-2-Clause)
    https://github.com/freelawproject/eyecite

    Example usage:
        >>> extractor = CitationExtractor()
        >>> citations = extractor.extract_citations(
        ...     "The Court in Roe v. Wade, 410 U.S. 113 (1973), held..."
        ... )
        >>> citations[0].reporter
        'U.S.'
        >>> citations[0].volume
        410
    """

    def __init__(self):
        """Initialize the citation extractor."""
        self._eyecite_available = None

    def _check_eyecite(self):
        """Check if eyecite is available."""
        if self._eyecite_available is None:
            self._eyecite_available = find_spec("eyecite") is not None
        return self._eyecite_available

    def extract_citations(self, text: str) -> list[ExtractedCitation]:
        """Extract all citations from text.

        Args:
            text: Legal text to extract citations from

        Returns:
            List of ExtractedCitation objects
        """
        if not self._check_eyecite():
            raise ImportError(
                "eyecite not installed. Install with: pip install eyecite"
            )

        from eyecite import get_citations
        from eyecite.models import (
            FullCaseCitation,
            IdCitation,
            ShortCaseCitation,
            SupraCitation,
        )

        citations = get_citations(text)
        results = []

        for cite in citations:
            if isinstance(cite, FullCaseCitation):
                results.append(ExtractedCitation(
                    raw_text=str(cite),
                    citation_type="full",
                    reporter=cite.groups.get("reporter"),
                    volume=self._safe_int(cite.groups.get("volume")),
                    page=self._safe_int(cite.groups.get("page")),
                    year=self._safe_int(cite.groups.get("year")),
                    court=cite.metadata.court if cite.metadata else None,
                    span=cite.span(),
                    normalized=cite.corrected_citation(),
                ))
            elif isinstance(cite, ShortCaseCitation):
                results.append(ExtractedCitation(
                    raw_text=str(cite),
                    citation_type="short",
                    reporter=cite.groups.get("reporter"),
                    volume=self._safe_int(cite.groups.get("volume")),
                    page=self._safe_int(cite.groups.get("page")),
                    span=cite.span(),
                ))
            elif isinstance(cite, SupraCitation):
                results.append(ExtractedCitation(
                    raw_text=str(cite),
                    citation_type="supra",
                    span=cite.span(),
                ))
            elif isinstance(cite, IdCitation):
                results.append(ExtractedCitation(
                    raw_text=str(cite),
                    citation_type="id",
                    span=cite.span(),
                ))

        return results

    def extract_case_citations(self, text: str) -> list[ExtractedCitation]:
        """Extract only full case citations from text.

        Args:
            text: Legal text to extract citations from

        Returns:
            List of full case citations only
        """
        all_cites = self.extract_citations(text)
        return [c for c in all_cites if c.citation_type == "full"]

    def extract_statutory_citations(self, text: str) -> list[ExtractedCitation]:
        """Extract statutory citations (U.S.C., state codes) from text.

        Note: eyecite primarily handles case citations. For comprehensive
        statutory citation extraction, additional patterns may be needed.

        Args:
            text: Legal text to extract citations from

        Returns:
            List of statutory citations
        """
        import re

        # Common statutory citation patterns
        patterns = [
            # U.S. Code: "42 U.S.C. § 1983" or "42 USC 1983"
            r"(\d+)\s*U\.?S\.?C\.?\s*[§]?\s*(\d+[a-z]*(?:\([a-z0-9]+\))*)",
            # Code of Federal Regulations: "29 C.F.R. § 1910.134"
            r"(\d+)\s*C\.?F\.?R\.?\s*[§]?\s*([\d.]+)",
            # Federal Register: "88 Fed. Reg. 12345"
            r"(\d+)\s*Fed\.?\s*Reg\.?\s*(\d+)",
        ]

        results = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                results.append(ExtractedCitation(
                    raw_text=match.group(0),
                    citation_type="statute",
                    span=(match.start(), match.end()),
                ))

        return results

    def annotate_text(self, text: str, tag: str = "cite") -> str:
        """Annotate text with citation markup.

        Args:
            text: Legal text to annotate
            tag: HTML/XML tag to wrap citations with

        Returns:
            Text with citations wrapped in tags

        Example:
            >>> extractor.annotate_text("See 410 U.S. 113.")
            'See <cite>410 U.S. 113</cite>.'
        """
        if not self._check_eyecite():
            raise ImportError("eyecite not installed")

        from eyecite import annotate_citations, get_citations

        citations = get_citations(text)
        annotations = [[c.span(), f"<{tag}>", f"</{tag}>"] for c in citations]
        return annotate_citations(text, annotations)

    def resolve_citations(
        self,
        citations: list[ExtractedCitation],
        court_cases: list,
    ) -> list[tuple[ExtractedCitation, object | None]]:
        """Attempt to resolve citations to database records.

        Args:
            citations: List of extracted citations
            court_cases: List of CourtCase objects from database

        Returns:
            List of (citation, matched_case) tuples
        """
        results = []

        # Build lookup by reporter/volume/page
        lookup = {}
        for case in court_cases:
            if case.citation:
                lookup[case.citation.lower()] = case

        for cite in citations:
            matched = None
            if cite.normalized:
                matched = lookup.get(cite.normalized.lower())
            if not matched and cite.raw_text:
                matched = lookup.get(cite.raw_text.lower())
            results.append((cite, matched))

        return results

    def _safe_int(self, value) -> int | None:
        """Safely convert a value to int."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def get_citation_network(self, text: str) -> dict:
        """Analyze the citation network in a document.

        Args:
            text: Legal text to analyze

        Returns:
            Dictionary with citation statistics and relationships
        """
        citations = self.extract_citations(text)

        return {
            "total_citations": len(citations),
            "full_citations": len([c for c in citations if c.citation_type == "full"]),
            "short_citations": len([c for c in citations if c.citation_type == "short"]),
            "id_citations": len([c for c in citations if c.citation_type == "id"]),
            "supra_citations": len([c for c in citations if c.citation_type == "supra"]),
            "unique_reporters": list(set(
                c.reporter for c in citations if c.reporter
            )),
            "citations": citations,
        }
