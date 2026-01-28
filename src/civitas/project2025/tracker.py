"""Track Project 2025 proposals against actual legislation and executive actions.

This is the core counter-initiative component of Civitas.
"""

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from civitas.db.models import ExecutiveOrder, Legislation, Project2025Policy


class Project2025Tracker:
    """Track implementation of Project 2025 proposals.

    Matches proposals against:
    - Federal legislation
    - State legislation
    - Executive orders
    - Agency rules

    Example:
        >>> tracker = Project2025Tracker(session)
        >>> matches = tracker.find_matching_legislation(proposal)
        >>> tracker.generate_report()
    """

    def __init__(self, session: Session):
        """Initialize tracker.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def find_matching_legislation(
        self,
        policy: Project2025Policy,
        threshold: int = 1,
    ) -> list[Legislation]:
        """Find legislation that matches a Project 2025 policy.

        Args:
            policy: The policy to match
            threshold: Minimum keyword matches required

        Returns:
            List of matching Legislation objects
        """
        keywords = json.loads(policy.keywords) if policy.keywords else []
        terms = self._extract_terms(policy, keywords)
        if not terms:
            return []

        # Search legislation for keyword matches
        query = self.session.query(Legislation)

        matches = []
        for leg in query.all():
            score = self._calculate_match_score(leg, terms)
            if score >= threshold:
                matches.append((leg, score))

        # Sort by score and return legislation objects
        matches.sort(key=lambda x: -x[1])
        return [leg for leg, _ in matches[:20]]

    def find_matching_executive_orders(
        self,
        policy: Project2025Policy,
        threshold: int = 1,
    ) -> list[ExecutiveOrder]:
        """Find executive orders matching a policy.

        Args:
            policy: The policy to match
            threshold: Minimum keyword matches required

        Returns:
            List of matching ExecutiveOrder objects
        """
        keywords = json.loads(policy.keywords) if policy.keywords else []
        terms = self._extract_terms(policy, keywords)
        if not terms:
            return []

        query = self.session.query(ExecutiveOrder)

        matches = []
        for eo in query.all():
            score = self._calculate_eo_match_score(eo, terms)
            if score >= threshold:
                matches.append((eo, score))

        matches.sort(key=lambda x: -x[1])
        return [eo for eo, _ in matches[:10]]

    def _calculate_match_score(
        self,
        legislation: Legislation,
        terms: list[str],
    ) -> int:
        """Calculate match score between legislation and keywords."""
        score = 0
        search_text = " ".join(
            [
                legislation.title or "",
                legislation.summary or "",
                legislation.policy_area or "",
                legislation.full_text or "",
            ]
        ).lower()

        for term in terms:
            if term in search_text:
                score += 1

        return score

    def _calculate_eo_match_score(
        self,
        eo: ExecutiveOrder,
        terms: list[str],
    ) -> int:
        """Calculate match score for executive orders."""
        score = 0
        search_text = " ".join(
            [
                eo.title or "",
                eo.abstract or "",
                eo.full_text or "",
            ]
        ).lower()

        for term in terms:
            if term in search_text:
                score += 1

        return score

    def _extract_terms(self, policy: Project2025Policy, keywords: list[str]) -> list[str]:
        """Build a normalized term list for matching."""
        combined = " ".join(
            [
                policy.proposal_text or "",
                policy.proposal_summary or "",
                policy.agency or "",
                " ".join(keywords),
            ]
        ).lower()
        raw_terms = {term.strip(".,;:()[]{}\"'") for term in combined.split()}
        terms = [
            term
            for term in raw_terms
            if len(term) >= 5 and term not in {"shall", "would", "could", "there", "their"}
        ]
        return sorted(terms)

    def update_policy_matches(self, policy_id: int) -> dict:
        """Update matched items for a policy.

        Args:
            policy_id: ID of the Project2025Policy

        Returns:
            Dictionary with match counts
        """
        policy = self.session.query(Project2025Policy).get(policy_id)
        if not policy:
            return {"error": "Policy not found"}

        # Find matches
        legislation = self.find_matching_legislation(policy)
        eos = self.find_matching_executive_orders(policy)

        # Update policy record
        policy.matching_legislation_ids = json.dumps([leg.id for leg in legislation])
        policy.matching_eo_ids = json.dumps([e.id for e in eos])
        policy.last_checked = datetime.now(UTC)

        # Update status based on matches
        if legislation or eos:
            policy.status = "in_progress"

        self.session.commit()

        return {
            "policy_id": policy_id,
            "legislation_matches": len(legislation),
            "eo_matches": len(eos),
        }

    def generate_report(self) -> dict:
        """Generate comprehensive tracking report.

        Returns:
            Dictionary with tracking statistics and alerts
        """
        policies = self.session.query(Project2025Policy).all()

        report = {
            "total_policies": len(policies),
            "by_status": {},
            "by_agency": {},
            "active_implementations": [],
            "recent_matches": [],
        }

        for policy in policies:
            # Count by status
            status = policy.status
            report["by_status"][status] = report["by_status"].get(status, 0) + 1

            # Count by agency
            agency = policy.agency
            report["by_agency"][agency] = report["by_agency"].get(agency, 0) + 1

            # Track active implementations
            if policy.status == "in_progress":
                leg_ids = json.loads(policy.matching_legislation_ids or "[]")
                eo_ids = json.loads(policy.matching_eo_ids or "[]")

                if leg_ids or eo_ids:
                    report["active_implementations"].append(
                        {
                            "policy_id": policy.id,
                            "agency": policy.agency,
                            "proposal_summary": policy.proposal_summary
                            or policy.proposal_text[:100],
                            "legislation_count": len(leg_ids),
                            "eo_count": len(eo_ids),
                        }
                    )

        # Sort by implementation count
        report["active_implementations"].sort(
            key=lambda x: -(x["legislation_count"] + x["eo_count"])
        )

        return report

    def generate_agency_report(self, agency: str) -> dict:
        """Generate report for a specific agency.

        Args:
            agency: Agency name

        Returns:
            Dictionary with agency-specific tracking data
        """
        policies = (
            self.session.query(Project2025Policy).filter(Project2025Policy.agency == agency).all()
        )

        report = {
            "agency": agency,
            "total_policies": len(policies),
            "policies": [],
        }

        for policy in policies:
            leg_ids = json.loads(policy.matching_legislation_ids or "[]")
            eo_ids = json.loads(policy.matching_eo_ids or "[]")

            report["policies"].append(
                {
                    "id": policy.id,
                    "status": policy.status,
                    "action_type": policy.proposal_text[:50] if policy.proposal_text else "",
                    "legislation_matches": len(leg_ids),
                    "eo_matches": len(eo_ids),
                    "page": policy.page_number,
                }
            )

        return report

    def get_high_priority_alerts(self, limit: int = 10) -> list[dict]:
        """Get high-priority implementation alerts.

        Returns policies with recent legislative or executive matches
        that may indicate active implementation.

        Args:
            limit: Maximum alerts to return

        Returns:
            List of alert dictionaries
        """
        policies = (
            self.session.query(Project2025Policy)
            .filter(Project2025Policy.status == "in_progress")
            .order_by(Project2025Policy.last_checked.desc())
            .limit(limit)
            .all()
        )

        alerts = []
        for policy in policies:
            leg_ids = json.loads(policy.matching_legislation_ids or "[]")
            eo_ids = json.loads(policy.matching_eo_ids or "[]")

            # Get actual legislation titles
            matched_legislation = []
            for leg_id in leg_ids[:3]:  # Limit to 3
                leg = self.session.query(Legislation).get(leg_id)
                if leg:
                    matched_legislation.append(
                        {
                            "id": leg.id,
                            "citation": leg.citation,
                            "title": leg.title[:100] if leg.title else "",
                        }
                    )

            alerts.append(
                {
                    "policy_id": policy.id,
                    "agency": policy.agency,
                    "proposal": policy.proposal_summary or policy.proposal_text[:200],
                    "matched_legislation": matched_legislation,
                    "eo_count": len(eo_ids),
                    "last_checked": policy.last_checked.isoformat()
                    if policy.last_checked
                    else None,
                }
            )

        return alerts
