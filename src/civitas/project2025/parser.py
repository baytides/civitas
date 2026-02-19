"""Parse Project 2025 Mandate for Leadership document.

The Mandate for Leadership (~900 pages) contains policy proposals
organized by federal agency. This module extracts these proposals
for tracking against actual legislation and executive actions.

Source: https://s3.documentcloud.org/documents/24088042/project-2025s-mandate-for-leadership-the-conservative-promise.pdf
"""

import json
import os
import re
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path

# Default Ollama configuration (Bay Tides AI)
DEFAULT_OLLAMA_HOST = "https://ollama.baytides.org"
DEFAULT_OLLAMA_MODEL = "llama3.2"


@dataclass
class PolicyProposal:
    """A specific policy proposal from Project 2025."""

    # Location in document
    section: str
    chapter: str | None = None
    page_number: int = 0

    # Target agency
    agency: str = "General"

    # Content
    proposal_text: str = ""
    proposal_summary: str | None = None

    # Keywords for matching against legislation
    keywords: list[str] = field(default_factory=list)

    # Action type
    action_type: str = "unknown"  # eliminate, restructure, defund, create, modify

    # Impact categorization
    category: str = "general"  # immigration, environment, healthcare, education, etc.
    priority: str = "medium"  # high, medium, low (based on emphasis in text)
    implementation_timeline: str = "unknown"  # day_one, first_100_days, first_year, long_term

    # Constitutional implications
    constitutional_concerns: list[str] = field(default_factory=list)

    # Confidence score from AI extraction
    confidence: float = 0.0


