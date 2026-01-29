#!/usr/bin/env python3
"""Extract justice authors from SCOTUS opinion text and link to JusticeOpinion records.

Court Listener API often doesn't include author in metadata, but the opinion
text itself contains the author information in standardized formats.

Usage:
    python scripts/extract_authors_from_text.py --db /opt/civitas/civitas.db
"""

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy.orm import Session

from civitas.db.models import Base, CourtCase, Justice, JusticeOpinion, get_engine

# Common SCOTUS justice last names (historical and current)
KNOWN_JUSTICES = {
    # Current
    "roberts", "thomas", "alito", "sotomayor", "kagan", "gorsuch",
    "kavanaugh", "barrett", "jackson",
    # Recent
    "breyer", "ginsburg", "kennedy", "scalia", "souter", "stevens",
    "o'connor", "rehnquist",
    # Historical (major)
    "marshall", "warren", "burger", "white", "blackmun", "powell",
    "brennan", "stewart", "harlan", "douglas", "clark", "frankfurter",
    "black", "reed", "murphy", "rutledge", "burton", "vinson", "minton",
    "jackson", "stone", "roberts", "cardozo", "brandeis", "hughes",
    "holmes", "taft", "mcreynolds", "sutherland", "butler", "sanford",
    "day", "mckenna", "moody", "brewer", "brown", "shiras", "white",
    "peckham", "mckenna", "fuller", "field", "miller", "davis", "strong",
    "bradley", "hunt", "waite", "clifford", "swayne", "grier", "wayne",
    "catron", "daniel", "woodbury", "mclean", "barbour", "taney",
    "baldwin", "thompson", "trimble", "duvall", "story", "todd",
    "livingston", "johnson", "washington", "chase", "moore", "paterson",
    "iredell", "wilson", "cushing", "blair", "rutledge", "jay",
}


def extract_authors_from_text(text: str | None) -> dict[str, list[str]]:
    """Extract author names from opinion text.

    Returns dict with keys: majority, dissent, concurrence
    """
    if not text:
        return {"majority": [], "dissent": [], "concurrence": []}

    authors: dict[str, list[str]] = {
        "majority": [],
        "dissent": [],
        "concurrence": [],
    }

    # Normalize whitespace
    text_clean = " ".join(text.split())
    text_upper = text_clean.upper()

    # Pattern 1: "JUSTICE NAME delivered the opinion"
    # Pattern 2: "NAME, J., [dissenting|concurring|opinion]"
    # Pattern 3: "Opinion of JUSTICE NAME"
    # Pattern 4: "MR. JUSTICE NAME delivered"
    # Pattern 5: "Statement of NAME, J."

    patterns = [
        # Majority patterns
        (
            r"(?:CHIEF\s+)?JUSTICE\s+([A-Z][A-Z']+)\s+delivered\s+the\s+opinion",
            "majority",
        ),
        (r"MR\.?\s+(?:CHIEF\s+)?JUSTICE\s+([A-Z][A-Za-z']+)\s+delivered", "majority"),
        (r"Opinion\s+of\s+(?:the\s+Court\s+by\s+)?(?:CHIEF\s+)?JUSTICE\s+([A-Z][A-Z']+)", "majority"),
        (r"([A-Z][A-Z']+),\s*(?:C\.?\s*)?J\.?,?\s+delivered\s+the\s+opinion", "majority"),
        # Dissent patterns
        (r"([A-Z][A-Z']+),\s*(?:C\.?\s*)?J\.?,?\s+dissenting", "dissent"),
        (r"(?:CHIEF\s+)?JUSTICE\s+([A-Z][A-Z']+)\s+(?:filed\s+a\s+)?dissent", "dissent"),
        (r"Statement\s+of\s+([A-Z][A-Z']+),\s*J\.?,?\s+dissenting", "dissent"),
        # Concurrence patterns
        (r"([A-Z][A-Z']+),\s*(?:C\.?\s*)?J\.?,?\s+concurring", "concurrence"),
        (r"(?:CHIEF\s+)?JUSTICE\s+([A-Z][A-Z']+)\s+(?:filed\s+a\s+)?concur", "concurrence"),
        (r"Statement\s+of\s+([A-Z][A-Z']+),\s*J\.?,?\s+concurring", "concurrence"),
    ]

    # Search in first 5000 chars (where authorship usually appears)
    search_text = text_clean[:5000]

    for pattern, opinion_type in patterns:
        for match in re.finditer(pattern, search_text, re.IGNORECASE):
            name = match.group(1).title()
            # Validate it's a known justice
            if name.lower() in KNOWN_JUSTICES:
                if name not in authors[opinion_type]:
                    authors[opinion_type].append(name)

    # Also check for "NAME, J." standalone pattern at start of opinion
    # This often indicates the author when it appears first
    standalone_pattern = r"^[^\n]*?([A-Z][A-Z']+),\s*(?:C\.?\s*)?J\."
    match = re.search(standalone_pattern, text_clean[:500])
    if match:
        name = match.group(1).title()
        if name.lower() in KNOWN_JUSTICES:
            # Determine type from context
            context = text_clean[:500].lower()
            if "dissent" in context:
                if name not in authors["dissent"]:
                    authors["dissent"].append(name)
            elif "concur" in context:
                if name not in authors["concurrence"]:
                    authors["concurrence"].append(name)
            elif not authors["majority"]:
                authors["majority"].append(name)

    return authors


