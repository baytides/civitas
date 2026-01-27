"""Implementation tracker for Project 2025 policies.

Tracks the progress of P2025 implementation against:
- Executive Orders and Presidential Proclamations
- Federal Register documents (rules, notices)
- Agency actions and guidance
- Legislation

Cross-references with project2025.observer data structure.
"""

import json
import os
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

# Default Ollama configuration (Carl AI VM on Azure)
DEFAULT_OLLAMA_HOST = "http://20.98.70.48:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"


class ImplementationTracker:
    """Tracks Project 2025 implementation progress.

    Monitors government actions and matches them against P2025 objectives
    to track implementation progress similar to project2025.observer.

    Example:
        >>> tracker = ImplementationTracker(session)
        >>> progress = tracker.get_progress_summary()
        >>> print(f"Completed: {progress['completed']}")
        >>> print(f"In Progress: {progress['in_progress']}")
        >>> print(f"Not Started: {progress['not_started']}")
    """

    # Status values matching project2025.observer structure
    STATUS_NOT_STARTED = "not_started"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_BLOCKED = "blocked"
    STATUS_REVERSED = "reversed"

    # Categories based on P2025 document structure
    CATEGORIES = [
        "White House",
        "Executive Office of the President",
        "Department of State",
        "Department of Defense",
        "Department of Homeland Security",
        "Department of Justice",
        "Department of Education",
        "Department of Health and Human Services",
        "Department of Agriculture",
        "Department of Housing and Urban Development",
        "Department of Interior",
        "Department of Labor",
        "Department of Transportation",
        "Department of Energy",
        "Environmental Protection Agency",
        "Department of Commerce",
        "Department of Treasury",
        "Department of Veterans Affairs",
        "Intelligence Community",
        "Media Agencies",
        "Agency for International Development",
        "Independent Regulatory Agencies",
        "Financial Regulatory Agencies",
        "Federal Reserve",
        "Federal Communications Commission",
        "Federal Trade Commission",
        "Federal Election Commission",
    ]

    def __init__(
        self,
        session: Session,
        ollama_host: Optional[str] = None,
        ollama_model: Optional[str] = None,
    ):
        """Initialize the implementation tracker.

        Args:
            session: SQLAlchemy database session
            ollama_host: Ollama server URL (default: Carl AI VM)
            ollama_model: Model name (default: llama3.2)
        """
        self.session = session
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)

    def _get_ollama_client(self):
        """Get Ollama client."""
        try:
            import ollama
        except ImportError:
            raise ImportError("Install ollama: pip install ollama")
        return ollama.Client(host=self.ollama_host)

    def get_progress_summary(self) -> dict:
        """Get overall P2025 implementation progress summary.

        Returns:
            Dict with counts by status and category
        """
        from civitas.db.models import Project2025Policy

        total = self.session.query(Project2025Policy).count()

        by_status = {}
        for status in [self.STATUS_NOT_STARTED, self.STATUS_IN_PROGRESS,
                       self.STATUS_COMPLETED, self.STATUS_BLOCKED, self.STATUS_REVERSED]:
            count = self.session.query(Project2025Policy).filter(
                Project2025Policy.status == status
            ).count()
            by_status[status] = count

        # By agency
        by_agency = self.session.query(
            Project2025Policy.agency,
            func.count(Project2025Policy.id)
        ).group_by(Project2025Policy.agency).all()

        return {
            "total_objectives": total,
            "by_status": by_status,
            "by_agency": {agency: count for agency, count in by_agency},
            "completion_percentage": (
                (by_status.get(self.STATUS_COMPLETED, 0) / total * 100)
                if total > 0 else 0
            ),
            "as_of": datetime.utcnow().isoformat(),
        }

    def match_executive_order(self, eo_id: int) -> list[dict]:
        """Match an executive order against P2025 objectives.

        Args:
            eo_id: Database ID of the executive order

        Returns:
            List of matched P2025 policies with confidence scores
        """
        from civitas.db.models import ExecutiveOrder, Project2025Policy

        eo = self.session.query(ExecutiveOrder).filter_by(id=eo_id).first()
        if not eo:
            return []

        # Get EO text for matching
        eo_text = f"{eo.title} {eo.abstract or ''}"

        # Get all P2025 policies for AI matching
        policies = self.session.query(Project2025Policy).all()

        matches = []
        for policy in policies:
            score = self._calculate_match_score(eo_text, policy)
            if score > 0.3:  # Threshold for relevance
                matches.append({
                    "policy_id": policy.id,
                    "agency": policy.agency,
                    "proposal": policy.proposal_text[:200],
                    "confidence": score,
                })

        return sorted(matches, key=lambda x: x["confidence"], reverse=True)

    def match_federal_register_doc(self, doc_number: str) -> list[dict]:
        """Match a Federal Register document against P2025 objectives.

        Args:
            doc_number: Federal Register document number

        Returns:
            List of matched P2025 policies
        """
        from civitas.db.models import FederalRegisterDocument, Project2025Policy

        doc = self.session.query(FederalRegisterDocument).filter_by(
            document_number=doc_number
        ).first()

        if not doc:
            return []

        doc_text = f"{doc.title} {doc.abstract or ''}"
        policies = self.session.query(Project2025Policy).filter(
            Project2025Policy.agency.ilike(f"%{doc.agencies[0] if doc.agencies else ''}%")
        ).all()

        matches = []
        for policy in policies:
            score = self._calculate_match_score(doc_text, policy)
            if score > 0.3:
                matches.append({
                    "policy_id": policy.id,
                    "agency": policy.agency,
                    "proposal": policy.proposal_text[:200],
                    "confidence": score,
                })

        return sorted(matches, key=lambda x: x["confidence"], reverse=True)

    def _calculate_match_score(self, text: str, policy) -> float:
        """Calculate match score between text and a P2025 policy.

        Uses keyword matching and optionally AI for deeper analysis.
        """
        text_lower = text.lower()
        policy_text = f"{policy.proposal_text} {policy.agency}".lower()

        # Keyword-based scoring
        keywords = json.loads(policy.keywords) if policy.keywords else []
        if not keywords:
            # Extract keywords from proposal
            words = policy.proposal_text.lower().split()
            skip = {"the", "a", "an", "to", "of", "and", "or", "for", "in", "on", "with"}
            keywords = [w for w in words if w not in skip and len(w) > 3][:10]

        matches = sum(1 for kw in keywords if kw in text_lower)
        keyword_score = matches / len(keywords) if keywords else 0

        # Agency matching
        agency_score = 0.3 if policy.agency.lower() in text_lower else 0

        # Combined score
        return min(1.0, keyword_score * 0.7 + agency_score)

    def update_policy_status(
        self,
        policy_id: int,
        status: str,
        evidence_urls: Optional[list[str]] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Update the implementation status of a P2025 policy.

        Args:
            policy_id: Database ID of the policy
            status: New status (not_started, in_progress, completed, blocked, reversed)
            evidence_urls: URLs documenting the implementation
            notes: Additional notes

        Returns:
            True if updated successfully
        """
        from civitas.db.models import Project2025Policy

        policy = self.session.query(Project2025Policy).filter_by(id=policy_id).first()
        if not policy:
            return False

        policy.status = status
        policy.last_checked = datetime.utcnow()

        if evidence_urls:
            existing = json.loads(policy.evidence_urls) if policy.evidence_urls else []
            existing.extend(evidence_urls)
            policy.evidence_urls = json.dumps(list(set(existing)))

        self.session.commit()
        return True

    def link_implementation(
        self,
        policy_id: int,
        action_type: str,
        action_id: int,
        action_reference: str,
    ) -> int:
        """Link a P2025 policy to an implementing action.

        Args:
            policy_id: Database ID of the P2025 policy
            action_type: Type of action (executive_order, rule, legislation, etc.)
            action_id: Database ID of the implementing action
            action_reference: Human-readable reference (e.g., "EO 14XXX")

        Returns:
            ID of the created implementation record
        """
        from civitas.db.models import P2025Implementation

        impl = P2025Implementation(
            policy_id=policy_id,
            action_type=action_type,
            action_id=action_id,
            action_reference=action_reference,
            implementation_date=date.today(),
            status="active",
        )
        self.session.add(impl)
        self.session.commit()

        # Update policy status
        self.update_policy_status(policy_id, self.STATUS_IN_PROGRESS)

        return impl.id

    def get_recent_implementations(self, days: int = 30, limit: int = 50) -> list[dict]:
        """Get recent P2025 implementation activity.

        Args:
            days: Number of days to look back
            limit: Maximum results

        Returns:
            List of recent implementation actions
        """
        from civitas.db.models import P2025Implementation, Project2025Policy

        since = date.today() - timedelta(days=days)

        implementations = self.session.query(P2025Implementation).filter(
            P2025Implementation.implementation_date >= since
        ).order_by(
            P2025Implementation.implementation_date.desc()
        ).limit(limit).all()

        results = []
        for impl in implementations:
            policy = self.session.query(Project2025Policy).filter_by(
                id=impl.policy_id
            ).first()

            results.append({
                "id": impl.id,
                "policy_id": impl.policy_id,
                "agency": policy.agency if policy else "Unknown",
                "proposal": policy.proposal_text[:200] if policy else "",
                "action_type": impl.action_type,
                "action_reference": impl.action_reference,
                "date": impl.implementation_date.isoformat(),
                "status": impl.status,
            })

        return results

    def get_blocked_policies(self) -> list[dict]:
        """Get P2025 policies that have been blocked (by courts, states, etc.).

        Returns:
            List of blocked policies with blocking details
        """
        from civitas.db.models import Project2025Policy, LegalChallenge

        policies = self.session.query(Project2025Policy).filter(
            Project2025Policy.status == self.STATUS_BLOCKED
        ).all()

        results = []
        for policy in policies:
            # Get associated legal challenges
            challenges = self.session.query(LegalChallenge).filter(
                LegalChallenge.p2025_policy_id == policy.id,
                LegalChallenge.status.in_(["won", "injunction_granted"])
            ).all()

            results.append({
                "policy_id": policy.id,
                "agency": policy.agency,
                "proposal": policy.proposal_text[:200],
                "challenges": [
                    {
                        "case": c.case_citation,
                        "court": c.court_level,
                        "status": c.status,
                        "outcome": c.outcome_summary,
                    }
                    for c in challenges
                ],
            })

        return results

    def get_agency_progress(self, agency: str) -> dict:
        """Get implementation progress for a specific agency.

        Args:
            agency: Agency name (e.g., "Department of Education")

        Returns:
            Progress summary for the agency
        """
        from civitas.db.models import Project2025Policy

        policies = self.session.query(Project2025Policy).filter(
            Project2025Policy.agency.ilike(f"%{agency}%")
        ).all()

        by_status = {}
        for status in [self.STATUS_NOT_STARTED, self.STATUS_IN_PROGRESS,
                       self.STATUS_COMPLETED, self.STATUS_BLOCKED, self.STATUS_REVERSED]:
            by_status[status] = sum(1 for p in policies if p.status == status)

        return {
            "agency": agency,
            "total_objectives": len(policies),
            "by_status": by_status,
            "completion_percentage": (
                (by_status.get(self.STATUS_COMPLETED, 0) / len(policies) * 100)
                if policies else 0
            ),
            "objectives": [
                {
                    "id": p.id,
                    "proposal": p.proposal_text[:200],
                    "status": p.status,
                    "page": p.page_number,
                }
                for p in policies[:20]  # Limit details
            ],
        }

    def scan_new_eos_for_matches(self, days: int = 7) -> list[dict]:
        """Scan recent executive orders for P2025 matches.

        Args:
            days: Number of days to look back

        Returns:
            List of EOs with their P2025 policy matches
        """
        from civitas.db.models import ExecutiveOrder

        since = date.today() - timedelta(days=days)

        eos = self.session.query(ExecutiveOrder).filter(
            ExecutiveOrder.signing_date >= since
        ).all()

        results = []
        for eo in eos:
            matches = self.match_executive_order(eo.id)
            if matches:
                results.append({
                    "eo_id": eo.id,
                    "eo_number": eo.executive_order_number,
                    "title": eo.title,
                    "date": eo.signing_date.isoformat() if eo.signing_date else None,
                    "matches": matches[:5],  # Top 5 matches
                })

        return results

    def generate_progress_report(self) -> dict:
        """Generate a comprehensive progress report similar to project2025.observer.

        Returns:
            Full progress report with all metrics
        """
        summary = self.get_progress_summary()

        # Get agency breakdown
        agency_progress = {}
        for agency in self.CATEGORIES[:10]:  # Top 10 agencies
            agency_progress[agency] = self.get_agency_progress(agency)

        # Get recent activity
        recent = self.get_recent_implementations(days=30)

        # Get blocked policies
        blocked = self.get_blocked_policies()

        return {
            "summary": summary,
            "by_agency": agency_progress,
            "recent_activity": recent,
            "blocked_policies": blocked,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def ai_classify_action(self, action_text: str, action_type: str) -> list[dict]:
        """Use AI to classify a government action against P2025 objectives.

        Args:
            action_text: Text of the action (EO title/abstract, rule summary, etc.)
            action_type: Type of action (executive_order, rule, legislation)

        Returns:
            List of matched P2025 policies with reasoning
        """
        from civitas.db.models import Project2025Policy

        client = self._get_ollama_client()

        # Get all policies grouped by agency
        policies = self.session.query(Project2025Policy).limit(100).all()

        policy_summaries = [
            f"ID {p.id} ({p.agency}): {p.proposal_text[:150]}"
            for p in policies
        ]

        system_prompt = """You are an expert at matching government actions to Project 2025 policy objectives.

Given a government action (executive order, rule, or legislation), identify which Project 2025 objectives it implements or advances.

Respond in JSON format:
{
  "matches": [
    {
      "policy_id": <number>,
      "confidence": <0.0-1.0>,
      "reasoning": "<why this matches>"
    }
  ],
  "analysis": "<brief overall analysis>"
}

Only include matches with confidence > 0.5."""

        user_prompt = f"""Classify this {action_type}:

ACTION TEXT:
{action_text}

PROJECT 2025 OBJECTIVES TO CHECK:
{chr(10).join(policy_summaries)}

Which P2025 objectives does this action implement or advance?"""

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
            return result.get("matches", [])

        except Exception as e:
            return [{"error": str(e)}]

    def sync_with_observer_data(self, observer_data: list[dict]) -> dict:
        """Sync local tracking with project2025.observer data.

        Args:
            observer_data: List of objectives from project2025.observer

        Returns:
            Sync statistics
        """
        from civitas.db.models import Project2025Policy

        stats = {"updated": 0, "new": 0, "unchanged": 0}

        for obj in observer_data:
            # Try to match by content
            existing = self.session.query(Project2025Policy).filter(
                Project2025Policy.agency.ilike(f"%{obj.get('agency', '')}%"),
                Project2025Policy.proposal_text.ilike(f"%{obj.get('title', '')[:50]}%")
            ).first()

            if existing:
                # Update status if observer has newer info
                observer_status = obj.get("status", "").lower()
                if observer_status and observer_status != existing.status:
                    existing.status = self._normalize_status(observer_status)
                    existing.last_checked = datetime.utcnow()
                    stats["updated"] += 1
                else:
                    stats["unchanged"] += 1
            else:
                stats["new"] += 1

        self.session.commit()
        return stats

    def _normalize_status(self, status: str) -> str:
        """Normalize status string to our enum values."""
        status_lower = status.lower().strip()

        if status_lower in ["completed", "done", "implemented"]:
            return self.STATUS_COMPLETED
        elif status_lower in ["in progress", "in_progress", "partial", "ongoing"]:
            return self.STATUS_IN_PROGRESS
        elif status_lower in ["blocked", "stopped", "enjoined"]:
            return self.STATUS_BLOCKED
        elif status_lower in ["reversed", "overturned", "rescinded"]:
            return self.STATUS_REVERSED
        else:
            return self.STATUS_NOT_STARTED