class Project2025Parser:
    """Parser for Project 2025 Mandate for Leadership PDF.

    Extracts policy proposals organized by section/agency.

    Example:
        >>> parser = Project2025Parser("data/project2025/mandate.pdf")
        >>> for proposal in parser.extract_proposals():
        ...     print(f"{proposal.agency}: {proposal.proposal_text[:100]}...")
    """

    # Known sections and their approximate page ranges
    SECTIONS = {
        "White House Office": (1, 50),
        "Executive Office of the President": (51, 100),
        "Department of State": (169, 254),
        "Department of Defense": (95, 168),
        "Department of Homeland Security": (135, 168),
        "Department of Justice": (545, 586),
        "Department of the Interior": (521, 544),
        "Department of Agriculture": (291, 328),
        "Department of Commerce": (665, 702),
        "Department of Labor": (591, 628),
        "Department of Health and Human Services": (449, 502),
        "Department of Housing and Urban Development": (503, 520),
        "Department of Transportation": (629, 664),
        "Department of Energy": (363, 416),
        "Department of Education": (319, 362),
        "Department of Veterans Affairs": (645, 664),
        "Environmental Protection Agency": (417, 448),
        "Small Business Administration": (755, 774),
        "Office of Management and Budget": (31, 50),
        "Office of Personnel Management": (75, 94),
        "Intelligence Community": (197, 216),
        "Independent Regulatory Agencies": (829, 870),
    }

    # Agency abbreviations for matching
    AGENCY_ABBREVIATIONS = {
        "EPA": "Environmental Protection Agency",
        "DOJ": "Department of Justice",
        "DHS": "Department of Homeland Security",
        "HHS": "Department of Health and Human Services",
        "DOE": "Department of Energy",
        "DOD": "Department of Defense",
        "State": "Department of State",
        "Education": "Department of Education",
        "Labor": "Department of Labor",
        "Interior": "Department of the Interior",
        "USDA": "Department of Agriculture",
        "Commerce": "Department of Commerce",
        "HUD": "Department of Housing and Urban Development",
        "DOT": "Department of Transportation",
        "VA": "Department of Veterans Affairs",
        "OMB": "Office of Management and Budget",
        "OPM": "Office of Personnel Management",
        "SBA": "Small Business Administration",
    }

    # Action patterns to identify proposal types
    ACTION_PATTERNS = {
        "eliminate": r"\b(eliminate|abolish|defund|dismantle|end|terminate|remove)\b",
        "restructure": r"\b(restructure|reorganize|reform|overhaul|consolidate)\b",
        "reduce": r"\b(reduce|cut|limit|restrict|downsize|streamline)\b",
        "create": r"\b(create|establish|implement|introduce|launch)\b",
        "modify": r"\b(modify|change|amend|revise|update|strengthen)\b",
        "privatize": r"\b(privatize|outsource|contract|devolve)\b",
        "repeal": r"\b(repeal|rescind|reverse|revoke|overturn)\b",
    }

    def __init__(self, pdf_path: Path | str):
        """Initialize parser with PDF path.

        Args:
            pdf_path: Path to the Mandate for Leadership PDF
        """
        self.pdf_path = Path(pdf_path)

    def extract_proposals(self) -> Generator[PolicyProposal, None, None]:
        """Extract policy proposals from the document.

        Yields:
            PolicyProposal objects for each identified proposal
        """
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber required: pip install pdfplumber")

        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                section = self._identify_section(page_num)

                # Extract actionable proposals from page
                yield from self._extract_from_page(text, section, page_num)

    def _identify_section(self, page_num: int) -> str:
        """Identify which section a page belongs to."""
        for section, (start, end) in self.SECTIONS.items():
            if start <= page_num <= end:
                return section
        return "General"

    def _extract_from_page(
        self,
        text: str,
        section: str,
        page_num: int,
    ) -> Generator[PolicyProposal, None, None]:
        """Extract proposals from page text.

        Looks for imperative statements suggesting policy changes.
        """
        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)

        for sentence in sentences:
            # Skip short sentences and headers
            if len(sentence) < 50 or len(sentence) > 1000:
                continue

            # Check for action patterns
            action_type = self._detect_action_type(sentence)
            if action_type == "unknown":
                continue

            # Check for imperative language
            if not self._is_proposal(sentence):
                continue

            # Extract agency mentions
            agency = self._extract_agency(sentence, section)

            # Extract keywords
            keywords = self._extract_keywords(sentence)

            yield PolicyProposal(
                section=section,
                page_number=page_num,
                agency=agency,
                proposal_text=sentence.strip(),
                keywords=keywords,
                action_type=action_type,
            )

    def _detect_action_type(self, text: str) -> str:
        """Detect the type of action proposed."""
        text_lower = text.lower()
        for action_type, pattern in self.ACTION_PATTERNS.items():
            if re.search(pattern, text_lower):
                return action_type
        return "unknown"

    def _is_proposal(self, text: str) -> bool:
        """Check if text appears to be a policy proposal."""
        # Look for imperative patterns
        imperative_patterns = [
            r"\bshould\b",
            r"\bmust\b",
            r"\bwill\b",
            r"\bneeds? to\b",
            r"\brequire[sd]?\b",
            r"\brecommend",
            r"\bpropose[sd]?\b",
            r"the (?:next|new) (?:administration|president)",
            r"day one",
        ]

        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in imperative_patterns)

    def _extract_agency(self, text: str, default_section: str) -> str:
        """Extract mentioned agency from proposal text."""
        text_upper = text.upper()

        # Check for abbreviations
        for abbrev, full_name in self.AGENCY_ABBREVIATIONS.items():
            if abbrev in text_upper:
                return full_name

        # Check for full names
        for section_name in self.SECTIONS.keys():
            if section_name.lower() in text.lower():
                return section_name

        # Default to section
        return default_section

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords for matching against legislation."""
        # Common words to skip
        skip_words = {
            "the",
            "a",
            "an",
            "to",
            "of",
            "and",
            "or",
            "should",
            "must",
            "will",
            "would",
            "could",
            "this",
            "that",
            "these",
            "those",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "for",
            "with",
            "in",
            "on",
            "at",
            "by",
            "from",
            "up",
            "about",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "again",
            "further",
            "then",
            "once",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "all",
            "each",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "can",
            "just",
            "new",
            "next",
            "administration",
            "president",
            "federal",
            "government",
            "agency",
            "department",
        }

        # Extract significant words
        words = re.findall(r"\b[a-z]{4,}\b", text.lower())
        keywords = [w for w in words if w not in skip_words]

        # Return unique keywords, limited to 15
        return list(dict.fromkeys(keywords))[:15]

    def get_proposals_by_agency(self, agency: str) -> list[PolicyProposal]:
        """Get all proposals targeting a specific agency."""
        return [p for p in self.extract_proposals() if p.agency == agency]

    def get_proposals_by_action(self, action_type: str) -> list[PolicyProposal]:
        """Get all proposals of a specific action type."""
        return [p for p in self.extract_proposals() if p.action_type == action_type]

    def generate_summary(self) -> dict:
        """Generate summary statistics of extracted proposals."""
        proposals = list(self.extract_proposals())

        by_agency = {}
        by_action = {}

        for p in proposals:
            by_agency[p.agency] = by_agency.get(p.agency, 0) + 1
            by_action[p.action_type] = by_action.get(p.action_type, 0) + 1

        return {
            "total_proposals": len(proposals),
            "by_agency": dict(sorted(by_agency.items(), key=lambda x: -x[1])),
            "by_action_type": dict(sorted(by_action.items(), key=lambda x: -x[1])),
        }


class EnhancedProject2025Parser(Project2025Parser):
    """Enhanced parser with AI-assisted extraction and categorization.

    Uses Ollama/Llama via Bay Tides API for deeper analysis including:
    - Better proposal extraction from complex paragraphs
    - Category classification (immigration, environment, etc.)
    - Constitutional concern identification
    - Implementation timeline detection

    Example:
        >>> parser = EnhancedProject2025Parser("data/project2025/mandate.pdf")
        >>> for proposal in parser.extract_proposals_with_ai():
        ...     print(f"{proposal.agency} [{proposal.category}]: {proposal.proposal_summary}")
    """

    # Policy categories for classification
    CATEGORIES = {
        "immigration": [
            "immigration",
            "border",
            "visa",
            "asylum",
            "deportation",
            "ice",
            "cbp",
            "dhs",
        ],
        "environment": [
            "climate",
            "epa",
            "environment",
            "emission",
            "pollution",
            "energy",
            "drilling",
        ],
        "healthcare": [
            "health",
            "hhs",
            "medicare",
            "medicaid",
            "abortion",
            "reproductive",
            "fda",
        ],
        "education": ["education", "school", "student", "teacher", "title ix", "dei"],
        "civil_rights": ["civil rights", "discrimination", "voting", "lgbtq", "gender", "race"],
        "labor": ["labor", "worker", "union", "wage", "osha", "nlrb"],
        "economy": ["tax", "budget", "spending", "debt", "deficit", "tariff", "trade"],
        "defense": ["military", "defense", "pentagon", "nato", "veteran"],
        "justice": ["justice", "doj", "fbi", "crime", "prosecution", "pardon"],
        "government_structure": [
            "civil service",
            "schedule f",
            "personnel",
            "bureaucracy",
            "regulation",
        ],
    }

    # Timeline indicators
    TIMELINE_PATTERNS = {
        "day_one": [r"day one", r"first day", r"immediately", r"upon taking office"],
        "first_100_days": [r"first 100 days", r"first hundred days", r"early", r"quickly"],
        "first_year": [r"first year", r"within a year", r"by end of"],
        "long_term": [r"long.?term", r"eventually", r"over time", r"gradual"],
    }

    def __init__(
        self,
        pdf_path: Path | str,
        ollama_host: str | None = None,
        ollama_model: str | None = None,
    ):
        """Initialize enhanced parser.

        Args:
            pdf_path: Path to the Mandate for Leadership PDF
            ollama_host: Ollama server URL (default: Bay Tides AI)
            ollama_model: Model name (default: llama3.2)
        """
        super().__init__(pdf_path)
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)

    def _get_ollama_client(self):
        """Get Ollama client."""
        try:
            import ollama
        except ImportError:
            raise ImportError("Install ollama: pip install ollama")
        return ollama.Client(host=self.ollama_host)

    def extract_proposals_with_ai(
        self,
        use_ai: bool = True,
        batch_size: int = 10,
    ) -> Generator[PolicyProposal, None, None]:
        """Extract proposals with AI-enhanced analysis.

        Args:
            use_ai: Whether to use AI for deeper analysis
            batch_size: Number of proposals to batch for AI analysis

        Yields:
            Enhanced PolicyProposal objects
        """
        # First pass: basic extraction
        batch = []
        for proposal in self.extract_proposals():
            # Add basic category detection
            proposal.category = self._detect_category(proposal.proposal_text)
            proposal.implementation_timeline = self._detect_timeline(proposal.proposal_text)
            proposal.priority = self._detect_priority(proposal.proposal_text, proposal.action_type)

            if use_ai:
                batch.append(proposal)
                if len(batch) >= batch_size:
                    # AI-enhance the batch
                    yield from self._ai_enhance_batch(batch)
                    batch = []
            else:
                yield proposal

        # Process remaining batch
        if batch:
            if use_ai:
                yield from self._ai_enhance_batch(batch)
            else:
                yield from batch

    def _detect_category(self, text: str) -> str:
        """Detect policy category from text."""
        text_lower = text.lower()
        scores = {}

        for category, keywords in self.CATEGORIES.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score

        if scores:
            return max(scores, key=scores.get)
        return "general"

    def _detect_timeline(self, text: str) -> str:
        """Detect implementation timeline from text."""
        text_lower = text.lower()

        for timeline, patterns in self.TIMELINE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return timeline

        return "unknown"

    def _detect_priority(self, text: str, action_type: str) -> str:
        """Detect priority level from text and action type."""
        text_lower = text.lower()

        # High priority indicators
        high_indicators = [
            "immediately",
            "urgent",
            "critical",
            "essential",
            "must",
            "day one",
            "first priority",
            "top priority",
            "eliminate",
        ]

        # Low priority indicators
        low_indicators = [
            "consider",
            "explore",
            "may",
            "could",
            "eventually",
            "long.?term",
        ]

        high_score = sum(1 for ind in high_indicators if ind in text_lower)
        low_score = sum(1 for ind in low_indicators if re.search(ind, text_lower))

        # Action type boost
        if action_type in ["eliminate", "repeal", "defund"]:
            high_score += 1

        if high_score > low_score + 1:
            return "high"
        elif low_score > high_score:
            return "low"
        return "medium"

    def _ai_enhance_batch(self, proposals: list[PolicyProposal]) -> list[PolicyProposal]:
        """Use AI to enhance a batch of proposals."""
        client = self._get_ollama_client()

        # Prepare proposals for AI
        proposal_texts = [f"[{i}] {p.proposal_text[:500]}" for i, p in enumerate(proposals)]

        system_prompt = """You are analyzing policy proposals from Project 2025.
