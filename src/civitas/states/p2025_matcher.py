"""P2025 policy matcher for state legislation.

Identifies state bills that relate to Project 2025 policies and uses
AI (Carl/Ollama) to determine whether they support or oppose each policy.

Usage:
    from civitas.states.p2025_matcher import P2025Matcher

    matcher = P2025Matcher(session)
    matches = matcher.match_bill(scraped_bill)
    for match in matches:
        print(f"Policy: {match.policy_title}")
        print(f"Stance: {match.stance} (confidence: {match.confidence})")
"""

import json
import os
import re
from collections.abc import Generator
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

# Default Ollama configuration (Carl AI VM on Azure)
DEFAULT_OLLAMA_HOST = "http://20.98.70.48:11434"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b-instruct-q8_0"


# P2025 policy categories and keywords for initial filtering
P2025_CATEGORIES = {
    "abortion": {
        "keywords": [
            "abortion",
            "reproductive",
            "pregnancy",
            "fetal",
            "unborn",
            "pro-life",
            "pro-choice",
            "roe",
            "dobbs",
            "contraception",
            "family planning",
            "planned parenthood",
            "termination",
        ],
        "p2025_stance": "restrict",  # P2025 wants to restrict
    },
    "immigration": {
        "keywords": [
            "immigration",
            "immigrant",
            "border",
            "asylum",
            "deportation",
            "alien",
            "refugee",
            "visa",
            "citizenship",
            "undocumented",
            "sanctuary",
            "ice",
            "dhs",
            "remain in mexico",
            "title 42",
        ],
        "p2025_stance": "restrict",
    },
    "environment": {
        "keywords": [
            "epa",
            "climate",
            "emissions",
            "environmental",
            "pollution",
            "clean air",
            "clean water",
            "carbon",
            "greenhouse",
            "fossil fuel",
            "renewable",
            "solar",
            "wind",
            "electric vehicle",
            "paris agreement",
        ],
        "p2025_stance": "deregulate",
    },
    "education": {
        "keywords": [
            "education",
            "school",
            "dei",
            "diversity equity inclusion",
            "critical race",
            "curriculum",
            "title ix",
            "student loan",
            "department of education",
            "charter school",
            "voucher",
            "transgender student",
            "library",
            "book ban",
        ],
        "p2025_stance": "reform",  # P2025 wants major reforms
    },
    "healthcare": {
        "keywords": [
            "medicaid",
            "medicare",
            "aca",
            "affordable care act",
            "obamacare",
            "health insurance",
            "drug pricing",
            "pharmaceutical",
            "fda",
            "public health",
            "hhs",
            "cdc",
            "vaccination",
            "mandate",
        ],
        "p2025_stance": "reform",
    },
    "labor": {
        "keywords": [
            "union",
            "nlrb",
            "minimum wage",
            "overtime",
            "worker",
            "collective bargaining",
            "right to work",
            "labor",
            "employee",
            "gig economy",
            "independent contractor",
        ],
        "p2025_stance": "deregulate",
    },
    "civil_rights": {
        "keywords": [
            "discrimination",
            "lgbtq",
            "transgender",
            "civil rights",
            "title vii",
            "eeoc",
            "affirmative action",
            "voting rights",
            "gender identity",
            "sexual orientation",
            "same-sex",
        ],
        "p2025_stance": "restrict",
    },
    "guns": {
        "keywords": [
            "firearm",
            "gun",
            "second amendment",
            "atf",
            "assault weapon",
            "background check",
            "red flag",
            "concealed carry",
            "ammunition",
        ],
        "p2025_stance": "expand",  # P2025 wants to expand gun rights
    },
    "federal_power": {
        "keywords": [
            "federal agency",
            "executive order",
            "administrative state",
            "chevron",
            "regulation",
            "deference",
            "bureaucracy",
            "schedule f",
            "civil service",
            "deep state",
        ],
        "p2025_stance": "reduce",
    },
}