def main():
    parser = argparse.ArgumentParser(
        description="Extract authors from SCOTUS opinion text and link to justices"
    )
    parser.add_argument("--db", type=str, default="civitas.db", help="Database path")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without saving"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of cases to process"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("SCOTUS Author Extractor")
    print("=" * 60)
    print(f"Database: {args.db}")
    print(f"Dry run: {args.dry_run}")
    print()

    engine = get_engine(args.db)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Build justice lookup
        justices = session.query(Justice).all()
        last_name_to_id = {j.last_name.lower(): j.id for j in justices}

        print(f"Loaded {len(justices)} justices in database")
        print()

        # Find cases with opinion text but no linked majority opinion
        query = session.query(CourtCase).filter(
            CourtCase.court_level == "scotus",
            CourtCase.majority_opinion.isnot(None),
        )

        if args.limit:
            query = query.limit(args.limit)

        cases = query.all()
        print(f"Processing {len(cases)} SCOTUS cases with opinion text")

        stats = {
            "processed": 0,
            "authors_found": 0,
            "new_links_created": 0,
            "authors_updated": 0,
        }

        for case in cases:
            stats["processed"] += 1

            # Extract authors from text
            authors = extract_authors_from_text(case.majority_opinion)

            # Check if we found a majority author
            if authors["majority"]:
                author_name = authors["majority"][0]
                justice_id = last_name_to_id.get(author_name.lower())

                stats["authors_found"] += 1

                # Update case.majority_author if empty
                if not case.majority_author and not args.dry_run:
                    case.majority_author = author_name
                    stats["authors_updated"] += 1

                # Create JusticeOpinion link if doesn't exist
                existing = (
                    session.query(JusticeOpinion)
                    .filter(
                        JusticeOpinion.court_case_id == case.id,
                        JusticeOpinion.opinion_type == "majority",
                    )
                    .first()
                )

                if not existing and not args.dry_run:
                    opinion = JusticeOpinion(
                        court_case_id=case.id,
                        justice_id=justice_id,
                        author_name=author_name,
                        opinion_type="majority",
                        created_at=datetime.now(UTC),
                    )
                    session.add(opinion)
                    stats["new_links_created"] += 1

            # Also create links for dissents and concurrences
            for author_name in authors.get("dissent", []):
                justice_id = last_name_to_id.get(author_name.lower())
                existing = (
                    session.query(JusticeOpinion)
                    .filter(
                        JusticeOpinion.court_case_id == case.id,
                        JusticeOpinion.author_name == author_name,
                        JusticeOpinion.opinion_type == "dissent",
                    )
                    .first()
                )
                if not existing and not args.dry_run:
                    session.add(
                        JusticeOpinion(
                            court_case_id=case.id,
                            justice_id=justice_id,
                            author_name=author_name,
                            opinion_type="dissent",
                            created_at=datetime.now(UTC),
                        )
                    )
                    stats["new_links_created"] += 1

            for author_name in authors.get("concurrence", []):
                justice_id = last_name_to_id.get(author_name.lower())
                existing = (
                    session.query(JusticeOpinion)
                    .filter(
                        JusticeOpinion.court_case_id == case.id,
                        JusticeOpinion.author_name == author_name,
                        JusticeOpinion.opinion_type == "concurrence",
                    )
                    .first()
                )
                if not existing and not args.dry_run:
                    session.add(
                        JusticeOpinion(
                            court_case_id=case.id,
                            justice_id=justice_id,
                            author_name=author_name,
                            opinion_type="concurrence",
                            created_at=datetime.now(UTC),
                        )
                    )
                    stats["new_links_created"] += 1

            # Commit periodically
            if not args.dry_run and stats["processed"] % 500 == 0:
                session.commit()
                print(f"  Progress: {stats['processed']} processed, {stats['new_links_created']} links created...")

        if not args.dry_run:
            session.commit()

        print()
        print("=" * 60)
        print("Results")
        print("=" * 60)
        print(f"Cases processed: {stats['processed']}")
        print(f"Authors found in text: {stats['authors_found']}")
        print(f"Case authors updated: {stats['authors_updated']}")
        print(f"New opinion links created: {stats['new_links_created']}")

        # Final stats per justice
        print()
        print("Final JusticeOpinion counts (active justices):")
        for j in justices:
            if j.is_active:
                count = (
                    session.query(JusticeOpinion)
                    .filter(JusticeOpinion.justice_id == j.id)
                    .count()
                )
                print(f"  {j.name}: {count}")


if __name__ == "__main__":
    main()
