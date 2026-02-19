#!/usr/bin/env python3
"""Extract quality Project 2025 policy proposals from the Mandate for Leadership PDF.

This script extracts complete policy proposals (not sentence fragments) and uses
Ollama to categorize, summarize, and assess each one.

Usage:
    python scripts/extract_p2025_policies.py --pdf data/project2025/mandate.pdf --output data/project2025/policies.json

    # To update database directly:
    python scripts/extract_p2025_policies.py --pdf data/project2025/mandate.pdf --update-db
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
    import pdfplumber
except ImportError:
    print("Install pdfplumber: pip install pdfplumber")
    sys.exit(1)

try:
    import ollama
except ImportError:
    print("Install ollama: pip install ollama")
    sys.exit(1)


# Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://ollama.baytides.org")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct-q8_0")


@dataclass
class Policy:
    """A complete policy proposal from Project 2025."""
    section: str
    agency: str
    page_start: int
    page_end: int
    raw_text: str
    title: str = ""
    summary: str = ""
    category: str = "general"
    action_type: str = "unknown"
    priority: str = "medium"
    timeline: str = "unknown"
    status: str = "not_started"
    confidence: float = 0.0


# Document sections with their page ranges and primary agency
SECTIONS = [
    ("Taking the Reins of Government", 1, 30, "Executive Office of the President"),
    ("White House Office", 31, 54, "White House Office"),
    ("Executive Office of the President", 55, 76, "Executive Office of the President"),
    ("Office of Management and Budget", 77, 94, "Office of Management and Budget"),
    ("National Security Council", 95, 110, "National Security Council"),
    ("Office of Science and Technology", 111, 124, "Office of Science and Technology"),
    ("Department of State", 169, 216, "Department of State"),
    ("Department of Defense", 95, 168, "Department of Defense"),
    ("Department of Homeland Security", 133, 168, "Department of Homeland Security"),
    ("Department of Justice", 545, 586, "Department of Justice"),
    ("Department of the Interior", 521, 544, "Department of the Interior"),
    ("Department of Agriculture", 291, 328, "Department of Agriculture"),
    ("Department of Commerce", 665, 702, "Department of Commerce"),
    ("Department of Labor", 591, 628, "Department of Labor"),
    ("Department of Health and Human Services", 449, 502, "Department of Health and Human Services"),
    ("Department of Housing and Urban Development", 503, 520, "Department of Housing and Urban Development"),
    ("Department of Transportation", 629, 664, "Department of Transportation"),
    ("Department of Energy", 363, 416, "Department of Energy"),
    ("Department of Education", 319, 362, "Department of Education"),
    ("Department of Veterans Affairs", 645, 664, "Department of Veterans Affairs"),
    ("Environmental Protection Agency", 417, 448, "Environmental Protection Agency"),
    ("Small Business Administration", 755, 774, "Small Business Administration"),
    ("Intelligence Community", 197, 216, "Intelligence Community"),
    ("Independent Regulatory Agencies", 829, 870, "Independent Regulatory Agencies"),
    ("Financial Regulatory Agencies", 703, 740, "Financial Regulatory Agencies"),
    ("Federal Communications Commission", 775, 798, "Federal Communications Commission"),
    ("Federal Election Commission", 799, 810, "Federal Election Commission"),
    ("Federal Trade Commission", 811, 828, "Federal Trade Commission"),
]


def extract_section_text(pdf, section_name: str, start_page: int, end_page: int) -> str:
    """Extract text from a section of the PDF."""
    text_parts = []
    for page_num in range(start_page - 1, min(end_page, len(pdf.pages))):
        page = pdf.pages[page_num]
        text = page.extract_text() or ""
        text_parts.append(text)
    return "\n".join(text_parts)


def find_policy_blocks(text: str) -> list[str]:
    """Find distinct policy proposal blocks in text.

    Looks for numbered recommendations, bullet points, or distinct paragraphs
    that contain actionable policy language.
    """
    # Patterns that indicate policy recommendations
    policy_indicators = [
        r"The (?:next |new )?(?:Administration|President|Congress) should",
        r"(?:The )?(?:Department|Agency|Office|EPA|DOJ|DHS) should",
        r"(?:Congress|Legislature) should",
        r"(?:Must|Should|Will) (?:eliminate|abolish|repeal|restructure|reform|create|establish)",
        r"(?:Recommendation|Proposal|Action Item):",
        r"Day (?:One|1)",
        r"(?:First|Within) (?:100|hundred) days",
        r"(?:Immediately|Urgently) (?:terminate|end|stop|begin|start)",
    ]

    # Split into paragraphs
    paragraphs = re.split(r'\n\s*\n', text)

    policy_blocks = []
    current_block = []

    for para in paragraphs:
        para = para.strip()
        if len(para) < 100:  # Skip very short paragraphs
            continue

        # Check if this paragraph contains policy language
        is_policy = any(re.search(pattern, para, re.IGNORECASE) for pattern in policy_indicators)

        if is_policy:
            # Start a new block or add to current
            if current_block:
                policy_blocks.append("\n\n".join(current_block))
            current_block = [para]
        elif current_block:
            # Continue current block if it's related context
            if len(current_block) < 3:  # Limit block size
                current_block.append(para)
            else:
                policy_blocks.append("\n\n".join(current_block))
                current_block = []

    # Don't forget the last block
    if current_block:
        policy_blocks.append("\n\n".join(current_block))

    return policy_blocks


def analyze_with_ollama(text: str, section: str, agency: str) -> dict:
    """Use Ollama to analyze a policy block."""
    client = ollama.Client(host=OLLAMA_HOST)

    prompt = f"""Analyze this policy proposal from Project 2025's "{section}" section for the {agency}.

