#!/usr/bin/env python3
"""Seed database with curated P2025 policies.

These are manually extracted key policies from the Mandate for Leadership
that are most likely to be implemented and have the highest impact.

Usage:
    python scripts/seed_p2025_policies.py --db-path /opt/civitas/civitas.db
"""

import argparse
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Curated high-priority P2025 policies
# Source: Project 2025 Mandate for Leadership
CURATED_POLICIES = [
    # IMMIGRATION
    {
        "section": "Department of Homeland Security",
        "agency": "Department of Homeland Security",
        "short_title": "Eliminate DACA and rescind work permits for Dreamers",
        "proposal_summary": (
            "Terminate the Deferred Action for Childhood Arrivals (DACA) program, "
            "rescinding work authorization and deportation protections for approximately "
            "600,000 individuals who were brought to the US as children."
        ),
        "category": "immigration",
        "action_type": "eliminate",
        "priority": "high",
        "implementation_timeline": "first_100_days",
        "status": "not_started",
        "confidence": 0.95,
    },
    {
        "section": "Department of Homeland Security",
        "agency": "Department of Homeland Security",
        "short_title": "Resume border wall construction on Day One",
        "proposal_summary": (
            "Immediately resume construction of the southern border wall using "
            "emergency military funding and repurposed federal dollars, completing "
            "the physical barrier across the entire US-Mexico border."
        ),
        "category": "immigration",
        "action_type": "create",
        "priority": "high",
        "implementation_timeline": "day_one",
        "status": "not_started",
        "confidence": 0.95,
    },
    {
        "section": "Department of Homeland Security",
        "agency": "Department of Homeland Security",
        "short_title": "Invoke Alien Enemies Act for mass deportations",
        "proposal_summary": (
            "Use the Alien Enemies Act of 1798 to enable mass deportations without "
            "individual hearings, targeting specific nationalities and groups."
        ),
        "category": "immigration",
        "action_type": "create",
        "priority": "high",
        "implementation_timeline": "first_100_days",
        "status": "not_started",
        "confidence": 0.85,
    },
    {
        "section": "Department of Homeland Security",
        "agency": "Department of Homeland Security",
        "short_title": "End birthright citizenship for children of undocumented",
        "proposal_summary": (
            "Issue executive order challenging birthright citizenship guaranteed by "
            "the 14th Amendment, denying citizenship to children born in the US to "
            "undocumented parents."
        ),
        "category": "immigration",
        "action_type": "eliminate",
        "priority": "high",
        "implementation_timeline": "first_100_days",
        "status": "not_started",
        "confidence": 0.90,
    },
    # ENVIRONMENT
    {
        "section": "Environmental Protection Agency",
        "agency": "Environmental Protection Agency",
        "short_title": "Repeal EPA regulations on carbon emissions",
        "proposal_summary": (
            "Eliminate EPA regulations limiting carbon dioxide emissions from power "
            "plants, vehicles, and industrial facilities. Withdraw from enforcement "
            "of the Clean Air Act provisions related to climate change."
        ),
        "category": "environment",
        "action_type": "eliminate",
        "priority": "high",
        "implementation_timeline": "first_100_days",
        "status": "not_started",
        "confidence": 0.95,
    },
    {
        "section": "Department of Energy",
        "agency": "Department of Energy",
        "short_title": "Maximize fossil fuel production on federal lands",
        "proposal_summary": (
            "Open all federal lands and waters to oil, gas, and coal leasing. "
            "Expedite permitting for drilling, pipelines, and refineries. "
            "Reverse Biden administration's pause on LNG export approvals."
        ),
        "category": "energy",
        "action_type": "create",
        "priority": "high",
        "implementation_timeline": "day_one",
        "status": "not_started",
        "confidence": 0.95,
    },
    {
        "section": "Environmental Protection Agency",
        "agency": "Environmental Protection Agency",
        "short_title": "Dismantle EPA climate programs and reduce staff by 50%",
        "proposal_summary": (
            "Eliminate climate-related programs at EPA, reduce agency staff by 50%, "
            "and transfer remaining functions to states. End participation in "
            "international climate agreements."
        ),
        "category": "environment",
        "action_type": "eliminate",
        "priority": "high",
        "implementation_timeline": "first_year",
        "status": "not_started",
        "confidence": 0.90,
    },
    # EDUCATION
    {
        "section": "Department of Education",
        "agency": "Department of Education",
        "short_title": "Abolish the Department of Education",
        "proposal_summary": (
            "Eliminate the federal Department of Education entirely, transferring "
            "limited functions to other agencies and returning education policy "
            "entirely to states. End federal student loan programs."
        ),
        "category": "education",
        "action_type": "eliminate",
        "priority": "high",
        "implementation_timeline": "first_year",
        "status": "not_started",
        "confidence": 0.85,
    },
    {
        "section": "Department of Education",
        "agency": "Department of Education",
        "short_title": "End Title IX protections for transgender students",
        "proposal_summary": (
            "Rescind Biden administration Title IX rules protecting transgender "
            "students. Prohibit transgender athletes from competing consistent with "
            "their gender identity. Remove gender identity from civil rights protections."
        ),
        "category": "civil_rights",
        "action_type": "eliminate",
        "priority": "high",
        "implementation_timeline": "day_one",
        "status": "not_started",
        "confidence": 0.95,
    },
    {
        "section": "Department of Education",
        "agency": "Department of Education",
        "short_title": "Ban diversity and inclusion programs in schools",
        "proposal_summary": (
            "Prohibit federal funding for schools that implement diversity, equity, "
            "and inclusion (DEI) programs, critical race theory curriculum, or "
            "gender identity education."
        ),
        "category": "education",
        "action_type": "eliminate",
        "priority": "high",
        "implementation_timeline": "first_100_days",
        "status": "not_started",
        "confidence": 0.90,
    },
    # HEALTHCARE
    {
        "section": "Department of Health and Human Services",
        "agency": "Department of Health and Human Services",
        "short_title": "Restrict abortion access through FDA and HHS actions",
        "proposal_summary": (
            "Revoke FDA approval of mifepristone, restrict mail-order abortion "
            "medications, and enforce Comstock Act provisions to prohibit mailing "
            "of abortion-related materials."
        ),
        "category": "healthcare",
        "action_type": "eliminate",
        "priority": "high",
        "implementation_timeline": "first_100_days",
        "status": "not_started",
        "confidence": 0.90,
    },
    {
        "section": "Department of Health and Human Services",
        "agency": "Department of Health and Human Services",
        "short_title": "Remove contraception mandate from ACA",
        "proposal_summary": (
            "Eliminate the Affordable Care Act's requirement that insurance plans "
            "cover contraception without cost-sharing. Expand religious exemptions "
            "for employers who object to covering birth control."
        ),
        "category": "healthcare",
        "action_type": "eliminate",
        "priority": "medium",
        "implementation_timeline": "first_year",
        "status": "not_started",
        "confidence": 0.85,
    },
    {
        "section": "Department of Health and Human Services",
        "agency": "Department of Health and Human Services",
        "short_title": "Block Medicaid expansion and add work requirements",
        "proposal_summary": (
            "Convert Medicaid to state block grants with reduced federal funding. "
            "Add work requirements for able-bodied adults. Cap enrollment and "
            "allow states to reduce benefits."
        ),
        "category": "healthcare",
        "action_type": "restructure",
        "priority": "high",
        "implementation_timeline": "first_year",
        "status": "not_started",
        "confidence": 0.85,
    },
    # CIVIL RIGHTS
    {
        "section": "Department of Justice",
        "agency": "Department of Justice",
        "short_title": "Eliminate DOJ Civil Rights Division functions",
        "proposal_summary": (
            "Restructure the DOJ Civil Rights Division to focus only on religious "
            "liberty cases. End enforcement of voting rights protections, fair "
            "housing laws, and employment discrimination claims."
        ),
        "category": "civil_rights",
        "action_type": "eliminate",
        "priority": "high",
        "implementation_timeline": "first_year",
        "status": "not_started",
        "confidence": 0.85,
    },
    {
        "section": "Office of Personnel Management",
        "agency": "Office of Personnel Management",
        "short_title": "Remove all federal DEI programs and positions",
        "proposal_summary": (
            "Eliminate all diversity, equity, and inclusion offices, programs, and "
            "positions across the federal government. Prohibit DEI training and "
            "affirmative action in federal hiring."
        ),
        "category": "civil_rights",
        "action_type": "eliminate",
        "priority": "high",
        "implementation_timeline": "day_one",
        "status": "not_started",
        "confidence": 0.95,
    },
    # LABOR
    {
        "section": "Department of Labor",
        "agency": "Department of Labor",
        "short_title": "Weaken overtime protections and minimum wage enforcement",
        "proposal_summary": (
            "Raise the salary threshold for overtime exemptions, reducing the number "
            "of workers eligible for overtime pay. Reduce enforcement of minimum "
            "wage violations and allow more independent contractor classifications."
        ),
        "category": "labor",
        "action_type": "reduce",
        "priority": "medium",
        "implementation_timeline": "first_year",
        "status": "not_started",
        "confidence": 0.80,
    },
    {
        "section": "National Labor Relations Board",
        "agency": "National Labor Relations Board",
        "short_title": "Restrict union organizing rights and collective bargaining",
        "proposal_summary": (
            "Reverse NLRB decisions expanding union organizing rights. Make it "
            "harder for workers to form unions. Limit collective bargaining scope "
            "and weaken strike protections."
        ),
        "category": "labor",
        "action_type": "reduce",
        "priority": "medium",
        "implementation_timeline": "first_year",
        "status": "not_started",
        "confidence": 0.80,
    },
    # GOVERNMENT STRUCTURE
    {
        "section": "Executive Office of the President",
        "agency": "Executive Office of the President",
        "short_title": "Implement Schedule F to fire career civil servants",
        "proposal_summary": (
            "Reclassify up to 50,000 federal employees as 'Schedule F' political "
            "appointees who can be fired at will. Replace career civil servants "
            "with loyalists across all agencies."
        ),
        "category": "government_structure",
        "action_type": "restructure",
        "priority": "high",
        "implementation_timeline": "day_one",
        "status": "not_started",
        "confidence": 0.95,
    },
    {
        "section": "Department of Justice",
        "agency": "Department of Justice",
        "short_title": "Place DOJ under direct White House control",
        "proposal_summary": (
            "End DOJ independence from the White House. Require all significant "
            "prosecutorial decisions to be approved by political appointees. "
            "Use DOJ to investigate political opponents."
        ),
        "category": "justice",
        "action_type": "restructure",
        "priority": "high",
        "implementation_timeline": "day_one",
        "status": "not_started",
        "confidence": 0.90,
    },
    {
        "section": "Federal Communications Commission",
        "agency": "Federal Communications Commission",
        "short_title": "Use FCC to pressure media outlets critical of administration",
        "proposal_summary": (
            "Review broadcast licenses of media companies critical of the "
            "administration. Use FCC regulatory power to pressure news coverage. "
            "Eliminate net neutrality protections permanently."
        ),
        "category": "government_structure",
        "action_type": "restructure",
        "priority": "medium",
        "implementation_timeline": "first_year",
        "status": "not_started",
        "confidence": 0.75,
    },
    # FOREIGN POLICY / DEFENSE
    {
        "section": "Department of Defense",
        "agency": "Department of Defense",
        "short_title": "Remove DEI and gender ideology from military",
        "proposal_summary": (
            "Ban diversity training in the military. Reverse policies allowing "
            "transgender service members. End military funding for abortion travel. "
            "Purge 'woke' officers."
        ),
        "category": "defense",
        "action_type": "eliminate",
        "priority": "high",
        "implementation_timeline": "day_one",
        "status": "not_started",
        "confidence": 0.90,
    },
    {
        "section": "Department of State",
        "agency": "Department of State",
        "short_title": "Withdraw from international climate agreements",
        "proposal_summary": (
            "Withdraw from the Paris Climate Agreement and all international "
            "climate commitments. End funding for UN climate programs. "
            "Exit or defund international environmental organizations."
        ),
        "category": "foreign_policy",
        "action_type": "eliminate",
        "priority": "high",
        "implementation_timeline": "day_one",
        "status": "not_started",
        "confidence": 0.95,
    },
    # ECONOMY / FINANCIAL
    {
        "section": "Consumer Financial Protection Bureau",
        "agency": "Consumer Financial Protection Bureau",
        "short_title": "Eliminate or severely restrict CFPB",
        "proposal_summary": (
            "Abolish the Consumer Financial Protection Bureau or transfer its "
            "functions to other agencies. End enforcement actions against "
            "predatory lenders, payday loans, and credit card companies."
        ),
        "category": "economy",
        "action_type": "eliminate",
        "priority": "high",
        "implementation_timeline": "first_year",
        "status": "not_started",
        "confidence": 0.85,
    },
    {
        "section": "Department of the Treasury",
        "agency": "Department of the Treasury",
        "short_title": "Make Trump tax cuts permanent and cut corporate rates",
        "proposal_summary": (
            "Make the 2017 Tax Cuts and Jobs Act provisions permanent. Further "
            "reduce corporate tax rates. Eliminate estate tax and capital gains "
            "taxes on inherited wealth."
        ),
        "category": "economy",
        "action_type": "modify",
        "priority": "high",
        "implementation_timeline": "first_year",
        "status": "not_started",
        "confidence": 0.85,
    },
]


def seed_database(db_path: str = None):
    """Seed database with curated P2025 policies."""
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

    # Add curated policies
    for p in CURATED_POLICIES:
        db_policy = Project2025Policy(
            section=p["section"],
            agency=p["agency"],
            proposal_text=p["proposal_summary"],  # Use summary as full text for now
            proposal_summary=p["proposal_summary"],
            page_number=0,
            category=p["category"],
            action_type=p["action_type"],
            priority=p["priority"],
            implementation_timeline=p["implementation_timeline"],
            status=p["status"],
            confidence=p["confidence"],
            short_title=p["short_title"],
        )
        session.add(db_policy)
        print(f"  Added: {p['short_title']}")

    session.commit()
    print(f"\nAdded {len(CURATED_POLICIES)} curated policies to database")
    session.close()


def main():
    parser = argparse.ArgumentParser(description="Seed P2025 policies")
    parser.add_argument("--db-path", help="Database path (default: civitas.db)")
    args = parser.parse_args()

    seed_database(args.db_path)


if __name__ == "__main__":
    main()
