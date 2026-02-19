"""Resistance recommendation engine.

Generates actionable recommendations based on:
- Current political control (Tier 1: Courts/States)
- Potential congressional control (Tier 2: 2026+)
- Potential presidential control (Tier 3: 2028+)
"""

import json
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from civitas.ai.prompts import load_prompt

DEFAULT_OLLAMA_HOST = "https://ollama.baytides.org"
DEFAULT_OLLAMA_MODEL = "llama3.2"


class ResistanceRecommender:
    """Generates tiered resistance recommendations.

    Example:
        >>> recommender = ResistanceRecommender(session)
        >>> recs = recommender.generate_recommendations(policy_id=42)
        >>> for rec in recs['tier_1']:
        ...     print(f"{rec['action_type']}: {rec['title']}")
    """

    TIERS = {
        "tier_1_immediate": {
            "name": "Immediate Actions",
            "description": "Actions available now regardless of political control",
            "tools": ["Courts", "10th Amendment", "State Governments", "FOIA", "Public Comment"],
            "action_types": [
                "legal_challenge",
                "state_sanctuary",
                "state_lawsuit",
                "foia_request",
                "public_comment",
                "whistleblower_support",
                "organizing",
            ],
        },
        "tier_2_congressional": {
            "name": "Congressional Actions (2027+)",
            "description": "Actions if Democrats win House/Senate in 2026",
            "tools": ["Oversight", "Appropriations", "Legislation", "Confirmation"],
            "action_types": [
                "congressional_investigation",
                "defund_provision",
                "statutory_reversal",
                "codification",
                "confirmation_blocking",
                "public_hearing",
            ],
        },
        "tier_3_presidential": {
            "name": "Presidential Actions (2029+)",
            "description": "Actions if Democrat wins presidency in 2028",
            "tools": ["Executive Orders", "Agency Actions", "Personnel", "Pardons"],
            "action_types": [
                "executive_reversal",
                "regulatory_restoration",
                "personnel_change",
                "structural_reform",
                "constitutional_amendment",
            ],
        },
    }

    def __init__(
        self,
        session: Session,
        ollama_host: str | None = None,
        ollama_model: str | None = None,
    ):
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

    def generate_recommendations(
        self,
        policy_id: int,
        include_tiers: list[str] | None = None,
    ) -> dict:
        """Generate tiered resistance recommendations for a policy.

        Args:
            policy_id: Database ID of the P2025 policy
            include_tiers: Which tiers to generate (default: all)

        Returns:
            Dict with recommendations organized by tier
        """
        from civitas.db.models import (
            Project2025Policy,
        )

        # Get the policy
        policy = self.session.query(Project2025Policy).filter_by(id=policy_id).first()
        if not policy:
            return {"error": f"Policy {policy_id} not found"}

        tiers = include_tiers or list(self.TIERS.keys())
        results = {}

        for tier in tiers:
            tier_info = self.TIERS.get(tier)
            if not tier_info:
                continue

            # Generate recommendations for this tier
            recs = self._generate_tier_recommendations(policy, tier, tier_info)
            results[tier] = recs

            # Store in database
            for rec in recs:
                self._store_recommendation(policy_id, tier, rec)

        return {
            "policy_id": policy_id,
            "policy_summary": policy.proposal_text[:200],
            "generated_at": datetime.now(UTC).isoformat(),
            "recommendations": results,
        }

    def _generate_tier_recommendations(
        self,
        policy,
        tier: str,
        tier_info: dict,
    ) -> list[dict]:
        """Generate recommendations for a specific tier."""
        client = self._get_ollama_client()
        num_predict = int(os.getenv("RESISTANCE_RECOMMEND_NUM_PREDICT", "400"))
        temperature = float(os.getenv("RESISTANCE_RECOMMEND_TEMPERATURE", "0.3"))

        default_system_prompt = f"""You are a legal and political strategist generating actionable recommendations for resisting a policy.

TIER: {tier_info["name"]}
DESCRIPTION: {tier_info["description"]}
AVAILABLE TOOLS: {", ".join(tier_info["tools"])}
ACTION TYPES: {", ".join(tier_info["action_types"])}

Return ONLY JSON. Do not include any markdown or prose.
Output must be a JSON array of objects. Each object must contain:
- action_type: One of the allowed action types
- title: Brief title
- description: Detailed description of the action
- rationale: Why this would be effective
- legal_basis: Constitutional or statutory basis
- likelihood_of_success: high/medium/low
- time_sensitivity: urgent/soon/long_term
- resources_required: low/medium/high
- action_steps: Numbered list of concrete steps
- model_text: Draft language if applicable (complaint, legislation, etc.)

Respond in JSON format with an array of recommendations."""
        system_prompt = load_prompt(
            path_env="BAYTIDES_RESISTANCE_RECOMMEND_PROMPT_PATH",
            inline_env="BAYTIDES_RESISTANCE_RECOMMEND_PROMPT",
            fallback=default_system_prompt,
        )

        user_prompt = f"""Generate {tier_info["name"]} recommendations for this P2025 policy:

AGENCY: {policy.agency}
SECTION: {policy.section}
POLICY TEXT: {policy.proposal_text}

STATUS: {policy.status}
KEYWORDS: {policy.keywords}

Generate 2-4 specific, actionable recommendations for this tier. Focus on legal viability and practical implementation."""

        try:
            response = client.chat(
                model=self.ollama_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                format="json",
                options={"temperature": temperature, "num_predict": num_predict},
            )

            content = response["message"]["content"]
            try:
                recs = json.loads(content)
                if isinstance(recs, dict) and "recommendations" in recs:
                    recs = recs["recommendations"]
                elif not isinstance(recs, list):
                    recs = [recs]
            except json.JSONDecodeError:
                # Attempt a self-repair pass for malformed JSON
                repair_prompt = (
                    "Fix the following content into valid JSON. "
                    "Return ONLY a JSON array of recommendation objects. "
                    "Each object must include action_type, title, description, "
                    "rationale, legal_basis, likelihood_of_success, time_sensitivity, "
                    "resources_required, action_steps, model_text.\n\nCONTENT:\n"
                    f"{content}"
                )
                try:
                    repair = client.chat(
                        model=self.ollama_model,
                        messages=[{"role": "user", "content": repair_prompt}],
                        format="json",
                        options={"temperature": 0.0, "num_predict": 300},
                    )
                    fixed = repair["message"]["content"]
                    recs = json.loads(fixed)
                    if isinstance(recs, dict) and "recommendations" in recs:
                        recs = recs["recommendations"]
                    elif not isinstance(recs, list):
                        recs = [recs]
                except Exception:
                    # Fallback to a single, minimally structured recommendation
                    recs = [
                        {
                            "action_type": "unknown",
                            "title": "AI-generated recommendation (unstructured)",
                            "description": content.strip()[:2000],
                            "rationale": "",
                            "legal_basis": None,
                            "likelihood_of_success": "medium",
                            "time_sensitivity": "soon",
                            "resources_required": "medium",
                            "action_steps": [],
                        }
                    ]

            return recs

        except Exception as e:
            return [{"error": str(e)}]

    def _store_recommendation(self, policy_id: int, tier: str, rec: dict) -> None:
        """Store a recommendation in the database."""
        import time

        from sqlalchemy.exc import OperationalError

        from civitas.db.models import ResistanceRecommendation

        if rec.get("error") or rec.get("parse_error"):
            return

        def _jsonify(value):
            if value is None:
                return None
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=True)
            return value

        db_rec = ResistanceRecommendation(
            p2025_policy_id=policy_id,
            tier=tier,
            action_type=rec.get("action_type", "unknown"),
            title=rec.get("title", "Untitled")[:500],
            description=rec.get("description", ""),
            rationale=rec.get("rationale", ""),
            legal_basis=_jsonify(rec.get("legal_basis")),
            likelihood_of_success=str(rec.get("likelihood_of_success", "medium")).lower(),
            time_sensitivity=str(rec.get("time_sensitivity", "soon")).lower(),
            resources_required=str(rec.get("resources_required", "medium")).lower()
            if not isinstance(rec.get("resources_required"), (dict, list))
            else "medium",
            action_steps=_jsonify(rec.get("action_steps", [])),
            model_complaint=_jsonify(rec.get("model_text"))
            if "challenge" in rec.get("action_type", "")
            else None,
            model_legislation=_jsonify(rec.get("model_text"))
            if "legislation" in rec.get("action_type", "")
            else None,
            ai_model_version=self.ollama_model,
            ai_confidence_score=rec.get("confidence", 0.7),
        )
        self.session.add(db_rec)
        for attempt in range(3):
            try:
                self.session.commit()
                break
            except OperationalError as exc:
                if "database is locked" not in str(exc).lower() or attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))

    def get_urgent_actions(self, category: str | None = None) -> list[dict]:
        """Get urgent Tier 1 actions across all policies.

        Args:
            category: Filter by category (immigration, environment, etc.)

        Returns:
            List of urgent recommendations sorted by priority
        """
        from civitas.db.models import Project2025Policy, ResistanceRecommendation

        query = self.session.query(ResistanceRecommendation).filter(
            ResistanceRecommendation.tier == "tier_1_immediate",
            ResistanceRecommendation.time_sensitivity == "urgent",
        )

        if category:
            query = query.join(Project2025Policy).filter(
                Project2025Policy.agency.ilike(f"%{category}%")
            )

        recs = query.order_by(ResistanceRecommendation.likelihood_of_success.desc()).limit(20).all()

        return [
            {
                "id": rec.id,
                "policy_id": rec.p2025_policy_id,
                "action_type": rec.action_type,
                "title": rec.title,
                "description": rec.description,
                "legal_basis": rec.legal_basis,
                "likelihood": rec.likelihood_of_success,
            }
            for rec in recs
        ]

    def get_model_documents(self, action_type: str) -> list[dict]:
        """Get model legal documents by type.

        Args:
            action_type: Type of action (legal_challenge, state_legislation, etc.)

        Returns:
            List of model documents
        """
        from civitas.db.models import ResistanceRecommendation

        recs = (
            self.session.query(ResistanceRecommendation)
            .filter(
                ResistanceRecommendation.action_type == action_type,
                ResistanceRecommendation.model_complaint.isnot(None)
                | ResistanceRecommendation.model_legislation.isnot(None),
            )
            .limit(20)
            .all()
        )

        return [
            {
                "id": rec.id,
                "policy_id": rec.p2025_policy_id,
                "title": rec.title,
                "model_complaint": rec.model_complaint,
                "model_legislation": rec.model_legislation,
            }
            for rec in recs
        ]

    def generate_all_recommendations(
        self,
        category: str | None = None,
        limit: int = 100,
    ) -> dict:
        """Generate recommendations for multiple policies.

        Args:
            category: Filter by category
            limit: Maximum policies to process

        Returns:
            Summary of generated recommendations
        """
        from civitas.db.models import Project2025Policy

        query = self.session.query(Project2025Policy)
        if category:
            query = query.filter(Project2025Policy.agency.ilike(f"%{category}%"))

        policies = query.limit(limit).all()

        stats = {
            "processed": 0,
            "tier_1_count": 0,
            "tier_2_count": 0,
            "tier_3_count": 0,
            "errors": 0,
        }

        for policy in policies:
            try:
                results = self.generate_recommendations(policy.id)

                if "recommendations" in results:
                    stats["tier_1_count"] += len(
                        results["recommendations"].get("tier_1_immediate", [])
                    )
                    stats["tier_2_count"] += len(
                        results["recommendations"].get("tier_2_congressional", [])
                    )
                    stats["tier_3_count"] += len(
                        results["recommendations"].get("tier_3_presidential", [])
                    )

                stats["processed"] += 1

            except Exception:
                stats["errors"] += 1

        return stats
