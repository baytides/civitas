"""Generate AI justice profiles for Supreme Court justices."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from civitas.ai.prompts import load_prompt
from civitas.db.models import CourtCase, Justice, JusticeOpinion, JusticeProfile

DEFAULT_OLLAMA_HOST = "http://20.98.70.48:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"

DISCLAIMER_TEXT = (
    "We do not have any insight into the respective justice's opinion on any current or "
    "prospective cases in front of them, and all analysis is based on a profile generated "
    "using prior court records and opinions by the justices to create a purely statistical "
    "analysis of the respective justice. None of the statistics produced here should be "
    "taken as actual outcomes."
)


class JusticeProfileGenerator:
    """Generate and store justice profile analysis."""

    def __init__(
        self,
        session: Session,
        ollama_host: str | None = None,
        ollama_model: str | None = None,
    ) -> None:
        self.session = session
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)

    def _get_ollama_client(self):
        try:
            import ollama
        except ImportError as exc:
            raise ImportError("Install ollama: pip install ollama") from exc
        return ollama.Client(host=self.ollama_host)

    def _build_prompt(self, payload: dict) -> list[dict]:
        default_system = (
            "You are a legal analyst. Return JSON only with keys: "
            "summary, judicial_philosophy, voting_tendencies, notable_opinions, "
            "statistical_profile, methodology. "
            "summary: 3-4 sentences. judicial_philosophy: 3-4 sentences. "
            "voting_tendencies: 4-7 bullet phrases. notable_opinions: 3-6 items. "
            "statistical_profile: JSON object with 4-6 key metrics. "
            "methodology: 2-3 sentences. No markdown, no extra keys."
        )
        system = load_prompt(
            path_env="CARL_JUSTICE_PROFILE_PROMPT_PATH",
            inline_env="CARL_JUSTICE_PROFILE_PROMPT",
            fallback=default_system,
        )
        user = f"Justice profile input: {json.dumps(payload, ensure_ascii=True)}"
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _parse_response(self, text: str) -> dict | None:
        if not text:
            return None
        raw = text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        snippet = raw[start : end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            return None

    def _compute_stats(self, justice_id: int) -> dict:
        total = (
            self.session.query(JusticeOpinion)
            .filter(JusticeOpinion.justice_id == justice_id)
            .count()
        )
        majority = (
            self.session.query(JusticeOpinion)
            .filter(
                JusticeOpinion.justice_id == justice_id,
                JusticeOpinion.opinion_type == "majority",
            )
            .count()
        )
        dissent = (
            self.session.query(JusticeOpinion)
            .filter(
                JusticeOpinion.justice_id == justice_id,
                JusticeOpinion.opinion_type == "dissent",
            )
            .count()
        )
        concurrence = (
            self.session.query(JusticeOpinion)
            .filter(
                JusticeOpinion.justice_id == justice_id,
                JusticeOpinion.opinion_type == "concurrence",
            )
            .count()
        )

        majority_rate = (majority / total) if total else 0.0
        dissent_rate = (dissent / total) if total else 0.0
        concurrence_rate = (concurrence / total) if total else 0.0

        recent_cases = (
            self.session.query(CourtCase.case_name, CourtCase.citation, CourtCase.decision_date)
            .join(JusticeOpinion, JusticeOpinion.court_case_id == CourtCase.id)
            .filter(JusticeOpinion.justice_id == justice_id)
            .order_by(CourtCase.decision_date.desc().nullslast())
            .limit(5)
            .all()
        )

        return {
            "total_opinions": total,
            "majority_opinions": majority,
            "dissent_opinions": dissent,
            "concurrence_opinions": concurrence,
            "majority_rate": round(majority_rate, 3),
            "dissent_rate": round(dissent_rate, 3),
            "concurrence_rate": round(concurrence_rate, 3),
            "recent_cases": [
                {
                    "case_name": row[0],
                    "citation": row[1],
                    "decision_date": str(row[2]) if row[2] else None,
                }
                for row in recent_cases
            ],
        }

    def _store_profile(self, justice_id: int, parsed: dict) -> JusticeProfile:
        def to_json(value) -> str | None:
            if value is None:
                return None
            if isinstance(value, (list, dict)):
                return json.dumps(value, ensure_ascii=True)
            return json.dumps([value], ensure_ascii=True) if isinstance(value, str) else None

        def to_text(value) -> str | None:
            if value is None:
                return None
            if isinstance(value, str):
                return value
            return json.dumps(value, ensure_ascii=True)

        profile = (
            self.session.query(JusticeProfile)
            .filter(JusticeProfile.justice_id == justice_id)
            .first()
        )
        if profile is None:
            profile = JusticeProfile(justice_id=justice_id)
            self.session.add(profile)

        profile.profile_summary = to_text(parsed.get("summary"))
        profile.judicial_philosophy = to_text(parsed.get("judicial_philosophy"))
        profile.voting_tendencies = to_json(parsed.get("voting_tendencies"))
        profile.notable_opinions = to_json(parsed.get("notable_opinions"))
        statistical = parsed.get("statistical_profile")
        if statistical is not None:
            profile.statistical_profile = json.dumps(statistical, ensure_ascii=True)
        else:
            profile.statistical_profile = None
        profile.methodology = to_text(parsed.get("methodology"))
        profile.disclaimer = DISCLAIMER_TEXT
        profile.ai_model_version = self.ollama_model
        profile.generated_at = datetime.now(UTC)
        profile.updated_at = datetime.now(UTC)
        return profile

    def generate_for_justice(self, justice: Justice, force: bool = False) -> bool:
        existing = (
            self.session.query(JusticeProfile)
            .filter(JusticeProfile.justice_id == justice.id)
            .first()
        )
        if existing and not force:
            return False

        stats = self._compute_stats(justice.id)
        payload = {
            "name": justice.name,
            "role": justice.role,
            "is_active": justice.is_active,
            "stats": stats,
            "disclaimer": DISCLAIMER_TEXT,
        }

        client = self._get_ollama_client()
        messages = self._build_prompt(payload)
        response = client.chat(model=self.ollama_model, messages=messages)
        content = response.get("message", {}).get("content", "")
        parsed = self._parse_response(content)
        if not parsed:
            return False

        self._store_profile(justice.id, parsed)
        return True

    def generate_batch(self, limit: int = 20, force: bool = False) -> int:
        justices = (
            self.session.query(Justice)
            .order_by(Justice.is_active.desc(), Justice.last_name.asc())
            .limit(limit)
            .all()
        )
        created = 0
        for justice in justices:
            if self.generate_for_justice(justice, force=force):
                self.session.commit()
                created += 1
        return created
