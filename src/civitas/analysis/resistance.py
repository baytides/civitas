"""Resistance strategy generator using Ollama/Llama AI.

Generates detailed resistance content including:
- Legal challenge outlines and court strategies
- Grassroots organizing guides
- Policy advocacy roadmaps
- Coalition building frameworks
- Media and communication strategies
"""

import json
import os
from dataclasses import dataclass
from enum import Enum

import httpx


class StrategyType(Enum):
    """Types of resistance strategies."""

    LEGAL = "legal"
    ORGANIZING = "organizing"
    ADVOCACY = "advocacy"
    MEDIA = "media"
    ELECTORAL = "electoral"
    DIRECT_ACTION = "direct_action"


@dataclass
class LegalStrategy:
    """Legal challenge strategy for a policy/law."""

    # Overview
    title: str
    applicable_to: str  # What type of law/policy this applies to
    legal_basis: list[str]  # Constitutional provisions, precedents

    # Court strategy
    recommended_court: str  # Federal district, state court, etc.
    standing_requirements: str  # Who can sue
    causes_of_action: list[str]  # Legal claims
    key_precedents: list[dict]  # Case names and why they're relevant
    potential_arguments: list[str]

    # Practical info
    timeline_estimate: str
    cost_estimate: str
    organizations_that_can_help: list[str]
    diy_steps: list[str]  # Steps individuals can take


@dataclass
class OrganizingGuide:
    """Grassroots organizing guide for an issue."""

    title: str
    goal: str
    target: str  # Who you're trying to influence

    # Building power
    stakeholders: list[str]  # Who to bring together
    coalition_partners: list[str]  # Organizations to partner with
    messaging_framework: dict  # Values, frames, talking points

    # Tactics
    short_term_actions: list[dict]  # Actions for next 2 weeks
    medium_term_campaign: list[dict]  # 1-3 month campaign
    long_term_strategy: list[dict]  # Systemic change

    # Resources
    tools_needed: list[str]
    sample_materials: list[str]  # Flyers, scripts, etc.


@dataclass
class ResistanceContent:
    """Complete resistance content for a category/issue."""

    category_slug: str
    issue_title: str

    # Detailed strategies
    legal_strategies: list[LegalStrategy]
    organizing_guides: list[OrganizingGuide]
    advocacy_roadmap: dict
    media_strategy: dict

    # Quick reference
    key_organizations: list[dict]
    emergency_contacts: list[dict]
    know_your_rights: list[str]


