#!/usr/bin/env python3
"""Extract Project 2025 policy proposals from the text version of the document.

This script parses the text version of the Mandate for Leadership document
to extract actionable policy proposals, then uses Ollama to categorize and
summarize them.

Usage:
    python scripts/extract_p2025_from_text.py --input data/project2025/mandate.txt --output data/project2025/policies.json

    # To update database directly:
    python scripts/extract_p2025_from_text.py --input data/project2025/mandate.txt --update-db
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import ollama
except ImportError:
    print("Install ollama: pip install ollama")
    sys.exit(1)


# Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct-q8_0")


@dataclass
class Policy:
    """A policy proposal from Project 2025."""
    section: str
    agency: str
    raw_text: str
    title: str = ""
    summary: str = ""
    category: str = "general"
    action_type: str = "unknown"
    priority: str = "medium"
    timeline: str = "unknown"
    status: str = "not_started"
    confidence: float = 0.0


# Chapter/section markers in the document
SECTION_MARKERS = [
    ("WHITE HOUSE OFFICE", "White House Office"),
    ("EXECUTIVE OFFICE OF THE PRESIDENT", "Executive Office of the President"),
    ("CENTRAL PERSONNEL AGENCIES", "Office of Personnel Management"),
    ("DEPARTMENT OF DEFENSE", "Department of Defense"),
    ("DEPARTMENT OF HOMELAND SECURITY", "Department of Homeland Security"),
    ("DEPARTMENT OF STATE", "Department of State"),
    ("INTELLIGENCE COMMUNITY", "Intelligence Community"),
    ("MEDIA AGENCIES", "Media Agencies"),
    ("AGENCY FOR INTERNATIONAL DEVELOPMENT", "USAID"),
    ("DEPARTMENT OF AGRICULTURE", "Department of Agriculture"),
    ("DEPARTMENT OF EDUCATION", "Department of Education"),
    ("DEPARTMENT OF ENERGY", "Department of Energy"),
    ("ENVIRONMENTAL PROTECTION AGENCY", "Environmental Protection Agency"),
    ("DEPARTMENT OF HEALTH AND HUMAN SERVICES", "Department of Health and Human Services"),
    ("DEPARTMENT OF HOUSING AND URBAN DEVELOPMENT", "Department of Housing and Urban Development"),
    ("DEPARTMENT OF THE INTERIOR", "Department of the Interior"),
    ("DEPARTMENT OF JUSTICE", "Department of Justice"),
    ("DEPARTMENT OF LABOR", "Department of Labor"),
    ("DEPARTMENT OF TRANSPORTATION", "Department of Transportation"),
    ("DEPARTMENT OF VETERANS AFFAIRS", "Department of Veterans Affairs"),
    ("DEPARTMENT OF COMMERCE", "Department of Commerce"),
    ("DEPARTMENT OF THE TREASURY", "Department of the Treasury"),
    ("EXPORT-IMPORT BANK", "Export-Import Bank"),
    ("FEDERAL RESERVE", "Federal Reserve"),
    ("SMALL BUSINESS ADMINISTRATION", "Small Business Administration"),
    ("TRADE", "Trade"),
    ("FINANCIAL REGULATORY AGENCIES", "Financial Regulatory Agencies"),
    ("FEDERAL COMMUNICATIONS COMMISSION", "Federal Communications Commission"),
    ("FEDERAL ELECTION COMMISSION", "Federal Election Commission"),
    ("FEDERAL TRADE COMMISSION", "Federal Trade Commission"),
]


def find_current_section(text_before: str) -> tuple[str, str]:
    """Determine which section a piece of text belongs to."""
    # Search backwards through section markers
    best_match = ("General", "General")
    best_pos = -1

    for marker, agency in SECTION_MARKERS:
        pos = text_before.upper().rfind(marker)
        if pos > best_pos:
            best_pos = pos
            best_match = (marker, agency)

    return best_match


def extract_policy_paragraphs(text: str) -> list[tuple[str, str, str]]:
    """Extract paragraphs that contain policy recommendations.

    Returns list of (agency, section, text) tuples.
    """
    # Patterns that indicate policy recommendations
    policy_patterns = [
        r"(?:The\s+)?(?:next\s+)?(?:Administration|President|Congress)\s+should",
        r"(?:The\s+)?(?:Department|Agency|Bureau|Office|EPA|DOJ|DHS|HHS)\s+should",
        r"(?:Congress|Legislature)\s+should",
        r"(?:Must|Should|Will)\s+(?:eliminate|abolish|repeal|restructure|reform|create|establish|end|terminate|reduce)",
        r"(?:Recommendation|Proposal|Priority):",
        r"Day\s+(?:One|1)",
        r"(?:First|Within)\s+(?:100|hundred)\s+days",
        r"(?:Immediately|Urgently)\s+(?:terminate|end|stop|begin|start)",
        r"(?:repeal|rescind|reverse|revoke|overturn)",
        r"(?:eliminate|defund|dismantle)\s+(?:the|all)",
    ]

    combined_pattern = "|".join(f"({p})" for p in policy_patterns)

    policies = []

    # Split into paragraphs (double newline or significant whitespace)
    paragraphs = re.split(r'\n\s*\n', text)

    for i, para in enumerate(paragraphs):
        para = para.strip()

        # Skip short paragraphs
        if len(para) < 150:
            continue

        # Skip table of contents, acknowledgments, etc.
        if re.search(r'^\s*(?:Chapter|Section|Table of Contents|Acknowledgments|Contents)', para, re.IGNORECASE):
            continue

        # Check if this paragraph contains policy language
        if re.search(combined_pattern, para, re.IGNORECASE):
            # Get context to determine section
            context = "\n".join(paragraphs[max(0, i-20):i])
            section_marker, agency = find_current_section(context)

            # Clean up the text
            clean_text = re.sub(r'\s+', ' ', para).strip()

            # Skip if it's too long (probably multiple merged paragraphs)
            if len(clean_text) > 3000:
                clean_text = clean_text[:3000] + "..."

            policies.append((agency, section_marker, clean_text))

    return policies


def analyze_with_ollama(text: str, section: str, agency: str) -> dict:
    """Use Ollama to analyze a policy block."""
    client = ollama.Client(host=OLLAMA_HOST)

    prompt = f"""Analyze this policy proposal from Project 2025's section on {agency}.