@dataclass
class P2025Match:
    """A match between a state bill and a P2025 policy."""

    policy_id: int
    policy_title: str
    policy_category: str

    # Match details
    relevance_score: float  # 0-1, how relevant the bill is to this policy
    stance: str  # "supports", "opposes", "neutral"
    confidence: float  # 0-1, AI confidence in stance classification

    # Explanation
    rationale: str | None = None  # AI-generated explanation

    # Matched keywords
    matched_keywords: list[str] = field(default_factory=list)


class P2025Matcher:
    """Matches state legislation against Project 2025 policies.

    Uses a two-phase approach:
    1. Keyword matching for initial filtering (fast)
    2. AI analysis for stance detection (accurate)
    """

    def __init__(
        self,
        session: Session,
        ollama_host: str | None = None,
        ollama_model: str | None = None,
        use_ai: bool = True,
    ):
        """Initialize the matcher.

        Args:
            session: SQLAlchemy database session
            ollama_host: Ollama server URL (default: Carl AI VM)
            ollama_model: Model name (default: llama3.1:8b-instruct-q8_0)
            use_ai: Whether to use AI for stance detection
        """
        self.session = session
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        self.use_ai = use_ai
        self._policies_cache: dict[str, list] | None = None

    def _get_policies_by_category(self) -> dict[str, list]:
        """Load and cache P2025 policies grouped by category."""
        if self._policies_cache is not None:
            return self._policies_cache

        from civitas.db.models import Project2025Policy

        policies = self.session.query(Project2025Policy).all()

        # Group by category
        by_category: dict[str, list] = {}
        for policy in policies:
            cat = policy.category or "general"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(policy)

        self._policies_cache = by_category
        return by_category

    def _get_ollama_client(self):
        """Get Ollama client."""
        try:
            import ollama
        except ImportError:
            raise ImportError("Install ollama: pip install ollama")
        return ollama.Client(host=self.ollama_host)

    def match_bill(self, bill) -> list[P2025Match]:
        """Match a bill against P2025 policies.

        Args:
            bill: ScrapedBill or Legislation object

        Returns:
            List of P2025Match objects for relevant policies
        """
        # Get searchable text from bill
        if hasattr(bill, "get_searchable_text"):
            text = bill.get_searchable_text()
        else:
            # Handle database Legislation model
            parts = [bill.title or "", bill.summary or "", bill.full_text or ""]
            if bill.subjects:
                try:
                    parts.extend(json.loads(bill.subjects))
                except (json.JSONDecodeError, TypeError):
                    pass
            text = " ".join(parts).lower()

        # Phase 1: Keyword matching to find relevant categories
        relevant_categories = self._find_relevant_categories(text)

        if not relevant_categories:
            return []

        # Phase 2: Find matching policies and determine stance
        matches = []
        for category, matched_keywords in relevant_categories.items():
            category_matches = self._match_category_policies(bill, text, category, matched_keywords)
            matches.extend(category_matches)

        # Sort by relevance score
        matches.sort(key=lambda m: m.relevance_score, reverse=True)

        return matches

    def _find_relevant_categories(self, text: str) -> dict[str, list[str]]:
        """Find P2025 categories relevant to the bill text.

        Args:
            text: Lowercase bill text

        Returns:
            Dict mapping category to list of matched keywords
        """
        relevant = {}

        for category, info in P2025_CATEGORIES.items():
            matched = []
            for keyword in info["keywords"]:
                # Use word boundaries for matching
                pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
                if re.search(pattern, text):
                    matched.append(keyword)

            if matched:
                relevant[category] = matched

        return relevant

    def _match_category_policies(
        self,
        bill,
        text: str,
        category: str,
        matched_keywords: list[str],
    ) -> list[P2025Match]:
        """Match bill against policies in a specific category.

        Args:
            bill: Bill object
            text: Lowercase bill text
            category: P2025 category
            matched_keywords: Keywords that matched

        Returns:
            List of P2025Match objects
        """
        matches = []
        policies_by_cat = self._get_policies_by_category()

        # Get policies for this category and general
        policies = policies_by_cat.get(category, [])
        if category != "general":
            policies = policies + policies_by_cat.get("general", [])[:5]

        for policy in policies[:10]:  # Limit to top 10 per category
            # Calculate relevance based on keyword overlap
            policy_keywords = []
            if policy.keywords:
                try:
                    policy_keywords = json.loads(policy.keywords)
                except (json.JSONDecodeError, TypeError):
                    pass

            # Count keyword matches
            keyword_matches = set(matched_keywords)
            if policy_keywords:
                for kw in policy_keywords:
                    if kw.lower() in text:
                        keyword_matches.add(kw)

            relevance = min(1.0, len(keyword_matches) / 5.0)  # Normalize to 0-1

            if relevance < 0.2:
                continue  # Skip low relevance

            # Determine stance
            if self.use_ai:
                stance, confidence, rationale = self._ai_classify_stance(bill, policy, category)
            else:
                stance, confidence, rationale = self._heuristic_stance(bill, text, category)

            matches.append(
                P2025Match(
                    policy_id=policy.id,
                    policy_title=policy.short_title
                    or policy.proposal_summary
                    or f"Policy {policy.id}",
                    policy_category=category,
                    relevance_score=relevance,
                    stance=stance,
                    confidence=confidence,
                    rationale=rationale,
                    matched_keywords=list(keyword_matches),
                )
            )

        return matches

    def _heuristic_stance(
        self,
        bill,
        text: str,
        category: str,
    ) -> tuple[str, float, str | None]:
        """Determine stance using heuristics (no AI).

        Args:
            bill: Bill object
            text: Bill text
            category: P2025 category

        Returns:
            Tuple of (stance, confidence, rationale)
        """
        p2025_stance = P2025_CATEGORIES.get(category, {}).get("p2025_stance", "unknown")

        # Look for resistance/protection language
        resistance_terms = [
            "protect",
            "preserve",
            "defend",
            "safeguard",
            "expand",
            "strengthen",
            "guarantee",
            "ensure access",
            "right to",
        ]

        restriction_terms = [
            "prohibit",
            "ban",
            "restrict",
            "limit",
            "eliminate",
            "repeal",
            "defund",
            "reduce",
            "terminate",
        ]

        resistance_count = sum(1 for term in resistance_terms if term in text)
        restriction_count = sum(1 for term in restriction_terms if term in text)

        # Determine stance based on what P2025 wants vs what the bill does
        if p2025_stance in ["restrict", "reduce", "deregulate"]:
            # P2025 wants to restrict/reduce; protection = opposition
            if resistance_count > restriction_count:
                return "opposes", 0.6, "Bill appears to protect/expand what P2025 wants to restrict"
            elif restriction_count > resistance_count:
                return "supports", 0.6, "Bill appears to restrict what P2025 wants restricted"
        elif p2025_stance in ["expand"]:
            # P2025 wants to expand; restriction = opposition
            if restriction_count > resistance_count:
                return "opposes", 0.6, "Bill appears to restrict what P2025 wants to expand"
            elif resistance_count > restriction_count:
                return "supports", 0.6, "Bill appears to expand what P2025 wants expanded"

        return "neutral", 0.4, "Unable to determine clear stance from text"

    def _ai_classify_stance(
        self,
        bill,
        policy,
        category: str,
    ) -> tuple[str, float, str | None]:
        """Use AI to classify bill's stance toward P2025 policy.

        Args:
            bill: Bill object
            policy: P2025 policy object
            category: Policy category

        Returns:
            Tuple of (stance, confidence, rationale)
        """
        client = self._get_ollama_client()

        # Get bill text
        bill_title = getattr(bill, "title", "") or ""
        bill_summary = getattr(bill, "summary", "") or getattr(bill, "full_text", "")[:1000] or ""
        bill_state = getattr(bill, "state", "").upper()

        system_prompt = (
            "You are a legislative analyst determining whether a state bill "
            "supports or opposes a Project 2025 policy proposal.\n\n"
            "Project 2025 is a conservative policy blueprint. You must determine "
            "if the state bill:\n"
            "- SUPPORTS the P2025 policy (aligns with, implements, or advances "
            "similar goals)\n"
            "- OPPOSES the P2025 policy (counters, blocks, or provides "
            "protections against it)\n"
            "- NEUTRAL (not clearly related or takes no clear stance)\n\n"
            "Respond in JSON format with:\n"
            '- stance: "supports", "opposes", or "neutral"\n'
            "- confidence: 0.0 to 1.0\n"
            "- rationale: 1-2 sentence explanation"
        )

        policy_text = (
            policy.proposal_text[:500]
            if policy.proposal_text
            else (policy.proposal_summary or "No text available")
        )
        user_prompt = (
            f"STATE BILL ({bill_state}):\n"
            f"Title: {bill_title}\n"
            f"Summary: {bill_summary[:800]}\n\n"
            f"PROJECT 2025 POLICY:\n"
            f"Category: {category}\n"
            f"Policy: {policy_text}\n\n"
            "Does this state bill support, oppose, or remain neutral toward "
            "this P2025 policy?"
        )

        try:
            response = client.chat(
                model=self.ollama_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                format="json",
                options={"temperature": 0.2, "num_predict": 200},
            )

            content = response["message"]["content"]
            result = json.loads(content)

            stance = result.get("stance", "neutral").lower()
            if stance not in ["supports", "opposes", "neutral"]:
                stance = "neutral"

            confidence = float(result.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))

            rationale = result.get("rationale", "")

            return stance, confidence, rationale

        except Exception as e:
            # Fall back to heuristic on error
            return "neutral", 0.3, f"AI analysis failed: {str(e)[:50]}"

    def batch_match_bills(
        self,
        bills,
        min_relevance: float = 0.3,
    ) -> Generator[tuple, None, None]:
        """Match multiple bills against P2025 policies.

        Args:
            bills: Iterable of bill objects
            min_relevance: Minimum relevance score to include

        Yields:
            Tuples of (bill, matches)
        """
        for bill in bills:
            matches = self.match_bill(bill)
            filtered = [m for m in matches if m.relevance_score >= min_relevance]
            if filtered:
                yield bill, filtered


