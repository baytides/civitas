"""Generate AI justice profiles for Supreme Court justices."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from civitas.ai.prompts import load_prompt
from civitas.db.models import CourtCase, Justice, JusticeOpinion, JusticeProfile

DEFAULT_OLLAMA_HOST = "https://ollama.baytides.org"
DEFAULT_OLLAMA_MODEL = "llama3.2"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_JUSTICE_NUM_PREDICT = 1200

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
        use_openai: bool | None = None,
    ) -> None:
        self.session = session
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)

        # Auto-detect provider: Groq > OpenAI > Ollama
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        if use_openai is not None:
            self.use_openai = use_openai
            self.use_groq = False
        elif self.groq_api_key:
            self.use_groq = True
            self.use_openai = False
        elif self.openai_api_key:
            self.use_openai = True
            self.use_groq = False
        else:
            self.use_openai = False
            self.use_groq = False

        self.openai_model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        self.groq_model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    def _get_ollama_client(self):
        try:
            import ollama
        except ImportError as exc:
            raise ImportError("Install ollama: pip install ollama") from exc
        return ollama.Client(host=self.ollama_host)

    def _get_openai_client(self):
        """Get OpenAI client."""
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("Install openai: pip install openai") from exc
        return OpenAI()

    def _get_groq_client(self):
        """Get Groq client."""
        try:
            from groq import Groq
        except ImportError as exc:
            raise ImportError("Install groq: pip install groq") from exc
        return Groq(api_key=self.groq_api_key)

    def _build_prompt(self, payload: dict) -> list[dict]:
        # fmt: off
        # Long prompt strings - kept as readable prose for LLM
        default_system = (
            "You are a constitutional law scholar writing comprehensive justice "
            "profiles for an informed public audience. Return JSON only.\n\n"
            "Write in flowing, analytical prose - NOT bullet points. Each section "
            "should read like professional legal scholarship.\n\n"
            "Required JSON structure:\n{\n"
            '  "summary": "A comprehensive 4-6 sentence narrative about this '
            "justice's path to the Supreme Court, their significance in Court "
            "history, and their overall impact on American jurisprudence. "
            'Include context about their confirmation and tenure.",\n\n'
            '  "judicial_philosophy": "A detailed 5-8 sentence analysis of their '
            "interpretive methodology. Discuss their approach to constitutional "
            "interpretation (originalism, living constitutionalism, pragmatism, "
            "etc.), their views on precedent and stare decisis, their treatment "
            "of federal vs. state power, and any distinctive analytical "
            'frameworks they employ. Use specific examples from their record.",\n\n'
            '  "voting_tendencies": "A flowing 4-6 sentence narrative (NOT bullets) '
            "describing their voting patterns. Discuss which justices they most "
            "frequently align with, areas of law where they are most predictable "
            "vs. surprising, and any notable shifts in their jurisprudence over "
            'time. Analyze their position within the Court\'s ideological spectrum.",\n\n'
            '  "statistical_profile": {\n'
            '    "majority_alignment_rate": 0.85,\n'
            '    "dissent_frequency": 0.12,\n'
            '    "opinion_authorship_rate": 0.15,\n'
            '    "ideological_score": "Describe their position on conservative-liberal spectrum",\n'
            '    "key_coalition_partners": "Justices they most frequently join",\n'
            '    "signature_areas": "Areas of law where they have been most influential"\n'
            "  },\n\n"
            '  "methodology": "A clear 3-4 sentence explanation for the general '
            "audience describing how this profile was generated. Explain that the "
            "analysis is based on statistical analysis of published Supreme Court "
            "opinions, voting records, and case outcomes. Note that AI was used to "
            "synthesize patterns from court records and that this represents "
            'analytical observations, not predictions of future behavior."\n'
            "}\n\n"
            "CRITICAL RULES:\n"
            "- Write substantive narratives, not lists or bullet points\n"
            "- voting_tendencies MUST be prose paragraphs, not an array\n"
            "- Focus on legal analysis, not political characterization\n"
            "- Be specific about constitutional doctrines and legal frameworks\n"
            "- The methodology should be written for a general audience\n"
            "- Do NOT include notable_opinions - that data comes from our database\n"
            "- No markdown formatting"
        )
        # fmt: on

        system = load_prompt(
            path_env="BAYTIDES_JUSTICE_PROFILE_PROMPT_PATH",
            inline_env="BAYTIDES_JUSTICE_PROFILE_PROMPT",
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
            self.session.query(
                CourtCase.case_name,
                CourtCase.citation,
                CourtCase.decision_date,
                CourtCase.case_analysis,
            )
            .join(JusticeOpinion, JusticeOpinion.court_case_id == CourtCase.id)
            .filter(JusticeOpinion.justice_id == justice_id)
            .order_by(CourtCase.decision_date.desc().nullslast())
            .limit(10)
            .all()
        )

        # Extract ideological patterns from case analyses
        ideological_counts = {"conservative": 0, "liberal": 0, "mixed": 0, "technical": 0}
        categories_seen = {}
        for row in recent_cases:
            if row[3]:  # case_analysis exists
                try:
                    analysis = json.loads(row[3])
                    lean = analysis.get("ideological_lean", "").lower()
                    if lean in ideological_counts:
                        ideological_counts[lean] += 1
                    for cat in analysis.get("categories", []):
                        categories_seen[cat] = categories_seen.get(cat, 0) + 1
                except (json.JSONDecodeError, TypeError):
                    pass

        # Get top categories this justice has ruled on
        top_categories = sorted(categories_seen.items(), key=lambda x: -x[1])[:5]

        return {
            "total_opinions": total,
            "majority_opinions": majority,
            "dissent_opinions": dissent,
            "concurrence_opinions": concurrence,
            "majority_rate": round(majority_rate, 3),
            "dissent_rate": round(dissent_rate, 3),
            "concurrence_rate": round(concurrence_rate, 3),
            "ideological_breakdown": ideological_counts,
            "top_legal_areas": [cat for cat, _ in top_categories],
            "recent_cases": [
                {
                    "case_name": row[0],
                    "citation": row[1],
                    "decision_date": str(row[2]) if row[2] else None,
                }
                for row in recent_cases[:5]
            ],
        }

    def _ollama_generate(self, messages: list[dict]) -> str:
        """Generate using Ollama."""
        client = self._get_ollama_client()
        num_predict = int(
            os.getenv("JUSTICE_PROFILE_NUM_PREDICT", str(DEFAULT_JUSTICE_NUM_PREDICT))
        )
        response = client.chat(
            model=self.ollama_model,
            messages=messages,
            format="json",
            options={"num_predict": num_predict},
        )
        return response.get("message", {}).get("content", "")

    def _openai_generate(self, messages: list[dict]) -> str:
        """Generate using OpenAI."""
        client = self._get_openai_client()
        response = client.chat.completions.create(
            model=self.openai_model,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    def _groq_generate(self, messages: list[dict]) -> str:
        """Generate using Groq (fast, free tier)."""
        client = self._get_groq_client()
        response = client.chat.completions.create(
            model=self.groq_model,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    def _store_profile(
        self, justice_id: int, parsed: dict, real_cases: list[dict], model_used: str | None = None
    ) -> JusticeProfile:
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
        # Use REAL case data from database, not LLM-generated (which hallucinates)
        profile.notable_opinions = json.dumps(real_cases, ensure_ascii=True) if real_cases else None
        statistical = parsed.get("statistical_profile")
        if statistical is not None:
            profile.statistical_profile = json.dumps(statistical, ensure_ascii=True)
        else:
            profile.statistical_profile = None
        profile.methodology = to_text(parsed.get("methodology"))
        profile.disclaimer = DISCLAIMER_TEXT
        profile.ai_model_version = model_used or self.ollama_model
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

        messages = self._build_prompt(payload)

        # Use Groq > OpenAI > Ollama based on configuration
        if self.use_groq:
            content = self._groq_generate(messages)
            model_used = self.groq_model
        elif self.use_openai:
            content = self._openai_generate(messages)
            model_used = self.openai_model
        else:
            content = self._ollama_generate(messages)
            model_used = self.ollama_model

        parsed = self._parse_response(content)
        if not parsed:
            return False

        # Pass real case data from database (not LLM hallucinations)
        real_cases = stats.get("recent_cases", [])
        self._store_profile(justice.id, parsed, real_cases, model_used)
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