TEXT:
{text[:2500]}

Provide a JSON response with:
{{
    "title": "A clear, concise title (5-10 words) describing the specific policy action",
    "summary": "A 1-2 sentence plain-language summary of what this policy would do and who it affects",
    "category": "One of: immigration, environment, healthcare, education, civil_rights, labor, economy, defense, justice, government_structure, foreign_policy, energy, housing, general",
    "action_type": "One of: eliminate, restructure, reduce, create, modify, privatize, repeal",
    "priority": "high, medium, or low based on urgency language in the text",
    "timeline": "day_one, first_100_days, first_year, long_term, or unknown",
    "is_policy": true if this contains a specific actionable policy recommendation, false if it's just background or commentary,
    "confidence": 0.0-1.0 (how confident that this is a clear, actionable policy proposal)
}}

Rules:
- The title should describe the SPECIFIC action, not just the topic
- If the text says "eliminate" or "abolish", use action_type "eliminate"
- If the text mentions "Day One" or "immediately", priority should be "high"
- Only set is_policy=true if there's a concrete action recommended

Respond with ONLY valid JSON, no other text."""

    try:
        response = client.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            options={"temperature": 0.2, "num_predict": 500}
        )

        content = response.get("response", "")
        # Extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"    Ollama error: {e}")

    return {
        "title": "Unknown Policy",
        "summary": "",
        "category": "general",
        "action_type": "unknown",
        "priority": "medium",
        "timeline": "unknown",
        "is_policy": False,
        "confidence": 0.0
    }


def extract_policies(input_path: str, use_ai: bool = True, verbose: bool = True) -> list[Policy]:
    """Extract all policies from the text file."""
    policies = []

    if verbose:
        print(f"Reading: {input_path}")

    with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    if verbose:
        print(f"Document length: {len(text):,} characters")

    # Extract policy paragraphs
    policy_paragraphs = extract_policy_paragraphs(text)

    if verbose:
        print(f"Found {len(policy_paragraphs)} potential policy paragraphs")

    for i, (agency, section, para_text) in enumerate(policy_paragraphs):
        if verbose:
            print(f"\n[{i+1}/{len(policy_paragraphs)}] {agency}")
            print(f"  Text preview: {para_text[:100]}...")

        if use_ai:
            analysis = analyze_with_ollama(para_text, section, agency)

            # Skip non-policies
            if not analysis.get("is_policy", False):
                if verbose:
                    print(f"  Skipped: not a specific policy")
                continue

            # Skip low-confidence extractions
            if analysis.get("confidence", 0) < 0.5:
                if verbose:
                    print(f"  Skipped: low confidence ({analysis.get('confidence')})")
                continue

            policy = Policy(
                section=section,
                agency=agency,
                raw_text=para_text,
                title=analysis.get("title", "Unknown"),
                summary=analysis.get("summary", ""),
                category=analysis.get("category", "general"),
                action_type=analysis.get("action_type", "unknown"),
                priority=analysis.get("priority", "medium"),
                timeline=analysis.get("timeline", "unknown"),
                confidence=analysis.get("confidence", 0.5),
            )

            if verbose:
                print(f"  Added: {policy.title}")
                print(f"  Category: {policy.category}, Priority: {policy.priority}")
        else:
            policy = Policy(
                section=section,
                agency=agency,
                raw_text=para_text,
            )

        policies.append(policy)

    return policies


def save_to_json(policies: list[Policy], output_path: str):
    """Save policies to JSON file."""
    data = [asdict(p) for p in policies]
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved {len(policies)} policies to {output_path}")


def update_database(policies: list[Policy], db_path: str = None):
    """Update the database with extracted policies."""
    from civitas.db.models import Project2025Policy
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    if db_path is None:
        db_path = os.getenv("CIVITAS_DB_PATH", "civitas.db")

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()

    # Clear existing policies
    deleted = session.query(Project2025Policy).delete()
    print(f"Deleted {deleted} existing policies")
    session.commit()

    # Add new policies
    for p in policies:
        db_policy = Project2025Policy(
            section=p.section,
            agency=p.agency,
            proposal_text=p.raw_text,
            proposal_summary=p.summary,
            page_number=0,  # Not applicable for text extraction
            category=p.category,
            action_type=p.action_type,
            priority=p.priority,
            implementation_timeline=p.timeline,
            status=p.status,
            confidence=p.confidence,
            title=p.title,
            title_short=p.title[:100] if p.title else None,
            title_full=p.title,
        )
        session.add(db_policy)

    session.commit()
    print(f"Added {len(policies)} new policies to database")
    session.close()


def main():
    parser = argparse.ArgumentParser(description="Extract P2025 policies from text file")
    parser.add_argument("--input", required=True, help="Path to mandate text file")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--update-db", action="store_true", help="Update database directly")
    parser.add_argument("--db-path", help="Database path (default: civitas.db)")
    parser.add_argument("--no-ai", action="store_true", help="Skip AI analysis")
    parser.add_argument("--quiet", action="store_true", help="Reduce output")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found at {args.input}")
        sys.exit(1)

    policies = extract_policies(
        args.input,
        use_ai=not args.no_ai,
        verbose=not args.quiet
    )

    print(f"\n{'='*60}")
    print(f"Extracted {len(policies)} quality policies")

    # Show category breakdown
    categories = {}
    for p in policies:
        categories[p.category] = categories.get(p.category, 0) + 1

    print("\nBy category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Show priority breakdown
    priorities = {}
    for p in policies:
        priorities[p.priority] = priorities.get(p.priority, 0) + 1

    print("\nBy priority:")
    for pri, count in sorted(priorities.items(), key=lambda x: -x[1]):
        print(f"  {pri}: {count}")

    if args.output:
        save_to_json(policies, args.output)

    if args.update_db:
        update_database(policies, args.db_path)


if __name__ == "__main__":
    main()