class ResistanceGenerator:
    """Generate detailed resistance content using Ollama/Llama AI.

    Uses Azure-hosted Ollama to generate:
    - Legal challenge outlines
    - Organizing guides
    - Advocacy strategies
    - Media playbooks
    """

    def __init__(
        self,
        ollama_host: str | None = None,
        model: str | None = None,
        timeout: float = 180.0,  # Longer timeout for detailed content
    ):
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://20.98.70.48:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def generate_legal_strategy(
        self,
        law_title: str,
        law_summary: str,
        category: str,
        jurisdiction: str,
        specific_concerns: list[str],
    ) -> LegalStrategy:
        """Generate a legal challenge strategy for a specific law.

        Args:
            law_title: Title of the law/policy
            law_summary: Summary of what it does
            category: Category slug (e.g., "immigration", "civil_rights")
            jurisdiction: "federal" or state name
            specific_concerns: List of specific problematic provisions

        Returns:
            LegalStrategy with court strategy, precedents, and practical info
        """
        prompt = f"""You are a constitutional law expert helping citizens understand how to legally challenge unjust laws.

LAW TO CHALLENGE:
Title: {law_title}
Summary: {law_summary}
Jurisdiction: {jurisdiction}
Category: {category}

SPECIFIC CONCERNS:
{chr(10).join(f"- {c}" for c in specific_concerns)}

Generate a comprehensive legal challenge strategy. Include:

1. CONSTITUTIONAL/LEGAL BASIS
- What constitutional provisions or federal laws might this violate?
- Consider: First Amendment, Fourteenth Amendment (due process, equal protection),
  Commerce Clause, Supremacy Clause, federal civil rights laws, etc.

2. COURT STRATEGY
- Which court should the case be filed in? (Federal district court, state court, etc.)
- Who has standing to sue? (Individuals affected, organizations, states)
- What causes of action (legal claims) could be brought?

3. KEY PRECEDENTS
- List 3-5 relevant Supreme Court or Circuit Court cases
- Explain briefly why each is relevant

4. POTENTIAL ARGUMENTS
- What are the strongest legal arguments against this law?
- What counterarguments might defendants raise?

5. PRACTICAL INFORMATION
- Estimated timeline for litigation
- Cost range (from pro bono options to full litigation)
- Organizations that provide legal help in this area
- Steps individuals can take now

Respond with JSON in this exact format:
{{
  "legal_basis": ["First Amendment - free speech", "Fourteenth Amendment - equal protection"],
  "recommended_court": "Federal District Court",
  "standing_requirements": "Individuals directly affected by..., organizations representing...",
  "causes_of_action": ["Constitutional violation under 42 U.S.C. § 1983", "..."],
  "key_precedents": [
    {{"case": "Case Name v. Defendant (Year)", "relevance": "Established that..."}}
  ],
  "potential_arguments": ["The law violates... because...", "Under precedent X..."],
  "timeline_estimate": "12-24 months for district court, 2-4 years with appeals",
  "cost_estimate": "Pro bono available through ACLU, private litigation $50k-500k+",
  "organizations_that_can_help": ["ACLU", "Lambda Legal", "NAACP LDF"],
  "diy_steps": ["Document how you're affected", "File formal complaint with agency", "Contact legal organizations"]
}}"""

        response = self._query_ollama(prompt)
        data = self._parse_json(response)

        return LegalStrategy(
            title=f"Legal Challenge: {law_title}",
            applicable_to=law_summary,
            legal_basis=data.get("legal_basis", []),
            recommended_court=data.get("recommended_court", "Federal District Court"),
            standing_requirements=data.get("standing_requirements", ""),
            causes_of_action=data.get("causes_of_action", []),
            key_precedents=data.get("key_precedents", []),
            potential_arguments=data.get("potential_arguments", []),
            timeline_estimate=data.get("timeline_estimate", "Unknown"),
            cost_estimate=data.get("cost_estimate", "Varies"),
            organizations_that_can_help=data.get("organizations_that_can_help", []),
            diy_steps=data.get("diy_steps", []),
        )

    def generate_organizing_guide(
        self,
        issue: str,
        category: str,
        jurisdiction: str,
        target_change: str,
    ) -> OrganizingGuide:
        """Generate a grassroots organizing guide for an issue.

        Args:
            issue: The specific issue to organize around
            category: Category slug
            jurisdiction: "federal", "state", or "local"
            target_change: What change you want to achieve

        Returns:
            OrganizingGuide with coalition building, tactics, and materials
        """
        prompt = f"""You are an experienced community organizer helping people build power for change.

ISSUE: {issue}
CATEGORY: {category}
JURISDICTION: {jurisdiction}
TARGET CHANGE: {target_change}

Create a comprehensive organizing guide. Include:

1. POWER MAPPING
- Who are the stakeholders affected by this issue?
- Who are potential coalition partners (organizations, unions, faith groups)?
- Who is the target (decision-maker with power to make the change)?

2. MESSAGING
- What values frame this issue (fairness, freedom, safety, community)?
- What are the key talking points?
- What's the narrative arc (problem, solution, action)?

3. CAMPAIGN TACTICS
- Short-term (next 2 weeks): Quick wins, visibility actions
- Medium-term (1-3 months): Sustained pressure campaign
- Long-term: Systemic change strategies

4. RESOURCES NEEDED
- Tools (canvassing lists, phone banks, social media)
- Materials (flyers, signs, scripts)
- People (volunteers, speakers, allies)

Respond with JSON:
{{
  "goal": "specific measurable goal",
  "target": "name/position of decision maker",
  "stakeholders": ["affected group 1", "affected group 2"],
  "coalition_partners": ["org type 1", "org type 2"],
  "messaging_framework": {{
    "core_value": "freedom/fairness/etc",
    "problem_statement": "...",
    "solution": "...",
    "call_to_action": "...",
    "talking_points": ["point 1", "point 2", "point 3"]
  }},
  "short_term_actions": [
    {{"action": "Action name", "goal": "what it achieves", "how": "step by step"}}
  ],
  "medium_term_campaign": [
    {{"phase": "Phase name", "actions": ["action 1", "action 2"], "goal": "..."}}
  ],
  "long_term_strategy": [
    {{"strategy": "Strategy name", "description": "...", "timeline": "..."}}
  ],
  "tools_needed": ["canvassing app", "phone bank software"],
  "sample_materials": ["door hanger template", "phone script", "social media posts"]
}}"""

        response = self._query_ollama(prompt)
        data = self._parse_json(response)

        return OrganizingGuide(
            title=f"Organizing Guide: {issue}",
            goal=data.get("goal", target_change),
            target=data.get("target", "Decision makers"),
            stakeholders=data.get("stakeholders", []),
            coalition_partners=data.get("coalition_partners", []),
            messaging_framework=data.get("messaging_framework", {}),
            short_term_actions=data.get("short_term_actions", []),
            medium_term_campaign=data.get("medium_term_campaign", []),
            long_term_strategy=data.get("long_term_strategy", []),
            tools_needed=data.get("tools_needed", []),
            sample_materials=data.get("sample_materials", []),
        )

    def generate_advocacy_roadmap(
        self,
        policy_goal: str,
        category: str,
        jurisdiction: str,
        current_status: str,
    ) -> dict:
        """Generate a policy advocacy roadmap.

        Args:
            policy_goal: What policy change you want
            category: Category slug
            jurisdiction: Level of government
            current_status: Current state of the issue

        Returns:
            Dict with lobbying strategy, legislative process guide, key contacts
        """
        prompt = f"""You are a policy advocate helping citizens navigate the legislative process.

POLICY GOAL: {policy_goal}
CATEGORY: {category}
JURISDICTION: {jurisdiction}
CURRENT STATUS: {current_status}

Create a policy advocacy roadmap. Include:

1. LEGISLATIVE PROCESS
- What committees would handle this issue?
- What's the typical path a bill takes?
- Key decision points where citizen input matters most

2. LOBBYING STRATEGY
- How to prepare for meetings with legislators
- What materials to bring
- How to follow up effectively
- Building ongoing relationships

3. BUILDING SUPPORT
- How to identify champion legislators
- How to neutralize opposition
- Coalition building for votes

4. TIMING
- Best times in the legislative calendar
- Relevant deadlines
- Session schedules

Respond with JSON:
{{
  "legislative_path": {{
    "committees": ["committee 1", "committee 2"],
    "process_steps": ["step 1", "step 2"],
    "key_decision_points": ["when committee votes", "floor vote"],
    "citizen_input_opportunities": ["public hearing", "written testimony"]
  }},
  "lobbying_strategy": {{
    "preparation": ["research legislator's positions", "prepare one-pager"],
    "meeting_tips": ["be specific", "share personal story", "make a clear ask"],
    "follow_up": ["send thank you", "provide additional info", "keep in touch"],
    "materials_to_prepare": ["one-page fact sheet", "personal story", "constituent letter"]
  }},
  "building_support": {{
    "finding_champions": ["check voting records", "committee membership"],
    "persuading_undecided": ["constituent pressure", "economic arguments"],
    "coalition_votes": "how to count and build to majority"
  }},
  "timing": {{
    "session_info": "when legislature is in session",
    "best_timing": "when to push for action",
    "key_deadlines": ["committee deadline", "floor deadline"]
  }}
}}"""

        response = self._query_ollama(prompt)
        return self._parse_json(response)

    def generate_media_strategy(
        self,
        issue: str,
        key_message: str,
        target_audience: str,
    ) -> dict:
        """Generate a media and communications strategy.

        Args:
            issue: The issue to communicate about
            key_message: Core message to convey
            target_audience: Who you're trying to reach

        Returns:
            Dict with press strategy, social media plan, spokesperson prep
        """
        prompt = f"""You are a communications strategist helping advocates get their message out.

ISSUE: {issue}
KEY MESSAGE: {key_message}
TARGET AUDIENCE: {target_audience}

Create a media and communications strategy. Include:

1. PRESS STRATEGY
- When and how to pitch stories
- Press release template elements
- Media list building
- Press event ideas

2. SOCIAL MEDIA
- Platform-specific strategies
- Content calendar ideas
- Hashtag strategy
- Engaging influencers

3. SPOKESPERSON PREPARATION
- Key messages and talking points
- Bridging techniques for tough questions
- Media training basics

4. RAPID RESPONSE
- Monitoring for opportunities
- Quick response protocol
- Crisis communications basics

Respond with JSON:
{{
  "press_strategy": {{
    "when_to_pitch": ["news hooks", "calendar opportunities"],
    "how_to_pitch": ["email template", "follow up strategy"],
    "press_release_elements": ["headline", "lede", "quotes", "background"],
    "media_list": ["types of outlets to target"],
    "event_ideas": ["press conference", "media availability"]
  }},
  "social_media": {{
    "platforms": {{"twitter": "strategy", "instagram": "strategy", "tiktok": "strategy"}},
    "content_types": ["personal stories", "infographics", "calls to action"],
    "posting_schedule": "recommendations",
    "hashtag_strategy": ["primary hashtag", "secondary hashtags"],
    "influencer_engagement": "how to identify and engage"
  }},
  "spokesperson_prep": {{
    "key_messages": ["message 1", "message 2", "message 3"],
    "talking_points": ["point 1", "point 2"],
    "bridging_phrases": ["That's an important point, and...", "What really matters is..."],
    "tough_questions": [{{"question": "...", "response": "..."}}]
  }},
  "rapid_response": {{
    "monitoring": ["google alerts", "social listening"],
    "response_protocol": ["assess", "draft", "approve", "distribute"],
    "crisis_basics": ["stay calm", "acknowledge", "correct misinformation"]
  }}
}}"""

        response = self._query_ollama(prompt)
        return self._parse_json(response)

    def generate_know_your_rights(
        self,
        category: str,
        context: str,
    ) -> list[dict]:
        """Generate know-your-rights information for a category.

        Args:
            category: Category slug
            context: Specific context (e.g., "if stopped by police", "at a protest")

        Returns:
            List of rights with explanations and what to do
        """
        prompt = f"""You are a civil rights educator helping people understand their legal rights.

CATEGORY: {category}
CONTEXT: {context}

Create a "Know Your Rights" guide. For each right:
1. State the right clearly
2. Explain what it means in practice
3. Give specific examples
4. Explain what to do if the right is violated

Focus on rights that are:
- Commonly misunderstood
- Frequently tested in this context
- Important for protecting yourself

Respond with JSON:
{{
  "rights": [
    {{
      "right": "Clear statement of the right",
      "explanation": "What this means in plain language",
      "in_practice": "How to exercise this right",
      "examples": [],
      "if_violated": "What to do if this right is violated",
      "important_note": "Any caveats or nuances"
    }}
  ],
  "general_tips": ["tip 1", "tip 2"],
  "emergency_resources": ["resource 1", "resource 2"]
}}"""

        response = self._query_ollama(prompt)
        data = self._parse_json(response)
        return data.get("rights", [])

    def generate_full_resistance_content(
        self,
        category_slug: str,
        issue_title: str,
        issue_summary: str,
        jurisdiction: str,
        specific_law: str | None = None,
    ) -> ResistanceContent:
        """Generate comprehensive resistance content for an issue.

        This is the main method that combines all strategies into
        a complete resistance package.
        """
        # Generate each component
        legal_strategies = []
        if specific_law:
            legal = self.generate_legal_strategy(
                law_title=specific_law,
                law_summary=issue_summary,
                category=category_slug,
                jurisdiction=jurisdiction,
                specific_concerns=["See issue summary"],
            )
            legal_strategies.append(legal)

        organizing = self.generate_organizing_guide(
            issue=issue_title,
            category=category_slug,
            jurisdiction=jurisdiction,
            target_change=f"Stop/reverse {issue_title}",
        )

        advocacy = self.generate_advocacy_roadmap(
            policy_goal=f"Address {issue_title}",
            category=category_slug,
            jurisdiction=jurisdiction,
            current_status="Active threat",
        )

        media = self.generate_media_strategy(
            issue=issue_title,
            key_message=f"Protect communities from {issue_title}",
            target_audience="General public and decision makers",
        )

        know_rights = self.generate_know_your_rights(
            category=category_slug,
            context=f"In context of {issue_title}",
        )

        return ResistanceContent(
            category_slug=category_slug,
            issue_title=issue_title,
            legal_strategies=legal_strategies,
            organizing_guides=[organizing],
            advocacy_roadmap=advocacy,
            media_strategy=media,
            key_organizations=self._get_key_orgs_for_category(category_slug),
            emergency_contacts=self._get_emergency_contacts(category_slug),
            know_your_rights=know_rights,
        )

    def _get_key_orgs_for_category(self, category: str) -> list[dict]:
        """Get key organizations for a category (static reference data)."""
        orgs = {
            "civil_rights": [
                {"name": "ACLU", "url": "https://www.aclu.org", "focus": "Civil liberties"},
                {"name": "NAACP LDF", "url": "https://www.naacpldf.org", "focus": "Racial justice"},
                {
                    "name": "Lambda Legal",
                    "url": "https://www.lambdalegal.org",
                    "focus": "LGBTQ+ rights",
                },
            ],
            "immigration": [
                {
                    "name": "RAICES",
                    "url": "https://www.raicestexas.org",
                    "focus": "Immigration legal services",
                },
                {"name": "NILC", "url": "https://www.nilc.org", "focus": "Immigrant rights policy"},
                {
                    "name": "United We Dream",
                    "url": "https://unitedwedream.org",
                    "focus": "Youth immigrant organizing",
                },
            ],
            "healthcare": [
                {
                    "name": "Families USA",
                    "url": "https://familiesusa.org",
                    "focus": "Healthcare access",
                },
                {
                    "name": "Community Catalyst",
                    "url": "https://communitycatalyst.org",
                    "focus": "Health advocacy",
                },
            ],
            "reproductive_rights": [
                {
                    "name": "National Abortion Federation",
                    "url": "https://prochoice.org",
                    "focus": "Abortion access",
                },
                {
                    "name": "Center for Reproductive Rights",
                    "url": "https://reproductiverights.org",
                    "focus": "Legal advocacy",
                },
                {
                    "name": "National Network of Abortion Funds",
                    "url": "https://abortionfunds.org",
                    "focus": "Funding access",
                },
            ],
            "environment": [
                {
                    "name": "Sierra Club",
                    "url": "https://www.sierraclub.org",
                    "focus": "Environmental protection",
                },
                {
                    "name": "Earthjustice",
                    "url": "https://earthjustice.org",
                    "focus": "Environmental law",
                },
                {"name": "350.org", "url": "https://350.org", "focus": "Climate action"},
            ],
            "elections": [
                {
                    "name": "League of Women Voters",
                    "url": "https://www.lwv.org",
                    "focus": "Voting rights",
                },
                {
                    "name": "Common Cause",
                    "url": "https://www.commoncause.org",
                    "focus": "Democracy reform",
                },
                {
                    "name": "Brennan Center",
                    "url": "https://www.brennancenter.org",
                    "focus": "Voting rights legal",
                },
            ],
        }
        return orgs.get(
            category,
            [
                {"name": "ACLU", "url": "https://www.aclu.org", "focus": "Civil liberties"},
            ],
        )

    def _get_emergency_contacts(self, category: str) -> list[dict]:
        """Get emergency contacts for a category."""
        contacts = {
            "immigration": [
                {
                    "name": "ICE Detainee Locator",
                    "number": "1-888-351-4024",
                    "when": "If someone is detained",
                },
                {
                    "name": "RAICES Hotline",
                    "number": "1-800-516-3996",
                    "when": "Immigration legal emergency",
                },
            ],
            "civil_rights": [
                {"name": "ACLU", "number": "Local affiliate", "when": "Rights violation"},
            ],
            "criminal_justice": [
                {
                    "name": "National Bail Fund Network",
                    "url": "https://www.communityjusticeexchange.org/nbfn-directory",
                    "when": "Bail needed",
                },
            ],
        }
        return contacts.get(category, [])

    def _query_ollama(self, prompt: str) -> str:
        """Send query to Ollama and return response."""
        url = f"{self.ollama_host}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "num_predict": 4000,  # Longer for detailed content
            },
        }

        try:
            response = self._client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to connect to Ollama at {self.ollama_host}: {e}")

    def _parse_json(self, response: str) -> dict:
        """Parse JSON from Ollama response."""
        try:
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            return {}

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
