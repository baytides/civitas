"""AI-powered Supreme Court case analysis.

Analyzes SCOTUS cases to extract:
- Legal issues and constitutional questions
- Justice voting patterns and coalitions
- Impact on precedent and legal doctrine
- Ideological indicators for justice profiling
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from civitas.db.models import CourtCase, JusticeOpinion

DEFAULT_OLLAMA_HOST = "https://ollama.baytides.org"
DEFAULT_OLLAMA_MODEL = "llama3.2"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

# Groq free tier limits
GROQ_RPM_LIMIT = 30  # requests per minute
GROQ_TPD_LIMIT = 500_000  # tokens per day (approximate)


class CaseAnalyzer:
    """Analyzes Supreme Court cases for legal significance and voting patterns."""

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

        # Rate limiting tracking for Groq
        self._groq_requests_this_minute = 0
        self._groq_minute_start = time.time()
        self._groq_tokens_today = 0
        self._groq_rate_limited = False

    def _get_ollama_client(self):
        try:
            import ollama
        except ImportError as exc:
            raise ImportError("Install ollama: pip install ollama") from exc
        return ollama.Client(host=self.ollama_host)

    def _get_openai_client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("Install openai: pip install openai") from exc
        return OpenAI()

    def _get_groq_client(self):
        try:
            from groq import Groq
        except ImportError as exc:
            raise ImportError("Install groq: pip install groq") from exc
        return Groq(api_key=self.groq_api_key)

    def _build_system_prompt(self) -> str:
        # fmt: off
        return (
            "You are a constitutional law expert analyzing Supreme Court cases. "
            "Respond with ONLY valid JSON.\n\n"
            "You MUST respond with this EXACT JSON structure:\n"
            "{\n"
            '  "legal_issues": ["Primary legal question 1", "Legal question 2"],\n'
            '  "constitutional_provisions": ["Amendment/Article involved"],\n'
            '  "legal_doctrine": "The legal doctrine or test applied",\n'
            '  "outcome_summary": "One sentence summary of the ruling",\n'
            '  "precedent_impact": "How this case affects existing law",\n'
            '  "ideological_lean": "conservative/liberal/mixed/technical",\n'
            '  "significance_score": 75,\n'
            '  "categories": ["civil_rights", "criminal_procedure", "federalism", '
            '"first_amendment", "due_process", "equal_protection", "executive_power", '
            '"separation_of_powers", "commerce_clause", "statutory_interpretation"],\n'
            '  "majority_reasoning": "Brief summary of majority\'s legal reasoning",\n'
            '  "dissent_reasoning": "Brief summary of dissent\'s reasoning (if any)"\n'
            "}\n\n"
            "RULES:\n"
            "- Respond with ONLY the JSON object, no other text\n"
            "- categories should only include relevant ones from the provided list\n"
            "- significance_score: 1-100 based on legal/historical importance\n"
            "- ideological_lean: based on outcome and reasoning, not politics\n"
            "- Be specific about constitutional provisions and legal doctrines"
        )
        # fmt: on

    def _build_user_prompt(self, case: CourtCase) -> str:
        # Get justice opinions for this case
        opinions = (
            self.session.query(JusticeOpinion).filter(JusticeOpinion.court_case_id == case.id).all()
        )

        majority_authors = [o.author_name for o in opinions if o.opinion_type == "majority"]
        dissent_authors = [o.author_name for o in opinions if o.opinion_type == "dissent"]
        concur_authors = [o.author_name for o in opinions if o.opinion_type == "concurrence"]

        prompt = f"""Analyze this Supreme Court case:

CASE: {case.case_name}
CITATION: {case.citation}
DECIDED: {case.decision_date}
VOTE: {case.vote_majority or "?"}-{case.vote_dissent or "?"}

MAJORITY AUTHOR: {case.majority_author or ", ".join(majority_authors) or "Unknown"}
DISSENTING: {", ".join(dissent_authors) if dissent_authors else "None"}
CONCURRING: {", ".join(concur_authors) if concur_authors else "None"}

HOLDING:
{(case.holding or "Not available")[:2000]}

SYLLABUS:
{(case.syllabus or "Not available")[:1500]}

