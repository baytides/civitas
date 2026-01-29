#!/usr/bin/env python3
"""Link all SCOTUS cases with authors to JusticeOpinion records.

This script fixes the data gap where cases have majority_author but no
corresponding JusticeOpinion link to the justice.

Usage:
    python scripts/link_all_opinions.py --db /opt/civitas/civitas.db
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy.orm import Session

from civitas.db.models import Base, CourtCase, Justice, JusticeOpinion, get_engine


def normalize_author_name(name: str | None) -> str | None:
    """Normalize author name for matching."""
    if not name:
        return None
    # Convert to lowercase and clean up
    name = name.lower().strip()
    # Remove common suffixes
    for suffix in ["jr.", "jr", "sr.", "sr", "iii", "ii", "i"]:
        name = name.replace(suffix, "")
    return " ".join(name.split())


def extract_last_name(full_name: str | None) -> str | None:
    """Extract last name from full name."""
    if not full_name:
        return None
    normalized = normalize_author_name(full_name)
    if not normalized:
        return None
    parts = normalized.split()
    return parts[-1] if parts else None


def main():
    parser = argparse.ArgumentParser(
        description="Link SCOTUS cases with authors to JusticeOpinion records"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="civitas.db",
        help="Database path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("SCOTUS Opinion Linker")
    print("=" * 60)
    print(f"Database: {args.db}")
    print(f"Dry run: {args.dry_run}")
    print()

    engine = get_engine(args.db)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Build justice lookup maps
        justices = session.query(Justice).all()
        last_name_to_id = {}
        full_name_to_id = {}

        for j in justices:
            last_name_to_id[j.last_name.lower()] = j.id
            full_name_to_id[normalize_author_name(j.name)] = j.id

        print(f"Loaded {len(justices)} justices")
        print()

        # Find all SCOTUS cases with majority_author but no JusticeOpinion
        cases_with_author = (
            session.query(CourtCase)
            .filter(
                CourtCase.court_level == "scotus",
                CourtCase.majority_author.isnot(None),
            )
            .all()
        )

        print(f"Found {len(cases_with_author)} SCOTUS cases with majority_author")

        linked = 0
        already_linked = 0
        unmatched = 0
        unmatched_names = {}

        for case in cases_with_author:
            # Check if already linked
            existing = (
                session.query(JusticeOpinion)
                .filter(
                    JusticeOpinion.court_case_id == case.id,
                    JusticeOpinion.opinion_type == "majority",
                )
                .first()
            )

            if existing:
                already_linked += 1
                continue

            # Try to find justice by last name
            author_last = extract_last_name(case.majority_author)
            justice_id = None

            if author_last:
                justice_id = last_name_to_id.get(author_last)

            # Try full name if last name didn't match
            if not justice_id:
                normalized = normalize_author_name(case.majority_author)
                if normalized:
                    justice_id = full_name_to_id.get(normalized)

            if justice_id:
                if not args.dry_run:
                    opinion = JusticeOpinion(
                        court_case_id=case.id,
                        justice_id=justice_id,
                        author_name=case.majority_author,
                        opinion_type="majority",
                        created_at=datetime.now(UTC),
                    )
                    session.add(opinion)
                linked += 1
            else:
                unmatched += 1
                name = case.majority_author or "Unknown"
                unmatched_names[name] = unmatched_names.get(name, 0) + 1

            # Commit periodically
            if not args.dry_run and linked % 500 == 0 and linked > 0:
                session.commit()
                print(f"  Progress: {linked} linked...")

        if not args.dry_run:
            session.commit()

        print()
        print("=" * 60)
        print("Results")
        print("=" * 60)
        print(f"Already linked: {already_linked}")
        print(f"Newly linked: {linked}")
        print(f"Unmatched (no justice found): {unmatched}")

        if unmatched_names:
            print()
            print("Top unmatched author names:")
            sorted_unmatched = sorted(unmatched_names.items(), key=lambda x: -x[1])[:20]
            for name, count in sorted_unmatched:
                print(f"  {name}: {count}")

        # Final stats
        print()
        print("Final JusticeOpinion counts by active justice:")
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
