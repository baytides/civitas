"""Generate plain-language insights for objectives, EOs, cases, and legislation."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from civitas.db.models import (
    ContentInsight,
    CourtCase,
    ExecutiveOrder,
    Legislation,
    Project2025Policy,
)

DEFAULT_OLLAMA_HOST = "http://20.98.70.48:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"
MAX_SOURCE_CHARS = 3200


class InsightGenerator:
    """Generate and store insight summaries."""

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

    def _truncate(self, text: str | None, limit: int = MAX_SOURCE_CHARS) -> str:
        if not text:
            return ""
        normalized = " ".join(text.split())
        return normalized[:limit]

    def _build_prompt(self, content_type: str, payload: dict) -> list[dict]:
        system = (
            "You are a nonpartisan policy analyst. "
            "Return JSON only with keys: summary, why_matters, key_impacts. "
            "summary: 2-3 plain-language sentences. "
            "why_matters: 2 sentences explaining impact on people or institutions. "
            "key_impacts: 3-5 short bullet phrases. "
            "No markdown, no extra keys."
        )
        user = f"Content type: {content_type}\nData: {json.dumps(payload, ensure_ascii=True)}"
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

    def _store_insight(
        self,
        content_type: str,
        content_id: int,
        parsed: dict,
    ) -> ContentInsight:
        key_impacts = parsed.get("key_impacts") or []
        if not isinstance(key_impacts, list):
            key_impacts = []

        existing = (
            self.session.query(ContentInsight)
            .filter(
                ContentInsight.content_type == content_type,
                ContentInsight.content_id == content_id,
            )
            .first()
        )
        if existing:
            existing.summary = parsed.get("summary")
            existing.why_matters = parsed.get("why_matters")
            existing.key_impacts = json.dumps(key_impacts, ensure_ascii=True)
            existing.ai_model_version = self.ollama_model
            existing.generated_at = datetime.now(UTC)
            self.session.add(existing)
            return existing

        insight = ContentInsight(
            content_type=content_type,
            content_id=content_id,
            summary=parsed.get("summary"),
            why_matters=parsed.get("why_matters"),
            key_impacts=json.dumps(key_impacts, ensure_ascii=True),
            ai_model_version=self.ollama_model,
            generated_at=datetime.now(UTC),
        )
        self.session.add(insight)
        return insight

    def _generate_for_payload(self, content_type: str, content_id: int, payload: dict) -> bool:
        client = self._get_ollama_client()
        messages = self._build_prompt(content_type, payload)
        response = client.chat(model=self.ollama_model, messages=messages)
        content = response.get("message", {}).get("content", "")
        parsed = self._parse_response(content)
        if not parsed:
            return False
        self._store_insight(content_type, content_id, parsed)
        return True

    def generate_batch(
        self,
        content_type: str,
        limit: int = 20,
        ids: list[int] | None = None,
        force: bool = False,
    ) -> int:
        """Generate insights for a batch of records."""
        if content_type not in {"objective", "eo", "case", "legislation"}:
            raise ValueError("content_type must be objective|eo|case|legislation")

        query = None
        model = None
        if content_type == "objective":
            model = Project2025Policy
            query = self.session.query(model)
        elif content_type == "eo":
            model = ExecutiveOrder
            query = self.session.query(model)
        elif content_type == "case":
            model = CourtCase
            query = self.session.query(model)
        elif content_type == "legislation":
            model = Legislation
            query = self.session.query(model)

        if ids:
            query = query.filter(model.id.in_(ids))

        if not force:
            existing_ids = {
                row[0]
                for row in self.session.query(ContentInsight.content_id)
                .filter(ContentInsight.content_type == content_type)
                .all()
            }
            if existing_ids:
                query = query.filter(model.id.notin_(existing_ids))

        items = query.limit(limit).all()
        success = 0

        for item in items:
            payload = self._build_payload(content_type, item)
            if not payload:
                continue
            if self._generate_for_payload(content_type, item.id, payload):
                success += 1
                self.session.commit()
        return success

    def _build_payload(self, content_type: str, item) -> dict:
        if content_type == "objective":
            return {
                "agency": item.agency,
                "category": item.category,
                "priority": item.priority,
                "timeline": item.implementation_timeline,
                "summary": self._truncate(item.proposal_summary),
                "text": self._truncate(item.proposal_text),
            }
        if content_type == "eo":
            return {
                "title": item.title,
                "president": item.president,
                "signing_date": str(item.signing_date) if item.signing_date else None,
                "abstract": self._truncate(item.abstract),
                "text": self._truncate(item.full_text),
            }
        if content_type == "case":
            return {
                "case_name": item.case_name,
                "court": item.court,
                "decision_date": str(item.decision_date) if item.decision_date else None,
                "holding": self._truncate(item.holding),
                "syllabus": self._truncate(item.syllabus),
            }
        if content_type == "legislation":
            return {
                "title": item.title or item.short_title,
                "jurisdiction": item.jurisdiction,
                "status": item.status,
                "summary": self._truncate(item.summary),
                "text": self._truncate(item.full_text),
            }
        return {}
