"""Generate short titles for Project 2025 objectives using Ollama via Bay Tides."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from civitas.ai.prompts import load_prompt
from civitas.db.models import Project2025Policy

DEFAULT_OLLAMA_HOST = "https://ollama.baytides.org"
DEFAULT_OLLAMA_MODEL = "llama3.2"


class Project2025TitleGenerator:
    """Generate short titles for Project 2025 objectives."""

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

    def _build_prompt(self, items: list[Project2025Policy]) -> list[dict]:
        default_system = (
            "You are a policy editor. Create short, human-readable titles for each item. "
            "Use 6-12 words. Start with a clear action or outcome. "
            "Avoid jargon, avoid filler words, avoid quoting the full sentence. "
            'Return JSON only: {"titles": [{"id": 1, "short_title": "..."}]}'
        )
        system = load_prompt(
            path_env="BAYTIDES_OBJECTIVE_TITLE_PROMPT_PATH",
            inline_env="BAYTIDES_OBJECTIVE_TITLE_PROMPT",
            fallback=default_system,
        )
        payload = [
            {
                "id": item.id,
                "agency": item.agency,
                "action_type": item.action_type,
                "category": item.category,
                "proposal_summary": item.proposal_summary,
                "proposal_text": (item.proposal_text or "")[:600],
            }
            for item in items
        ]
        user = f"Generate short titles for these items:\n{json.dumps(payload, ensure_ascii=True)}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

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

    def generate_batch(
        self,
        limit: int = 25,
        ids: list[int] | None = None,
        force: bool = False,
    ) -> int:
        """Generate short titles for a batch of objectives."""
        query = self.session.query(Project2025Policy)
        if ids:
            query = query.filter(Project2025Policy.id.in_(ids))
        elif not force:
            query = query.filter(Project2025Policy.short_title.is_(None))

        items = query.limit(limit).all()
        if not items:
            return 0

        client = self._get_ollama_client()
        messages = self._build_prompt(items)
        response = client.chat(model=self.ollama_model, messages=messages)
        content = response.get("message", {}).get("content", "")
        parsed = self._parse_response(content)
        if not parsed:
            return 0

        titles = parsed.get("titles") or []
        if not isinstance(titles, list):
            return 0

        updated = 0
        for entry in titles:
            item_id = entry.get("id")
            short_title = entry.get("short_title")
            if not item_id or not short_title:
                continue
            policy = self.session.get(Project2025Policy, item_id)
            if not policy:
                continue
            policy.short_title = short_title.strip()[:300]
            policy.updated_at = datetime.now(UTC)
            updated += 1

        if updated:
            self.session.commit()
        return updated