For each proposal, provide:
1. A concise summary (1-2 sentences)
2. Potential constitutional concerns (list any relevant amendments or legal issues)
3. Confidence score (0-1) for whether this is an actionable policy proposal

Respond in JSON format:
{
  "analyses": [
    {
      "index": 0,
      "summary": "...",
      "constitutional_concerns": ["First Amendment - free speech", "..."],
      "confidence": 0.85
    }
  ]
}"""

        user_prompt = f"""Analyze these Project 2025 policy proposals:

{chr(10).join(proposal_texts)}

Provide structured analysis for each."""

        try:
            response = client.chat(
                model=self.ollama_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                format="json",
            )

            content = response["message"]["content"]
            result = json.loads(content)

            for analysis in result.get("analyses", []):
                idx = analysis.get("index", 0)
                if 0 <= idx < len(proposals):
                    proposals[idx].proposal_summary = analysis.get("summary")
                    proposals[idx].constitutional_concerns = analysis.get(
                        "constitutional_concerns", []
                    )
                    proposals[idx].confidence = analysis.get("confidence", 0.5)

        except Exception:
            # Fall back to basic extraction on AI failure
            for p in proposals:
                p.confidence = 0.5

        return proposals

    def extract_by_chapter(self) -> dict[str, list[PolicyProposal]]:
        """Extract proposals organized by chapter."""
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber required: pip install pdfplumber")

        chapters = {}
        current_chapter = "Introduction"

        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""

                # Detect chapter headers
                chapter_match = re.search(
                    r"^(?:CHAPTER\s+\d+|SECTION\s+\d+)[:\s]+(.+?)$",
                    text,
                    re.MULTILINE | re.IGNORECASE,
                )
                if chapter_match:
                    current_chapter = chapter_match.group(1).strip()

                section = self._identify_section(page_num)

                for proposal in self._extract_from_page(text, section, page_num):
                    proposal.chapter = current_chapter
                    if current_chapter not in chapters:
                        chapters[current_chapter] = []
                    chapters[current_chapter].append(proposal)

        return chapters

    def generate_enhanced_summary(self, use_ai: bool = True) -> dict:
        """Generate comprehensive summary with AI enhancement."""
        proposals = list(self.extract_proposals_with_ai(use_ai=use_ai))

        by_agency = {}
        by_action = {}
        by_category = {}
        by_timeline = {}
        by_priority = {}
        constitutional_concerns = []

        for p in proposals:
            by_agency[p.agency] = by_agency.get(p.agency, 0) + 1
            by_action[p.action_type] = by_action.get(p.action_type, 0) + 1
            by_category[p.category] = by_category.get(p.category, 0) + 1
            by_timeline[p.implementation_timeline] = (
                by_timeline.get(p.implementation_timeline, 0) + 1
            )
            by_priority[p.priority] = by_priority.get(p.priority, 0) + 1
            constitutional_concerns.extend(p.constitutional_concerns)

        # Count constitutional concerns
        concern_counts = {}
        for concern in constitutional_concerns:
            concern_counts[concern] = concern_counts.get(concern, 0) + 1

        return {
            "total_proposals": len(proposals),
            "by_agency": dict(sorted(by_agency.items(), key=lambda x: -x[1])),
            "by_action_type": dict(sorted(by_action.items(), key=lambda x: -x[1])),
            "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
            "by_timeline": dict(sorted(by_timeline.items(), key=lambda x: -x[1])),
            "by_priority": dict(sorted(by_priority.items(), key=lambda x: -x[1])),
            "constitutional_concerns": dict(
                sorted(concern_counts.items(), key=lambda x: -x[1])[:20]
            ),
            "high_priority_day_one": [
                {
                    "agency": p.agency,
                    "summary": p.proposal_summary or p.proposal_text[:100],
                    "category": p.category,
                }
                for p in proposals
                if p.priority == "high" and p.implementation_timeline == "day_one"
            ][:20],
        }

    def get_actionable_items(self, category: str | None = None) -> list[PolicyProposal]:
        """Get high-confidence actionable proposals.

        Args:
            category: Filter by category (optional)

        Returns:
            List of high-confidence proposals sorted by priority
        """
        proposals = list(self.extract_proposals_with_ai(use_ai=True))

        # Filter high-confidence actionable items
        actionable = [p for p in proposals if p.confidence > 0.6 and p.action_type != "unknown"]

        if category:
            actionable = [p for p in actionable if p.category == category]

        # Sort by priority and confidence
        priority_order = {"high": 0, "medium": 1, "low": 2}
        actionable.sort(key=lambda p: (priority_order.get(p.priority, 1), -p.confidence))

        return actionable