TEXT:
{text[:3000]}

Provide a JSON response with:
{{
    "title": "A clear, concise title (5-10 words) describing the policy",
    "summary": "A 1-2 sentence plain-language summary of what this policy would do",
    "category": "One of: immigration, environment, healthcare, education, civil_rights, labor, economy, defense, justice, government_structure, foreign_policy, energy, housing, general",
    "action_type": "One of: eliminate, restructure, reduce, create, modify, privatize, repeal",
    "priority": "high, medium, or low based on urgency language",
    "timeline": "day_one, first_100_days, first_year, long_term, or unknown",
    "is_policy": true/false (is this actually a policy proposal or just background?),
    "confidence": 0.0-1.0 (how confident are you this is an actionable policy?)
}}

Respond with ONLY valid JSON, no other text."""

    try:
        response = client.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            options={"temperature": 0.2}
        )

        content = response.get("response", "")
        # Extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"Ollama error: {e}")

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


def extract_policies(pdf_path: str, use_ai: bool = True, verbose: bool = True) -> list[Policy]:
    """Extract all policies from the PDF."""
    policies = []

    if verbose:
        print(f"Opening PDF: {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        if verbose:
            print(f"PDF has {len(pdf.pages)} pages")

        for section_name, start_page, end_page, agency in SECTIONS:
            if verbose:
                print(f"\nProcessing: {section_name} (pages {start_page}-{end_page})")

            text = extract_section_text(pdf, section_name, start_page, end_page)
            policy_blocks = find_policy_blocks(text)

            if verbose:
                print(f"  Found {len(policy_blocks)} potential policy blocks")

            for i, block in enumerate(policy_blocks):
                if use_ai:
                    if verbose:
                        print(f"  Analyzing block {i+1}/{len(policy_blocks)}...")

                    analysis = analyze_with_ollama(block, section_name, agency)

                    # Skip non-policies
                    if not analysis.get("is_policy", False):
                        if verbose:
                            print(f"    Skipped: not a policy")
                        continue

                    # Skip low-confidence extractions
                    if analysis.get("confidence", 0) < 0.5:
                        if verbose:
                            print(f"    Skipped: low confidence ({analysis.get('confidence')})")
                        continue

                    policy = Policy(
                        section=section_name,
                        agency=agency,
                        page_start=start_page,
                        page_end=end_page,
                        raw_text=block[:2000],  # Limit text size
                        title=analysis.get("title", "Unknown"),
                        summary=analysis.get("summary", ""),
                        category=analysis.get("category", "general"),
                        action_type=analysis.get("action_type", "unknown"),
                        priority=analysis.get("priority", "medium"),
                        timeline=analysis.get("timeline", "unknown"),
                        confidence=analysis.get("confidence", 0.5),
                    )
                else:
                    policy = Policy(
                        section=section_name,
                        agency=agency,
                        page_start=start_page,
                        page_end=end_page,
                        raw_text=block[:2000],
                    )

                policies.append(policy)

                if verbose:
                    print(f"    Added: {policy.title[:50]}...")

    return policies


def save_to_json(policies: list[Policy], output_path: str):
    """Save policies to JSON file."""
    data = [asdict(p) for p in policies]
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(policies)} policies to {output_path}")


def update_database(policies: list[Policy], db_path: str = None):
    """Update the database with extracted policies."""
    from civitas.db.models import Base, Project2025Policy
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    if db_path is None:
        db_path = os.getenv("CIVITAS_DB_PATH", "civitas.db")

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()

    # Clear existing policies
    session.query(Project2025Policy).delete()
    session.commit()

    # Add new policies
    for p in policies:
        db_policy = Project2025Policy(
            section=p.section,
            agency=p.agency,
            proposal_text=p.raw_text,
            proposal_summary=p.summary,
            page_number=p.page_start,
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
    print(f"Updated database with {len(policies)} policies")
    session.close()


def main():
    parser = argparse.ArgumentParser(description="Extract P2025 policies from PDF")
    parser.add_argument("--pdf", required=True, help="Path to Mandate for Leadership PDF")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--update-db", action="store_true", help="Update database directly")
    parser.add_argument("--db-path", help="Database path (default: civitas.db)")
    parser.add_argument("--no-ai", action="store_true", help="Skip AI analysis")
    parser.add_argument("--quiet", action="store_true", help="Reduce output")

    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        print(f"Error: PDF not found at {args.pdf}")
        sys.exit(1)

    policies = extract_policies(
        args.pdf,
        use_ai=not args.no_ai,
        verbose=not args.quiet
    )

    print(f"\nExtracted {len(policies)} quality policies")

    # Show category breakdown
    categories = {}
    for p in policies:
        categories[p.category] = categories.get(p.category, 0) + 1
    print("\nBy category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    if args.output:
        save_to_json(policies, args.output)

    if args.update_db:
        update_database(policies, args.db_path)


if __name__ == "__main__":
    main()