def match_state_legislation(
    session: Session,
    state: str | None = None,
    limit: int | None = None,
    use_ai: bool = True,
) -> list[dict]:
    """Match state legislation against P2025 policies.

    Args:
        session: Database session
        state: Optional state filter (two-letter code)
        limit: Maximum bills to process
        use_ai: Whether to use AI for stance detection

    Returns:
        List of match results
    """
    from civitas.db.models import Legislation

    matcher = P2025Matcher(session, use_ai=use_ai)

    # Query legislation
    query = session.query(Legislation)

    if state:
        # Map state code to jurisdiction
        jurisdiction = state.lower()
        if len(state) == 2:
            from civitas.states.scrapers import STATE_NAMES

            jurisdiction = STATE_NAMES.get(state.lower(), state).lower().replace(" ", "_")
        query = query.filter(Legislation.jurisdiction == jurisdiction)

    # Exclude federal
    query = query.filter(Legislation.jurisdiction != "federal")

    if limit:
        query = query.limit(limit)

    results = []
    for bill, matches in matcher.batch_match_bills(query.all()):
        results.append(
            {
                "bill_id": bill.id,
                "citation": bill.citation,
                "title": bill.title,
                "state": bill.jurisdiction,
                "matches": [
                    {
                        "policy_id": m.policy_id,
                        "policy_title": m.policy_title,
                        "category": m.policy_category,
                        "relevance": m.relevance_score,
                        "stance": m.stance,
                        "confidence": m.confidence,
                        "rationale": m.rationale,
                    }
                    for m in matches
                ],
            }
        )

    return results
