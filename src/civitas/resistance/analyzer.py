"""AI-powered resistance analysis using Carl (Ollama/Llama).

Analyzes P2025 policies against constitutional law, court precedents,
and existing legislation to identify legal vulnerabilities and
counter-strategies.
"""

import json
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

# Default Ollama configuration (Carl AI VM on Azure)
DEFAULT_OLLAMA_HOST = "http://20.98.70.48:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"


class ResistanceAnalyzer:
    """Analyzes P2025 policies for legal vulnerabilities.

    Uses Carl (Llama on Ollama) to:
    1. Identify constitutional issues
    2. Find relevant court precedents
    3. Suggest legal challenge strategies
    4. Generate resistance recommendations

    Example:
        >>> analyzer = ResistanceAnalyzer(session)
        >>> analysis = analyzer.analyze_policy(policy_id=42)
        >>> print(analysis['constitutional_issues'])
        >>> print(analysis['recommended_challenges'])
    """

    # Constitutional provisions commonly relevant to resistance
    CONSTITUTIONAL_PROVISIONS = {
        "1st_amendment": {
            "name": "First Amendment",
            "text": "Congress shall make no law respecting an establishment of religion, "
            "or prohibiting the free exercise thereof; or abridging the freedom of speech, "
            "or of the press; or the right of the people peaceably to assemble, "
            "and to petition the Government for a redress of grievances.",
            "areas": ["religion", "speech", "press", "assembly", "petition"],
        },
        "4th_amendment": {
            "name": "Fourth Amendment",
            "text": "The right of the people to be secure in their persons, houses, papers, "
            "and effects, against unreasonable searches and seizures, shall not be violated.",
            "areas": ["privacy", "searches", "surveillance"],
        },
        "5th_amendment": {
            "name": "Fifth Amendment",
            "text": "No person shall be... deprived of life, liberty, or property, "
            "without due process of law; nor shall private property be taken "
            "for public use, without just compensation.",
            "areas": ["due_process", "self_incrimination", "takings"],
        },
        "10th_amendment": {
            "name": "Tenth Amendment",
            "text": "The powers not delegated to the United States by the Constitution, "
            "nor prohibited by it to the States, are reserved to the States respectively, "
            "or to the people.",
            "areas": ["federalism", "state_rights", "commandeering"],
        },
        "14th_amendment": {
            "name": "Fourteenth Amendment",
            "text": "No State shall make or enforce any law which shall abridge the privileges "
            "or immunities of citizens of the United States; nor shall any State deprive "
            "any person of life, liberty, or property, without due process of law; "
            "nor deny to any person within its jurisdiction the equal protection of the laws.",
            "areas": ["equal_protection", "due_process", "privileges_immunities"],
        },
        "apa": {
            "name": "Administrative Procedure Act",
            "text": "Requires federal agencies to follow notice-and-comment rulemaking, "
            "provides for judicial review of agency actions as arbitrary and capricious.",
            "areas": ["rulemaking", "notice_comment", "arbitrary_capricious"],
        },
    }

    # Key precedents for resistance
    KEY_PRECEDENTS = {
        "chevron": {
            "citation": "Chevron U.S.A., Inc. v. NRDC, 467 U.S. 837 (1984)",
            "holding": "Courts defer to reasonable agency interpretations of ambiguous statutes.",
            "status": "overruled",  # By Loper Bright
            "relevance": ["agency_interpretation", "regulatory"],
        },
        "loper_bright": {
            "citation": "Loper Bright Enterprises v. Raimondo, 603 U.S. ___ (2024)",
            "holding": "Overruled Chevron; courts must exercise independent judgment on statutory interpretation.",
            "status": "current",
            "relevance": ["agency_interpretation", "regulatory", "deference"],
        },
        "youngstown": {
            "citation": "Youngstown Sheet & Tube Co. v. Sawyer, 343 U.S. 579 (1952)",
            "holding": "Executive power is limited; president cannot act contrary to congressional will.",
            "status": "current",
            "relevance": ["executive_power", "separation_of_powers"],
        },
        "murphy_v_ncaa": {
            "citation": "Murphy v. NCAA, 584 U.S. ___ (2018)",
            "holding": "Federal government cannot commandeer states to enforce federal policy.",
            "status": "current",
            "relevance": ["anti_commandeering", "federalism", "10th_amendment"],
        },
        "printz": {
            "citation": "Printz v. United States, 521 U.S. 898 (1997)",
            "holding": "Federal government cannot compel state officials to enforce federal law.",
            "status": "current",
            "relevance": ["anti_commandeering", "federalism", "sanctuary"],
        },
        "nfib_v_sebelius": {
            "citation": "NFIB v. Sebelius, 567 U.S. 519 (2012)",
            "holding": "Spending Clause cannot be used to coerce states; limits on conditional funding.",
            "status": "current",
            "relevance": ["coercion", "conditional_funding", "federalism"],
        },
        "obergefell": {
            "citation": "Obergefell v. Hodges, 576 U.S. 644 (2015)",
            "holding": "Same-sex marriage is a constitutional right under Due Process and Equal Protection.",
            "status": "current",
            "relevance": ["marriage_equality", "lgbtq", "due_process", "equal_protection"],
        },
        "bostock": {
            "citation": "Bostock v. Clayton County, 590 U.S. ___ (2020)",
            "holding": "Title VII prohibits discrimination based on sexual orientation and gender identity.",
            "status": "current",
            "relevance": ["employment", "lgbtq", "title_vii"],
        },
    }

    def __init__(
        self,
        session: Session,
        ollama_host: str | None = None,
        ollama_model: str | None = None,
    ):
        """Initialize the resistance analyzer.

        Args:
            session: SQLAlchemy database session
            ollama_host: Ollama server URL (default: Carl AI VM)
            ollama_model: Model name (default: llama3.2)
        """
        self.session = session
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)

    def get_cached_analysis(
        self,
        policy_id: int,
        max_age_days: int | None = None,
    ) -> dict | None:
        """Return cached analysis if available and not stale."""
        from civitas.db.models import ResistanceAnalysis

        analysis = (
            self.session.query(ResistanceAnalysis)
            .filter(ResistanceAnalysis.p2025_policy_id == policy_id)
            .first()
        )
        if not analysis:
            return None

        if max_age_days is not None:
            cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
            if analysis.generated_at and analysis.generated_at < cutoff:
                return None

        try:
            return json.loads(analysis.analysis_json)
        except json.JSONDecodeError:
            return None

    def store_analysis(self, policy_id: int, analysis: dict) -> None:
        """Persist analysis for expert mode."""
        from civitas.db.models import ResistanceAnalysis

        serialized = json.dumps(analysis, ensure_ascii=True)
        existing = (
            self.session.query(ResistanceAnalysis)
            .filter(ResistanceAnalysis.p2025_policy_id == policy_id)
            .first()
        )
        if existing:
            existing.analysis_json = serialized
            existing.ai_model_version = analysis.get("model", self.ollama_model)
            existing.generated_at = datetime.now(UTC)
        else:
            self.session.add(
                ResistanceAnalysis(
                    p2025_policy_id=policy_id,
                    analysis_json=serialized,
                    ai_model_version=analysis.get("model", self.ollama_model),
                    generated_at=datetime.now(UTC),
                )
            )
        self.session.commit()

    def _get_ollama_client(self):
        """Get Ollama client."""
        try:
            import ollama
        except ImportError:
            raise ImportError("Install ollama: pip install ollama")
        return ollama.Client(host=self.ollama_host)

    def analyze_policy(self, policy_id: int, persist: bool = False) -> dict:
        """Analyze a P2025 policy for legal vulnerabilities.

        Args:
            policy_id: Database ID of the P2025 policy
            persist: Store analysis for expert mode cache

        Returns:
            Analysis dict with constitutional issues, precedents, and strategies
        """
        from civitas.db.models import Project2025Policy

        # Get the policy
        policy = self.session.query(Project2025Policy).filter_by(id=policy_id).first()
        if not policy:
            return {"error": f"Policy {policy_id} not found"}

        # Gather context from database
        context = self._gather_legal_context(policy)

        # Use AI to analyze
        analysis = self._ai_analyze(policy, context)

        if persist and not analysis.get("error"):
            self.store_analysis(policy_id, analysis)

        return analysis

    def analyze_or_load(self, policy_id: int, max_age_days: int | None = None) -> dict:
        """Load cached analysis or generate a new one."""
        cached = self.get_cached_analysis(policy_id, max_age_days=max_age_days)
        if cached:
            return cached
        return self.analyze_policy(policy_id, persist=True)

    def batch_analyze_cached(
        self,
        limit: int = 100,
        refresh_days: int = 30,
    ) -> int:
        """Generate cached analysis for policies missing or stale."""
        from civitas.db.models import Project2025Policy, ResistanceAnalysis

        cutoff = datetime.now(UTC) - timedelta(days=refresh_days)

        policies = (
            self.session.query(Project2025Policy)
            .outerjoin(
                ResistanceAnalysis,
                ResistanceAnalysis.p2025_policy_id == Project2025Policy.id,
            )
            .filter(
                (ResistanceAnalysis.id.is_(None))
                | (ResistanceAnalysis.generated_at.is_(None))
                | (ResistanceAnalysis.generated_at < cutoff)
            )
            .order_by(Project2025Policy.id)
            .limit(limit)
            .all()
        )

        processed = 0
        for policy in policies:
            analysis = self.analyze_policy(policy.id, persist=True)
            if analysis.get("error"):
                continue
            processed += 1
        return processed

    def _gather_legal_context(self, policy) -> dict:
        """Gather relevant legal context for a policy."""
        from civitas.db.models import CourtCase

        context = {
            "policy": {
                "id": policy.id,
                "agency": policy.agency,
                "section": policy.section,
                "proposal": policy.proposal_text,
                "keywords": json.loads(policy.keywords) if policy.keywords else [],
            },
            "relevant_cases": [],
            "relevant_legislation": [],
            "relevant_statutes": [],
            "constitutional_provisions": [],
        }

        # Identify potentially relevant constitutional provisions
        proposal_lower = policy.proposal_text.lower()

        # Match provisions based on content
        provision_matches = []
        if any(term in proposal_lower for term in ["religion", "church", "faith", "prayer"]):
            provision_matches.append("1st_amendment")
        if any(term in proposal_lower for term in ["speech", "press", "media", "censorship"]):
            provision_matches.append("1st_amendment")
        if any(term in proposal_lower for term in ["privacy", "surveillance", "search"]):
            provision_matches.append("4th_amendment")
        if any(term in proposal_lower for term in ["due process", "hearing", "notice"]):
            provision_matches.append("5th_amendment")
        if any(term in proposal_lower for term in ["state", "federal", "commandeer"]):
            provision_matches.append("10th_amendment")
        if any(term in proposal_lower for term in ["equal", "discrimination", "gender", "race"]):
            provision_matches.append("14th_amendment")
        if any(term in proposal_lower for term in ["rule", "regulation", "guidance", "agency"]):
            provision_matches.append("apa")

        for prov_key in set(provision_matches):
            context["constitutional_provisions"].append(self.CONSTITUTIONAL_PROVISIONS[prov_key])

        # Search for relevant court cases
        keywords = context["policy"]["keywords"][:5]
        if keywords:
            cases = (
                self.session.query(CourtCase)
                .filter(
                    CourtCase.case_name.ilike(f"%{keywords[0]}%")
                    | CourtCase.holding.ilike(f"%{keywords[0]}%")
                )
                .limit(10)
                .all()
            )

            for case in cases:
                context["relevant_cases"].append(
                    {
                        "citation": case.citation,
                        "case_name": case.case_name,
                        "holding": case.holding[:500] if case.holding else None,
                        "court": case.court,
                    }
                )

        return context

    def _ai_analyze(self, policy, context: dict) -> dict:
        """Use AI to analyze the policy and generate resistance strategies."""
        client = self._get_ollama_client()

        system_prompt = """You are a constitutional law expert analyzing government policies for legal vulnerabilities. Your role is to:

1. Identify constitutional issues with the policy
2. Find relevant legal precedents that could challenge it
3. Suggest legal strategies for resistance
4. Assess likelihood of success for different approaches

Be specific and cite actual constitutional provisions and case law.
Focus on actionable legal strategies, not political commentary.

Respond in JSON format with these fields:
- constitutional_issues: Array of {provision, issue, severity}
- relevant_precedents: Array of {citation, relevance}
- challenge_strategies: Array of {type, basis, likelihood, explanation}
- state_resistance_options: Array of {action, legal_basis, explanation}
- immediate_actions: Array of {action, who, explanation}
- overall_vulnerability_score: Number 0-100 (100 = most vulnerable to challenge)
"""

        user_prompt = f"""Analyze this Project 2025 policy proposal for legal vulnerabilities:

AGENCY: {policy.agency}
SECTION: {policy.section}
PROPOSAL: {policy.proposal_text}

CONTEXT FROM DATABASE:
Constitutional Provisions Potentially Relevant:
{json.dumps(context["constitutional_provisions"], indent=2)}

Related Court Cases in Database:
{json.dumps(context["relevant_cases"], indent=2)}

KEY PRECEDENTS TO CONSIDER:
{json.dumps(list(self.KEY_PRECEDENTS.values()), indent=2)}

Provide a detailed legal analysis with specific constitutional provisions and case citations.
Focus on realistic, actionable legal strategies."""

        try:
            response = client.chat(
                model=self.ollama_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                format="json",
                options={"temperature": 0.2, "num_predict": 800},
            )

            content = response["message"]["content"]

            # Parse JSON response
            try:
                analysis = json.loads(content)
            except json.JSONDecodeError:
                extracted = content
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1 and end > start:
                    extracted = content[start : end + 1]
                    try:
                        analysis = json.loads(extracted)
                    except json.JSONDecodeError:
                        analysis = {"raw_response": content, "parse_error": True}
                else:
                    analysis = {"raw_response": content, "parse_error": True}

            # Add metadata
            analysis["policy_id"] = policy.id
            analysis["analyzed_at"] = datetime.now(UTC).isoformat()
            analysis["model"] = self.ollama_model

            return analysis

        except Exception as e:
            return {
                "error": str(e),
                "policy_id": policy.id,
                "context": context,
            }

    def batch_analyze(self, limit: int = 50) -> list[dict]:
        """Analyze multiple policies that haven't been analyzed yet.

        Args:
            limit: Maximum policies to analyze

        Returns:
            List of analysis results
        """
        from civitas.db.models import Project2025Policy

        # Get policies without recent analysis
        policies = (
            self.session.query(Project2025Policy)
            .filter(Project2025Policy.last_checked.is_(None))
            .limit(limit)
            .all()
        )

        results = []
        for policy in policies:
            analysis = self.analyze_policy(policy.id)
            results.append(analysis)

            # Update last_checked
            policy.last_checked = datetime.now(UTC)

        self.session.commit()
        return results

    def find_constitutional_violations(self, policy_id: int) -> list[dict]:
        """Find specific constitutional violations in a policy.

        Args:
            policy_id: Database ID of the P2025 policy

        Returns:
            List of potential constitutional violations with citations
        """
        analysis = self.analyze_policy(policy_id)
        return analysis.get("constitutional_issues", [])

    def suggest_legal_challenges(self, policy_id: int) -> list[dict]:
        """Suggest legal challenge strategies for a policy.

        Args:
            policy_id: Database ID of the P2025 policy

        Returns:
            List of suggested legal challenges with strategies
        """
        analysis = self.analyze_policy(policy_id)
        return analysis.get("challenge_strategies", [])

    def get_state_resistance_options(self, policy_id: int) -> list[dict]:
        """Get state-level resistance options for a policy.

        Args:
            policy_id: Database ID of the P2025 policy

        Returns:
            List of state resistance actions
        """
        analysis = self.analyze_policy(policy_id)
        return analysis.get("state_resistance_options", [])
