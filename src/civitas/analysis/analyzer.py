"""AI-powered legislation analyzer using Ollama/Llama.

This module sends legislation text to Ollama for:
1. Category classification
2. Threat assessment (anti-democratic indicators)
3. Summary generation
4. Action recommendations
"""

import json
import os
from dataclasses import dataclass
from typing import Optional

import httpx

from .categories import CATEGORIES, LawCategory, get_category_by_slug
from .actions import get_actions_for_category, get_urgent_actions, ResistanceAction


@dataclass
class AnalysisResult:
    """Result of AI analysis on legislation."""

    # Classification
    primary_category: str
    secondary_categories: list[str]
    confidence: float  # 0.0 - 1.0

    # Threat assessment
    threat_level: str  # "none", "low", "medium", "high", "critical"
    threat_indicators: list[str]
    p2025_alignment: Optional[str]  # Which P2025 objective it aligns with, if any

    # Content analysis
    summary: str
    key_provisions: list[str]
    affected_groups: list[str]

    # Actions
    recommended_actions: list[dict]
    urgency: str  # "low", "medium", "high", "immediate"


class LegislationAnalyzer:
    """Analyze legislation using Ollama/Llama AI.

    Uses Azure-hosted Ollama for AI processing:
    - Endpoint: http://20.98.70.48:11434 (or OLLAMA_HOST env var)
    - Model: llama3.2 (or OLLAMA_MODEL env var)
    """

    def __init__(
        self,
        ollama_host: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
    ):
        self.ollama_host = ollama_host or os.getenv(
            "OLLAMA_HOST", "http://20.98.70.48:11434"
        )
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

        # Build category reference for prompts
        self._category_reference = self._build_category_reference()

    def _build_category_reference(self) -> str:
        """Build a reference string of all categories for the AI."""
        lines = []
        for cat in CATEGORIES:
            keywords_str = ", ".join(cat.keywords[:10])
            lines.append(f"- {cat.slug}: {cat.name} - {cat.description}")
            lines.append(f"  Keywords: {keywords_str}")
            if cat.p2025_related:
                lines.append(f"  P2025-related: Yes")
                if cat.threat_keywords:
                    lines.append(f"  Threat keywords: {', '.join(cat.threat_keywords[:5])}")
        return "\n".join(lines)

    def analyze(
        self,
        title: str,
        text: str,
        jurisdiction: str = "unknown",
        bill_number: Optional[str] = None,
    ) -> AnalysisResult:
        """Analyze legislation and return structured result.

        Args:
            title: Bill title
            text: Full text or summary of the legislation
            jurisdiction: State or "federal"
            bill_number: Optional bill number (e.g., "HB 1234")

        Returns:
            AnalysisResult with classification, threat assessment, and actions
        """
        prompt = self._build_analysis_prompt(title, text, jurisdiction, bill_number)
        response = self._query_ollama(prompt)
        return self._parse_response(response)

    def classify_only(self, title: str, summary: str) -> tuple[str, list[str], float]:
        """Quick classification without full analysis.

        Returns:
            Tuple of (primary_category, secondary_categories, confidence)
        """
        prompt = f"""Classify this legislation into one of these categories:

{self._category_reference}

LEGISLATION:
Title: {title}
Summary: {summary}

Respond with ONLY a JSON object in this exact format:
{{"primary": "category_slug", "secondary": ["slug1", "slug2"], "confidence": 0.85}}

Use category slugs exactly as shown above."""

        response = self._query_ollama(prompt)

        try:
            # Extract JSON from response
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str)
            return (
                data.get("primary", "government"),
                data.get("secondary", []),
                data.get("confidence", 0.5),
            )
        except (json.JSONDecodeError, IndexError):
            # Fallback: try to extract category from text
            for cat in CATEGORIES:
                if cat.slug in response.lower() or cat.name.lower() in response.lower():
                    return (cat.slug, [], 0.3)
            return ("government", [], 0.1)

    def assess_threat(self, title: str, text: str, category_slug: str) -> dict:
        """Assess threat level of legislation.

        Returns dict with:
            - level: "none", "low", "medium", "high", "critical"
            - indicators: list of concerning elements
            - p2025_alignment: description if aligns with P2025
        """
        category = get_category_by_slug(category_slug)
        threat_keywords = category.threat_keywords if category else []
        resistance_keywords = category.resistance_keywords if category else []

        prompt = f"""Analyze this legislation for potential threats to democratic institutions,
civil rights, or vulnerable communities.

LEGISLATION:
Title: {title}
Text excerpt: {text[:3000]}

CATEGORY: {category_slug}
KNOWN THREAT INDICATORS FOR THIS CATEGORY: {', '.join(threat_keywords)}
KNOWN PROTECTIVE INDICATORS: {', '.join(resistance_keywords)}

Assess the threat level. Consider:
1. Does it restrict rights or access to services?
2. Does it concentrate power or reduce oversight?
3. Does it target specific groups?
4. Does it align with Project 2025 objectives?

Respond with ONLY a JSON object:
{{
  "level": "none|low|medium|high|critical",
  "indicators": ["specific concern 1", "specific concern 2"],
  "p2025_alignment": "description if aligns with P2025, or null",
  "protective": false
}}

Set "protective" to true if this is PROTECTIVE legislation (expands rights/access)."""

        response = self._query_ollama(prompt)

        try:
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str)
            return {
                "level": data.get("level", "low"),
                "indicators": data.get("indicators", []),
                "p2025_alignment": data.get("p2025_alignment"),
                "protective": data.get("protective", False),
            }
        except (json.JSONDecodeError, IndexError):
            return {
                "level": "unknown",
                "indicators": [],
                "p2025_alignment": None,
                "protective": False,
            }

    def generate_summary(self, title: str, text: str, max_words: int = 100) -> str:
        """Generate a plain-language summary of legislation."""
        prompt = f"""Summarize this legislation in plain language that anyone can understand.
Focus on: what it does, who it affects, and why it matters.

LEGISLATION:
Title: {title}
Text: {text[:4000]}

Write a summary of {max_words} words or less. Do not use legal jargon.
Do not include phrases like "This bill" - just describe what it does."""

        response = self._query_ollama(prompt)
        return response.strip()

    def recommend_actions(
        self,
        category_slug: str,
        threat_level: str,
        jurisdiction: str,
    ) -> list[dict]:
        """Get recommended actions based on category and threat level.

        Combines pre-defined actions with AI-generated specific recommendations.
        """
        # Get pre-defined actions for category
        actions = get_actions_for_category(category_slug)

        # Filter by jurisdiction
        filtered_actions = [
            a for a in actions
            if not a.effective_for or jurisdiction in a.effective_for
        ]

        # If high threat, prioritize urgent actions
        if threat_level in ["high", "critical"]:
            urgent = get_urgent_actions(category_slug)
            # Move urgent actions to front
            urgent_titles = {a.title for a in urgent}
            other_actions = [a for a in filtered_actions if a.title not in urgent_titles]
            filtered_actions = urgent + other_actions

        # Convert to dicts for JSON serialization
        return [
            {
                "type": a.action_type.value,
                "title": a.title,
                "description": a.description,
                "how_to": a.how_to,
                "urgency": a.urgency.value,
                "resources": a.resources,
            }
            for a in filtered_actions[:5]  # Top 5 actions
        ]

    def _build_analysis_prompt(
        self,
        title: str,
        text: str,
        jurisdiction: str,
        bill_number: Optional[str],
    ) -> str:
        """Build the full analysis prompt."""
        bill_info = f"Bill: {bill_number}\n" if bill_number else ""

        return f"""Analyze this legislation comprehensively.

{bill_info}Title: {title}
Jurisdiction: {jurisdiction}
Text:
{text[:5000]}

CATEGORIES:
{self._category_reference}

Provide analysis as JSON with this exact structure:
{{
  "primary_category": "category_slug",
  "secondary_categories": ["slug1"],
  "confidence": 0.85,
  "threat_level": "none|low|medium|high|critical",
  "threat_indicators": ["concern1", "concern2"],
  "p2025_alignment": "description or null",
  "summary": "plain language summary",
  "key_provisions": ["provision 1", "provision 2"],
  "affected_groups": ["group 1", "group 2"],
  "urgency": "low|medium|high|immediate"
}}

IMPORTANT:
- Use exact category slugs from the list above
- threat_level: "none" for neutral/protective, up to "critical" for severe
- p2025_alignment: describe how it aligns with Project 2025 if it does, otherwise null
- Be specific about who is affected and how"""

    def _query_ollama(self, prompt: str) -> str:
        """Send query to Ollama and return response."""
        url = f"{self.ollama_host}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Lower for more consistent classification
                "num_predict": 2000,
            },
        }

        try:
            response = self._client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to connect to Ollama at {self.ollama_host}: {e}")

    def _parse_response(self, response: str) -> AnalysisResult:
        """Parse Ollama response into AnalysisResult."""
        try:
            # Extract JSON from response
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str)

            # Get actions based on category and threat
            primary_cat = data.get("primary_category", "government")
            threat = data.get("threat_level", "low")
            actions = self.recommend_actions(primary_cat, threat, "state")

            return AnalysisResult(
                primary_category=primary_cat,
                secondary_categories=data.get("secondary_categories", []),
                confidence=data.get("confidence", 0.5),
                threat_level=threat,
                threat_indicators=data.get("threat_indicators", []),
                p2025_alignment=data.get("p2025_alignment"),
                summary=data.get("summary", ""),
                key_provisions=data.get("key_provisions", []),
                affected_groups=data.get("affected_groups", []),
                recommended_actions=actions,
                urgency=data.get("urgency", "medium"),
            )
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            # Return minimal result on parse failure
            return AnalysisResult(
                primary_category="government",
                secondary_categories=[],
                confidence=0.0,
                threat_level="unknown",
                threat_indicators=[],
                p2025_alignment=None,
                summary="Analysis failed - please review manually",
                key_provisions=[],
                affected_groups=[],
                recommended_actions=[],
                urgency="medium",
            )

    def batch_classify(
        self,
        items: list[dict],  # List of {"title": str, "summary": str}
    ) -> list[tuple[str, list[str], float]]:
        """Classify multiple items efficiently.

        For batch processing, we classify each item individually
        but could be optimized for bulk in the future.
        """
        results = []
        for item in items:
            result = self.classify_only(item["title"], item.get("summary", ""))
            results.append(result)
        return results

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def check_ollama_connection(host: Optional[str] = None) -> bool:
    """Check if Ollama is accessible."""
    host = host or os.getenv("OLLAMA_HOST", "http://20.98.70.48:11434")
    try:
        response = httpx.get(f"{host}/api/tags", timeout=5.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def list_ollama_models(host: Optional[str] = None) -> list[str]:
    """List available models on Ollama."""
    host = host or os.getenv("OLLAMA_HOST", "http://20.98.70.48:11434")
    try:
        response = httpx.get(f"{host}/api/tags", timeout=5.0)
        response.raise_for_status()
        data = response.json()
        return [m["name"] for m in data.get("models", [])]
    except httpx.HTTPError:
        return []
