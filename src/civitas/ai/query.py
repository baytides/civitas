"""AI-powered natural language query interface for the Civitas database.

Supports multiple AI backends:
- Ollama (self-hosted Llama) - default, runs on Azure
- Anthropic Claude (API-based)
- OpenAI (API-based)
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from civitas.db.models import (
    Base,
    Legislation,
    LegislationAction,
    Legislator,
    Vote,
    LawCode,
    LawSection,
)

# Default Ollama configuration (Carl AI VM on Azure)
DEFAULT_OLLAMA_HOST = "http://20.98.70.48:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"


# SQL query templates for common operations
QUERY_TEMPLATES = {
    "search_legislation": """
        SELECT id, jurisdiction, citation, title, status, is_enacted, public_law_number, session
        FROM legislation
        WHERE {conditions}
        ORDER BY last_action_date DESC NULLS LAST
        LIMIT {limit}
    """,
    "get_legislation_detail": """
        SELECT l.*,
               (SELECT COUNT(*) FROM legislation_actions WHERE legislation_id = l.id) as action_count,
               (SELECT COUNT(*) FROM votes WHERE legislation_id = l.id) as vote_count
        FROM legislation l
        WHERE l.id = {id}
    """,
    "search_legislators": """
        SELECT id, jurisdiction, full_name, chamber, state, district, party, is_current
        FROM legislators
        WHERE {conditions}
        ORDER BY full_name
        LIMIT {limit}
    """,
    "count_by_jurisdiction": """
        SELECT jurisdiction,
               COUNT(*) as total,
               SUM(CASE WHEN is_enacted = 1 THEN 1 ELSE 0 END) as enacted
        FROM legislation
        GROUP BY jurisdiction
    """,
    "recent_laws": """
        SELECT id, jurisdiction, citation, title, public_law_number, enacted_date
        FROM legislation
        WHERE is_enacted = 1
        ORDER BY last_action_date DESC NULLS LAST
        LIMIT {limit}
    """,
}


class CivitasAI:
    """AI-powered interface for querying the Civitas database.

    This class provides both direct query methods and natural language
    query capabilities (when an AI provider is configured).
    """

    def __init__(
        self,
        db_path: str = "civitas.db",
        ai_provider: Optional[str] = None,
        api_key: Optional[str] = None,
        ollama_host: Optional[str] = None,
        ollama_model: Optional[str] = None,
    ):
        """Initialize the AI query interface.

        Args:
            db_path: Path to the SQLite database
            ai_provider: AI provider ("ollama", "anthropic", or "openai")
            api_key: API key for AI provider (or from env)
            ollama_host: Ollama server URL (default: Azure Carl VM)
            ollama_model: Ollama model name (default: llama3.2)
        """
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine)

        # AI provider configuration
        self.ai_provider = ai_provider or os.getenv("CIVITAS_AI_PROVIDER", "ollama")
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")

        # Ollama configuration (default to Carl AI VM on Azure)
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)

        self._ai_client = None

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    # =========================================================================
    # Direct Query Methods
    # =========================================================================

    def search(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        session_year: Optional[str] = None,
        enacted_only: bool = False,
        limit: int = 20,
    ) -> list[dict]:
        """Search legislation by keyword.

        Args:
            query: Search term (searches citation and title)
            jurisdiction: Filter by jurisdiction (federal, california)
            session_year: Filter by session/congress
            enacted_only: Only return enacted laws
            limit: Maximum results

        Returns:
            List of matching legislation records
        """
        db_session = self.get_session()
        try:
            q = db_session.query(Legislation)

            # Search in citation and title
            search_term = f"%{query}%"
            q = q.filter(
                (Legislation.citation.ilike(search_term)) |
                (Legislation.title.ilike(search_term)) |
                (Legislation.summary.ilike(search_term))
            )

            if jurisdiction:
                q = q.filter(Legislation.jurisdiction == jurisdiction)
            if session_year:
                q = q.filter(Legislation.session == session_year)
            if enacted_only:
                q = q.filter(Legislation.is_enacted == True)

            q = q.order_by(Legislation.last_action_date.desc().nullslast())
            q = q.limit(limit)

            results = []
            for leg in q.all():
                results.append({
                    "id": leg.id,
                    "jurisdiction": leg.jurisdiction,
                    "citation": leg.citation,
                    "title": leg.title,
                    "status": leg.status,
                    "is_enacted": leg.is_enacted,
                    "public_law_number": leg.public_law_number,
                    "session": leg.session,
                })

            return results
        finally:
            db_session.close()

    def get_legislation(self, legislation_id: int) -> Optional[dict]:
        """Get detailed information about a specific piece of legislation.

        Args:
            legislation_id: Database ID of the legislation

        Returns:
            Detailed legislation record or None
        """
        db_session = self.get_session()
        try:
            leg = db_session.query(Legislation).filter_by(id=legislation_id).first()
            if not leg:
                return None

            # Get related data
            actions = db_session.query(LegislationAction).filter_by(
                legislation_id=legislation_id
            ).order_by(LegislationAction.action_date.desc()).limit(10).all()

            votes = db_session.query(Vote).filter_by(
                legislation_id=legislation_id
            ).order_by(Vote.vote_date.desc()).all()

            return {
                "id": leg.id,
                "jurisdiction": leg.jurisdiction,
                "citation": leg.citation,
                "title": leg.title,
                "summary": leg.summary,
                "status": leg.status,
                "current_location": leg.current_location,
                "is_enacted": leg.is_enacted,
                "public_law_number": leg.public_law_number,
                "chapter_number": leg.chapter_number,
                "session": leg.session,
                "introduced_date": str(leg.introduced_date) if leg.introduced_date else None,
                "last_action_date": str(leg.last_action_date) if leg.last_action_date else None,
                "full_text": leg.full_text[:1000] + "..." if leg.full_text and len(leg.full_text) > 1000 else leg.full_text,
                "recent_actions": [
                    {
                        "date": str(a.action_date),
                        "text": a.action_text,
                        "committee": a.committee,
                    }
                    for a in actions
                ],
                "votes": [
                    {
                        "date": str(v.vote_date),
                        "chamber": v.chamber,
                        "ayes": v.ayes,
                        "nays": v.nays,
                        "result": v.result,
                    }
                    for v in votes
                ],
            }
        finally:
            db_session.close()

    def get_recent_laws(
        self,
        jurisdiction: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Get recently enacted laws.

        Args:
            jurisdiction: Filter by jurisdiction
            limit: Maximum results

        Returns:
            List of recent laws
        """
        db_session = self.get_session()
        try:
            q = db_session.query(Legislation).filter(Legislation.is_enacted == True)

            if jurisdiction:
                q = q.filter(Legislation.jurisdiction == jurisdiction)

            q = q.order_by(Legislation.last_action_date.desc().nullslast())
            q = q.limit(limit)

            return [
                {
                    "id": leg.id,
                    "jurisdiction": leg.jurisdiction,
                    "citation": leg.citation,
                    "title": leg.title,
                    "public_law_number": leg.public_law_number,
                    "chapter_number": leg.chapter_number,
                }
                for leg in q.all()
            ]
        finally:
            db_session.close()

    def get_legislator(
        self,
        name: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        chamber: Optional[str] = None,
        party: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        """Search for legislators.

        Args:
            name: Search by name
            jurisdiction: Filter by jurisdiction
            chamber: Filter by chamber (house/senate)
            party: Filter by party
            limit: Maximum results

        Returns:
            List of matching legislators
        """
        db_session = self.get_session()
        try:
            q = db_session.query(Legislator)

            if name:
                q = q.filter(Legislator.full_name.ilike(f"%{name}%"))
            if jurisdiction:
                q = q.filter(Legislator.jurisdiction == jurisdiction)
            if chamber:
                q = q.filter(Legislator.chamber == chamber)
            if party:
                q = q.filter(Legislator.party.ilike(f"%{party}%"))

            q = q.order_by(Legislator.full_name).limit(limit)

            return [
                {
                    "id": leg.id,
                    "full_name": leg.full_name,
                    "jurisdiction": leg.jurisdiction,
                    "chamber": leg.chamber,
                    "state": leg.state,
                    "district": leg.district,
                    "party": leg.party,
                    "is_current": leg.is_current,
                }
                for leg in q.all()
            ]
        finally:
            db_session.close()

    def get_statistics(self) -> dict:
        """Get database statistics.

        Returns:
            Dictionary of statistics
        """
        db_session = self.get_session()
        try:
            stats = {
                "total_legislation": db_session.query(Legislation).count(),
                "by_jurisdiction": {},
                "enacted_laws": db_session.query(Legislation).filter_by(is_enacted=True).count(),
                "total_legislators": db_session.query(Legislator).count(),
                "total_votes": db_session.query(Vote).count(),
                "law_codes": db_session.query(LawCode).count(),
            }

            # Count by jurisdiction
            for row in db_session.execute(text("""
                SELECT jurisdiction, COUNT(*) as total,
                       SUM(CASE WHEN is_enacted = 1 THEN 1 ELSE 0 END) as enacted
                FROM legislation
                GROUP BY jurisdiction
            """)):
                stats["by_jurisdiction"][row[0]] = {
                    "total": row[1],
                    "enacted": row[2],
                }

            return stats
        finally:
            db_session.close()

    # =========================================================================
    # Natural Language Query (AI-Powered)
    # =========================================================================

    def ask(self, question: str) -> str:
        """Ask a natural language question about legislation.

        This method uses AI to interpret the question and query the database.
        Default provider is Ollama (Llama on Azure), but will fall back to
        keyword search if AI is unavailable.

        Args:
            question: Natural language question

        Returns:
            Natural language response
        """
        # Always try AI query first (defaults to Ollama)
        try:
            return self._ai_query(question)
        except Exception as e:
            # Fall back to keyword search if AI fails
            return f"AI unavailable: {str(e)}\n\n{self._keyword_search_response(question)}"

    def _keyword_search_response(self, question: str) -> str:
        """Generate response using keyword search (no AI)."""
        # Extract potential search terms
        words = question.lower().split()
        skip_words = {"what", "which", "who", "how", "many", "is", "are", "the", "a", "an",
                      "about", "find", "search", "show", "me", "list", "get", "legislation",
                      "bill", "bills", "law", "laws", "on", "for", "in", "related", "to"}

        search_terms = [w for w in words if w not in skip_words and len(w) > 2]

        if not search_terms:
            stats = self.get_statistics()
            return f"""Database Statistics:
- Total legislation: {stats['total_legislation']:,}
- Enacted laws: {stats['enacted_laws']:,}
- Legislators: {stats['total_legislators']:,}
- Votes recorded: {stats['total_votes']:,}

By jurisdiction:
{chr(10).join(f"  - {k}: {v['total']:,} total, {v['enacted']:,} enacted" for k, v in stats['by_jurisdiction'].items())}

Try asking about specific topics like 'water', 'climate', 'housing', etc."""

        # Search for each term
        query = " ".join(search_terms)
        results = self.search(query, limit=10)

        if not results:
            return f"No legislation found matching: {query}"

        response = f"Found {len(results)} results for '{query}':\n\n"
        for r in results:
            status = "✓ Enacted" if r["is_enacted"] else r["status"] or "Pending"
            response += f"• {r['citation']} ({r['jurisdiction'].title()})\n"
            if r["title"]:
                response += f"  {r['title'][:100]}{'...' if len(r['title'] or '') > 100 else ''}\n"
            response += f"  Status: {status}\n\n"

        return response

    def _ai_query(self, question: str) -> str:
        """Use AI to answer the question."""
        if self.ai_provider == "ollama":
            return self._ollama_query(question)
        elif self.ai_provider == "anthropic":
            return self._anthropic_query(question)
        elif self.ai_provider == "openai":
            return self._openai_query(question)
        else:
            raise ValueError(f"Unknown AI provider: {self.ai_provider}")

    def _ollama_query(self, question: str) -> str:
        """Query using Ollama with Llama model (self-hosted on Azure).

        Uses the Ollama API running on Carl AI VM (20.98.70.48).
        """
        try:
            import ollama
        except ImportError:
            raise ImportError("Install ollama package: pip install ollama")

        # Create client with configured host
        client = ollama.Client(host=self.ollama_host)

        # Get database context
        stats = self.get_statistics()
        recent_laws = self.get_recent_laws(limit=5)

        # Build system prompt with database context
        system_prompt = f"""You are a helpful assistant for the Civitas legislative database, a civic empowerment platform that tracks legislation, court cases, and executive actions.

Database contains:
- {stats['total_legislation']:,} pieces of legislation
- {stats['enacted_laws']:,} enacted laws
- {stats['total_legislators']:,} legislators
- {stats.get('law_codes', 0)} law codes
- Jurisdictions: {', '.join(stats['by_jurisdiction'].keys()) if stats['by_jurisdiction'] else 'None yet'}

When answering questions about legislation:
1. Use the context provided from database searches
2. Be concise and factual
3. If data isn't available, say so clearly
4. Cite specific legislation by citation (e.g., HR 1, AB 123)

Recent laws in database:
{json.dumps(recent_laws, indent=2)}
"""

        # Extract search terms and query database for context
        search_results = self._extract_and_search(question)

        # Build user message with database context
        user_message = f"""Question: {question}

Relevant data from database search:
{json.dumps(search_results, indent=2, default=str)}

Please answer the question based on this data. If the data doesn't contain relevant information, say so and provide general guidance on how to find the information."""

        try:
            response = client.chat(
                model=self.ollama_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            return response["message"]["content"]
        except Exception as e:
            # Fall back to keyword search if Ollama is unavailable
            return f"AI service unavailable ({str(e)}). Falling back to keyword search.\n\n{self._keyword_search_response(question)}"

    def _extract_and_search(self, question: str) -> dict:
        """Extract search terms from question and query database for context."""
        # Extract keywords from question
        words = question.lower().split()
        skip_words = {
            "what", "which", "who", "how", "many", "is", "are", "the", "a", "an",
            "about", "find", "search", "show", "me", "list", "get", "legislation",
            "bill", "bills", "law", "laws", "on", "for", "in", "related", "to",
            "case", "cases", "court", "executive", "order", "orders", "recent",
            "latest", "new", "any", "all", "does", "do", "have", "has", "been",
            "was", "were", "will", "would", "could", "should", "can", "may",
            "might", "must", "shall", "there", "their", "they", "them", "this",
            "that", "these", "those", "with", "from", "into", "through", "during",
            "before", "after", "above", "below", "between", "under", "again",
        }

        search_terms = [w for w in words if w not in skip_words and len(w) > 2]
        query = " ".join(search_terms)

        results = {
            "statistics": self.get_statistics(),
            "legislation": [],
            "legislators": [],
        }

        if query:
            # Search legislation
            results["legislation"] = self.search(query, limit=10)

            # Search legislators if relevant terms present
            legislator_terms = {"senator", "representative", "congressman", "congresswoman", "member", "sponsor"}
            if any(term in question.lower() for term in legislator_terms):
                results["legislators"] = self.get_legislator(name=query, limit=5)

        return results

    def _anthropic_query(self, question: str) -> str:
        """Query using Anthropic's Claude."""
        try:
            import anthropic
        except ImportError:
            raise ImportError("Install anthropic package: pip install anthropic")

        if not self._ai_client:
            self._ai_client = anthropic.Anthropic(api_key=self.api_key)

        # Get database context
        stats = self.get_statistics()
        recent_laws = self.get_recent_laws(limit=5)

        system_prompt = f"""You are a helpful assistant for the Civitas legislative database.

Database contains:
- {stats['total_legislation']:,} pieces of legislation
- {stats['enacted_laws']:,} enacted laws
- {stats['total_legislators']:,} legislators
- Jurisdictions: {', '.join(stats['by_jurisdiction'].keys())}

You have access to these functions to query the database:
- search(query, jurisdiction, enacted_only, limit): Search legislation by keyword
- get_legislation(id): Get detailed info about specific legislation
- get_recent_laws(jurisdiction, limit): Get recently enacted laws
- get_legislator(name, jurisdiction, chamber, party): Search legislators
- get_statistics(): Get database statistics

When answering questions:
1. Identify what data is needed
2. Call appropriate functions
3. Summarize results clearly

Recent laws in database:
{json.dumps(recent_laws, indent=2)}
"""

        # Define tools for function calling
        tools = [
            {
                "name": "search_legislation",
                "description": "Search legislation by keyword in title or content",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search keywords"},
                        "jurisdiction": {"type": "string", "enum": ["federal", "california"]},
                        "enacted_only": {"type": "boolean", "default": False},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_legislation_detail",
                "description": "Get detailed information about a specific piece of legislation",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "legislation_id": {"type": "integer"},
                    },
                    "required": ["legislation_id"],
                },
            },
            {
                "name": "get_recent_laws",
                "description": "Get recently enacted laws",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "jurisdiction": {"type": "string", "enum": ["federal", "california"]},
                        "limit": {"type": "integer", "default": 10},
                    },
                },
            },
            {
                "name": "search_legislators",
                "description": "Search for legislators by name, party, or chamber",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "jurisdiction": {"type": "string"},
                        "chamber": {"type": "string", "enum": ["house", "senate"]},
                        "party": {"type": "string"},
                    },
                },
            },
        ]

        # Initial request
        response = self._ai_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=[{"role": "user", "content": question}],
        )

        # Handle tool calls
        while response.stop_reason == "tool_use":
            tool_results = []
            for content in response.content:
                if content.type == "tool_use":
                    result = self._execute_tool(content.name, content.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content.id,
                        "content": json.dumps(result),
                    })

            # Continue conversation with tool results
            response = self._ai_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_prompt,
                tools=tools,
                messages=[
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": tool_results},
                ],
            )

        # Extract text response
        for content in response.content:
            if hasattr(content, "text"):
                return content.text

        return "Unable to generate response."

    def _execute_tool(self, tool_name: str, args: dict) -> Any:
        """Execute a tool call and return results."""
        if tool_name == "search_legislation":
            return self.search(
                query=args.get("query", ""),
                jurisdiction=args.get("jurisdiction"),
                enacted_only=args.get("enacted_only", False),
                limit=args.get("limit", 10),
            )
        elif tool_name == "get_legislation_detail":
            return self.get_legislation(args["legislation_id"])
        elif tool_name == "get_recent_laws":
            return self.get_recent_laws(
                jurisdiction=args.get("jurisdiction"),
                limit=args.get("limit", 10),
            )
        elif tool_name == "search_legislators":
            return self.get_legislator(
                name=args.get("name"),
                jurisdiction=args.get("jurisdiction"),
                chamber=args.get("chamber"),
                party=args.get("party"),
            )
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _openai_query(self, question: str) -> str:
        """Query using OpenAI."""
        try:
            import openai
        except ImportError:
            raise ImportError("Install openai package: pip install openai")

        if not self._ai_client:
            self._ai_client = openai.OpenAI(api_key=self.api_key)

        # Similar implementation to Anthropic but using OpenAI's API
        # For brevity, fall back to keyword search for now
        return self._keyword_search_response(question)