Respond with the JSON structure specified."""
        return prompt

    def _ollama_analyze(self, system_prompt: str, user_prompt: str) -> str:
        client = self._get_ollama_client()
        response = client.chat(
            model=self.ollama_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            format="json",
            options={"num_predict": 1500, "temperature": 0.2},
        )
        return response.get("message", {}).get("content", "")

    def _openai_analyze(self, system_prompt: str, user_prompt: str) -> str:
        client = self._get_openai_client()
        response = client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    def _check_groq_rate_limit(self) -> bool:
        """Check if we're within Groq rate limits. Returns True if OK to proceed."""
        now = time.time()

        # Reset minute counter if a minute has passed
        if now - self._groq_minute_start >= 60:
            self._groq_requests_this_minute = 0
            self._groq_minute_start = now

        # Check if we've hit rate limits
        if self._groq_requests_this_minute >= GROQ_RPM_LIMIT:
            return False

        if self._groq_tokens_today >= GROQ_TPD_LIMIT:
            self._groq_rate_limited = True
            return False

        return True

    def _groq_analyze(self, system_prompt: str, user_prompt: str) -> str:
        client = self._get_groq_client()

        try:
            response = client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            # Track usage
            self._groq_requests_this_minute += 1
            if hasattr(response, "usage") and response.usage:
                self._groq_tokens_today += response.usage.total_tokens

            return response.choices[0].message.content

        except Exception as e:
            # Check for rate limit error (429)
            if "429" in str(e) or "rate" in str(e).lower():
                self._groq_rate_limited = True
                raise
            raise

    def _parse_response(self, text: str) -> dict | None:
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    return None
            return None

    def analyze_case(self, case: CourtCase, force: bool = False) -> dict | None:
        """Analyze a single court case.

        Args:
            case: CourtCase to analyze
            force: Regenerate even if analysis exists

        Returns:
            Analysis dict or None if failed
        """
        # Skip if already analyzed (unless force)
        if case.case_analysis and not force:
            try:
                return json.loads(case.case_analysis)
            except json.JSONDecodeError:
                pass  # Regenerate if corrupted

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(case)

        # Use appropriate provider with fallback
        content = None
        model_used = None

        # Try Groq first if available and not rate limited
        if self.use_groq and not self._groq_rate_limited and self._check_groq_rate_limit():
            try:
                content = self._groq_analyze(system_prompt, user_prompt)
                model_used = self.groq_model
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    print("  Groq rate limited, falling back to Ollama...")
                    self._groq_rate_limited = True
                else:
                    raise

        # Fall back to OpenAI if Groq failed/unavailable
        if content is None and self.use_openai:
            content = self._openai_analyze(system_prompt, user_prompt)
            model_used = self.openai_model

        # Fall back to Ollama as last resort
        if content is None:
            content = self._ollama_analyze(system_prompt, user_prompt)
            model_used = self.ollama_model

        analysis = self._parse_response(content)
        if not analysis:
            return None

        # Add metadata
        analysis["case_id"] = case.id
        analysis["case_name"] = case.case_name
        analysis["citation"] = case.citation

        # Store in database
        case.case_analysis = json.dumps(analysis, ensure_ascii=True)
        case.analysis_generated_at = datetime.now(UTC)
        case.analysis_model = model_used

        return analysis

    def analyze_batch(
        self,
        limit: int = 50,
        force: bool = False,
        court_level: str = "scotus",
        verbose: bool = True,
    ) -> tuple[int, int]:
        """Analyze multiple cases.

        Args:
            limit: Max cases to process
            force: Regenerate existing analyses
            court_level: Filter by court level (scotus, circuit, district)
            verbose: Print progress updates

        Returns:
            Tuple of (successful, failed) counts
        """
        query = self.session.query(CourtCase).filter(CourtCase.court_level == court_level)

        if not force:
            query = query.filter(CourtCase.case_analysis.is_(None))

        cases = query.order_by(CourtCase.decision_date.desc().nullslast()).limit(limit).all()

        successful = 0
        failed = 0
        groq_count = 0
        ollama_count = 0

        for i, case in enumerate(cases, 1):
            try:
                # Show which provider we're using
                if verbose:
                    using_groq = self.use_groq and not self._groq_rate_limited
                    provider = "Groq" if using_groq else "Ollama"
                    print(f"  [{i}/{len(cases)}] {case.case_name[:50]}... ({provider})")

                result = self.analyze_case(case, force=force)
                if result:
                    self.session.commit()
                    successful += 1

                    # Track which provider was used
                    if result.get("case_id") and case.analysis_model:
                        model = case.analysis_model.lower()
                        if "groq" in model or "llama-3.3" in model:
                            groq_count += 1
                        else:
                            ollama_count += 1
                else:
                    failed += 1
                    if verbose:
                        print("    Failed to parse response")

            except Exception as e:
                print(f"    Error: {e}")
                failed += 1
                self.session.rollback()

        if verbose:
            print(f"\n  Provider breakdown: Groq={groq_count}, Ollama={ollama_count}")

        return successful, failed

    def get_case_stats(self) -> dict:
        """Get statistics on case analysis progress."""
        total = self.session.query(CourtCase).filter(CourtCase.court_level == "scotus").count()

        analyzed = (
            self.session.query(CourtCase)
            .filter(CourtCase.court_level == "scotus", CourtCase.case_analysis.isnot(None))
            .count()
        )

        return {
            "total_scotus_cases": total,
            "analyzed": analyzed,
            "remaining": total - analyzed,
            "percent_complete": round(analyzed / total * 100, 1) if total else 0,
        }
