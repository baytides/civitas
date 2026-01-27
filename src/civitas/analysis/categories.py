"""Comprehensive law categories for legislative analysis.

These categories cover all major policy areas, not just Project 2025.
Each category includes subcategories and keywords for AI classification.
"""

from dataclasses import dataclass, field


@dataclass
class LawCategory:
    """A category for classifying legislation."""

    slug: str
    name: str
    description: str
    subcategories: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    p2025_related: bool = False  # Whether this category has P2025 objectives
    # Keywords indicating anti-democratic action
    threat_keywords: list[str] = field(default_factory=list)
    resistance_keywords: list[str] = field(
        default_factory=list
    )  # Keywords indicating protective legislation


# Comprehensive categories covering all major policy areas
CATEGORIES: list[LawCategory] = [
    # === CIVIL RIGHTS & SOCIAL POLICY ===
    LawCategory(
        slug="civil_rights",
        name="Civil Rights & Liberties",
        description=(
            "Voting rights, discrimination, free speech, privacy, and constitutional protections"
        ),
        subcategories=[
            "voting_rights",
            "discrimination",
            "free_speech",
            "privacy",
            "religious_liberty",
            "lgbtq_rights",
            "disability_rights",
            "racial_justice",
        ],
        keywords=[
            "civil rights", "voting", "discrimination", "equal protection",
            "free speech", "privacy", "first amendment", "fourteenth amendment",
            "LGBTQ", "transgender", "marriage equality", "disability", "ADA",
            "racial", "minority", "affirmative action", "DEI", "diversity",
        ],
        p2025_related=True,
        threat_keywords=[
            "eliminate DEI", "ban gender", "restrict voting", "voter ID",
            "purge voter rolls", "limit mail voting", "religious exemption",
        ],
        resistance_keywords=[
            "protect voting", "expand access", "anti-discrimination",
            "civil rights protection", "equality act",
        ],
    ),

    LawCategory(
        slug="immigration",
        name="Immigration",
        description="Border policy, asylum, visas, deportation, and citizenship",
        subcategories=[
            "border_security",
            "asylum",
            "deportation",
            "visas",
            "citizenship",
            "refugees",
            "daca",
            "sanctuary",
        ],
        keywords=[
            "immigration", "border", "asylum", "deportation", "visa",
            "citizenship", "refugee", "DACA", "sanctuary", "ICE",
            "CBP", "migrant", "undocumented", "alien", "naturalization",
        ],
        p2025_related=True,
        threat_keywords=[
            "mass deportation", "end asylum", "terminate DACA", "border wall",
            "immigration enforcement", "detain", "expedited removal",
        ],
        resistance_keywords=[
            "sanctuary", "protect immigrants", "DACA protection", "asylum access",
            "immigrant rights", "pathway to citizenship",
        ],
    ),

    # === HEALTHCARE ===
    LawCategory(
        slug="healthcare",
        name="Healthcare",
        description="Health insurance, Medicaid/Medicare, public health, and medical policy",
        subcategories=[
            "health_insurance",
            "medicaid",
            "medicare",
            "public_health",
            "mental_health",
            "pharmaceuticals",
            "hospitals",
            "pandemic",
        ],
        keywords=[
            "healthcare", "health insurance", "Medicaid", "Medicare", "ACA",
            "Affordable Care Act", "Obamacare", "public health", "mental health",
            "prescription", "pharmaceutical", "hospital", "medical",
            "pandemic", "vaccine", "CDC", "FDA", "NIH",
        ],
        p2025_related=True,
        threat_keywords=[
            "repeal ACA", "block grant Medicaid", "work requirements",
            "eliminate coverage", "reduce benefits",
        ],
        resistance_keywords=[
            "expand Medicaid", "protect coverage", "lower drug prices",
            "universal healthcare", "public option",
        ],
    ),

    LawCategory(
        slug="reproductive_rights",
        name="Reproductive Rights",
        description="Abortion, contraception, fertility, and reproductive healthcare",
        subcategories=[
            "abortion",
            "contraception",
            "fertility",
            "maternal_health",
            "family_planning",
        ],
        keywords=[
            "abortion", "reproductive", "contraception", "birth control",
            "fertility", "IVF", "maternal", "pregnancy", "Roe", "Dobbs",
            "family planning", "Planned Parenthood", "fetal",
        ],
        p2025_related=True,
        threat_keywords=[
            "ban abortion", "fetal personhood", "restrict contraception",
            "defund Planned Parenthood", "heartbeat bill", "life at conception",
        ],
        resistance_keywords=[
            "reproductive freedom", "protect abortion", "codify Roe",
            "contraception access", "reproductive healthcare",
        ],
    ),

    # === EDUCATION ===
    LawCategory(
        slug="education",
        name="Education",
        description="K-12, higher education, student loans, and education policy",
        subcategories=[
            "k12",
            "higher_education",
            "student_loans",
            "curriculum",
            "school_choice",
            "teachers",
            "special_education",
        ],
        keywords=[
            "education", "school", "student", "teacher", "curriculum",
            "college", "university", "student loan", "Pell Grant",
            "Department of Education", "charter", "voucher", "Title I",
            "special education", "IDEA",
        ],
        p2025_related=True,
        threat_keywords=[
            "eliminate Department of Education", "school voucher", "defund public",
            "ban CRT", "parental rights", "restrict curriculum",
        ],
        resistance_keywords=[
            "fund public education", "student loan forgiveness", "teacher pay",
            "protect public schools", "education funding",
        ],
    ),

    # === ENVIRONMENT & ENERGY ===
    LawCategory(
        slug="environment",
        name="Environment & Climate",
        description="Climate change, EPA, conservation, pollution, and environmental protection",
        subcategories=[
            "climate_change",
            "air_quality",
            "water",
            "conservation",
            "endangered_species",
            "pollution",
            "epa",
        ],
        keywords=[
            "environment", "climate", "EPA", "pollution", "emissions",
            "greenhouse gas", "clean air", "clean water", "conservation",
            "endangered species", "wildlife", "national park", "NEPA",
            "carbon", "renewable", "fossil fuel",
        ],
        p2025_related=True,
        threat_keywords=[
            "repeal clean air", "eliminate EPA", "rollback regulations",
            "expand drilling", "withdraw from Paris", "deregulate",
        ],
        resistance_keywords=[
            "climate action", "clean energy", "emissions reduction",
            "environmental justice", "protect EPA", "green new deal",
        ],
    ),

    LawCategory(
        slug="energy",
        name="Energy",
        description="Oil, gas, renewables, nuclear, and energy infrastructure",
        subcategories=[
            "oil_gas",
            "renewables",
            "nuclear",
            "grid",
            "efficiency",
            "pipelines",
        ],
        keywords=[
            "energy", "oil", "gas", "petroleum", "renewable", "solar",
            "wind", "nuclear", "grid", "electricity", "pipeline",
            "drilling", "fracking", "offshore", "FERC", "DOE",
        ],
        p2025_related=True,
        threat_keywords=[
            "energy dominance", "expand fossil", "repeal IRA", "end subsidies solar",
        ],
        resistance_keywords=[
            "clean energy transition", "renewable investment", "grid modernization",
        ],
    ),

    # === GOVERNMENT & DEMOCRACY ===
    LawCategory(
        slug="government",
        name="Government & Administration",
        description="Federal workforce, agency operations, and government structure",
        subcategories=[
            "federal_workforce",
            "agency_operations",
            "regulatory",
            "oversight",
            "ethics",
            "transparency",
        ],
        keywords=[
            "federal employee", "civil service", "agency", "regulation",
            "rulemaking", "oversight", "OMB", "OPM", "Schedule F",
            "executive order", "presidential authority", "bureaucracy",
        ],
        p2025_related=True,
        threat_keywords=[
            "Schedule F", "political appointees", "gut civil service",
            "unitary executive", "impound funds", "reduce workforce",
        ],
        resistance_keywords=[
            "protect civil service", "merit system", "whistleblower protection",
            "government accountability", "inspector general",
        ],
    ),

    LawCategory(
        slug="elections",
        name="Elections & Democracy",
        description="Election administration, campaign finance, and democratic processes",
        subcategories=[
            "election_admin",
            "campaign_finance",
            "redistricting",
            "electoral_college",
            "foreign_interference",
        ],
        keywords=[
            "election", "vote", "ballot", "campaign finance", "PAC",
            "redistricting", "gerrymandering", "electoral college",
            "FEC", "election security", "poll", "precinct",
        ],
        p2025_related=True,
        threat_keywords=[
            "election integrity", "voter fraud", "restrict mail voting",
            "citizen verification", "poll watchers",
        ],
        resistance_keywords=[
            "voting rights act", "automatic registration", "election protection",
            "independent redistricting", "campaign finance reform",
        ],
    ),

    # === ECONOMY & FINANCE ===
    LawCategory(
        slug="economy",
        name="Economy & Labor",
        description="Employment, wages, unions, trade, and economic policy",
        subcategories=[
            "employment",
            "wages",
            "unions",
            "trade",
            "small_business",
            "workforce_development",
        ],
        keywords=[
            "economy", "employment", "job", "wage", "minimum wage", "union",
            "labor", "trade", "tariff", "NLRB", "unemployment",
            "workforce", "small business", "SBA",
        ],
        p2025_related=True,
        threat_keywords=[
            "right to work", "weaken NLRB", "deregulate labor", "reduce minimum wage",
        ],
        resistance_keywords=[
            "raise minimum wage", "protect unions", "worker rights",
            "paid leave", "fair scheduling",
        ],
    ),

    LawCategory(
        slug="finance",
        name="Finance & Banking",
        description="Banking regulation, consumer protection, securities, and financial policy",
        subcategories=[
            "banking",
            "consumer_protection",
            "securities",
            "crypto",
            "insurance",
        ],
        keywords=[
            "bank", "financial", "SEC", "CFPB", "Wall Street", "credit",
            "loan", "mortgage", "consumer protection", "securities",
            "cryptocurrency", "bitcoin", "insurance", "Dodd-Frank",
        ],
        p2025_related=False,
        threat_keywords=[
            "eliminate CFPB", "deregulate banks", "repeal Dodd-Frank",
        ],
        resistance_keywords=[
            "consumer protection", "bank regulation", "predatory lending",
        ],
    ),

    LawCategory(
        slug="taxes",
        name="Taxes & Budget",
        description="Tax policy, federal budget, spending, and fiscal policy",
        subcategories=[
            "income_tax",
            "corporate_tax",
            "budget",
            "spending",
            "debt",
        ],
        keywords=[
            "tax", "IRS", "income tax", "corporate tax", "budget",
            "appropriations", "spending", "deficit", "debt", "fiscal",
            "revenue", "deduction", "credit",
        ],
        p2025_related=False,
        threat_keywords=[
            "flat tax", "cut IRS", "reduce corporate tax",
        ],
        resistance_keywords=[
            "tax the wealthy", "close loopholes", "fund IRS enforcement",
        ],
    ),

    # === JUSTICE & PUBLIC SAFETY ===
    LawCategory(
        slug="criminal_justice",
        name="Criminal Justice",
        description="Policing, courts, prisons, sentencing, and criminal law reform",
        subcategories=[
            "policing",
            "courts",
            "prisons",
            "sentencing",
            "death_penalty",
            "reform",
        ],
        keywords=[
            "criminal", "police", "law enforcement", "prison", "incarceration",
            "sentencing", "death penalty", "DOJ", "FBI", "prosecutor",
            "parole", "probation", "bail", "reform",
        ],
        p2025_related=True,
        threat_keywords=[
            "tough on crime", "expand death penalty", "mandatory minimum",
            "qualified immunity", "defund prosecutors",
        ],
        resistance_keywords=[
            "police reform", "end qualified immunity", "sentencing reform",
            "prison reform", "abolish death penalty", "bail reform",
        ],
    ),

    LawCategory(
        slug="guns",
        name="Guns & Firearms",
        description="Gun rights, gun control, and firearms policy",
        subcategories=[
            "gun_rights",
            "gun_control",
            "background_checks",
            "assault_weapons",
        ],
        keywords=[
            "gun", "firearm", "second amendment", "NRA", "ATF",
            "background check", "assault weapon", "magazine", "concealed carry",
            "red flag", "ghost gun",
        ],
        p2025_related=False,
        threat_keywords=[
            "expand gun rights", "constitutional carry", "repeal NFA",
        ],
        resistance_keywords=[
            "gun safety", "assault weapon ban", "universal background check",
            "red flag law", "gun violence prevention",
        ],
    ),

    # === FOREIGN POLICY & DEFENSE ===
    LawCategory(
        slug="foreign_policy",
        name="Foreign Policy",
        description="International relations, diplomacy, treaties, and foreign aid",
        subcategories=[
            "diplomacy",
            "treaties",
            "foreign_aid",
            "sanctions",
            "international_orgs",
        ],
        keywords=[
            "foreign policy", "diplomacy", "treaty", "foreign aid", "USAID",
            "State Department", "ambassador", "NATO", "UN", "sanctions",
            "international", "allies",
        ],
        p2025_related=True,
        threat_keywords=[
            "withdraw from", "America First", "reduce foreign aid", "leave NATO",
        ],
        resistance_keywords=[
            "international cooperation", "strengthen alliances", "diplomacy",
        ],
    ),

    LawCategory(
        slug="defense",
        name="Defense & Military",
        description="Military policy, veterans, defense spending, and national security",
        subcategories=[
            "military_policy",
            "veterans",
            "defense_spending",
            "nuclear",
            "cyber",
        ],
        keywords=[
            "defense", "military", "Pentagon", "DOD", "veteran", "VA",
            "nuclear", "cyber", "national security", "armed forces",
            "army", "navy", "air force", "marines",
        ],
        p2025_related=True,
        threat_keywords=[
            "politicize military", "end woke military", "remove DEI",
        ],
        resistance_keywords=[
            "veteran services", "military readiness", "civilian oversight",
        ],
    ),

    # === SOCIAL SERVICES ===
    LawCategory(
        slug="social_security",
        name="Social Security & Retirement",
        description="Social Security, pensions, and retirement policy",
        subcategories=[
            "social_security",
            "pensions",
            "retirement",
            "ssi",
        ],
        keywords=[
            "Social Security", "retirement", "pension", "SSI", "SSDI",
            "senior", "elderly", "401k", "IRA",
        ],
        p2025_related=False,
        threat_keywords=[
            "privatize Social Security", "raise retirement age", "cut benefits",
        ],
        resistance_keywords=[
            "protect Social Security", "expand benefits", "strengthen retirement",
        ],
    ),

    LawCategory(
        slug="housing",
        name="Housing",
        description="Affordable housing, homelessness, HUD, and housing policy",
        subcategories=[
            "affordable_housing",
            "homelessness",
            "hud",
            "fair_housing",
            "public_housing",
        ],
        keywords=[
            "housing", "HUD", "affordable housing", "homeless", "rent",
            "mortgage", "public housing", "Section 8", "fair housing",
            "zoning", "NIMBY",
        ],
        p2025_related=True,
        threat_keywords=[
            "privatize public housing", "reduce HUD", "eliminate fair housing",
        ],
        resistance_keywords=[
            "affordable housing", "tenant protection", "fair housing enforcement",
            "housing first", "end homelessness",
        ],
    ),

    LawCategory(
        slug="food_agriculture",
        name="Food & Agriculture",
        description="Farm policy, SNAP, food safety, and agricultural regulation",
        subcategories=[
            "farm_policy",
            "snap",
            "food_safety",
            "usda",
        ],
        keywords=[
            "agriculture", "farm", "USDA", "SNAP", "food stamp", "WIC",
            "food safety", "FDA", "crop", "subsidy", "farm bill",
        ],
        p2025_related=True,
        threat_keywords=[
            "work requirements SNAP", "cut food stamps", "reduce farm regulation",
        ],
        resistance_keywords=[
            "expand SNAP", "food security", "farm worker protection",
        ],
    ),

    # === TECHNOLOGY & COMMUNICATIONS ===
    LawCategory(
        slug="technology",
        name="Technology & Internet",
        description="Tech regulation, AI, social media, and internet policy",
        subcategories=[
            "big_tech",
            "ai",
            "social_media",
            "internet",
            "data_privacy",
        ],
        keywords=[
            "technology", "tech", "AI", "artificial intelligence", "social media",
            "internet", "data privacy", "Section 230", "algorithm",
            "platform", "antitrust", "Google", "Facebook", "Meta", "Amazon",
        ],
        p2025_related=False,
        threat_keywords=[
            "repeal Section 230", "punish big tech",
        ],
        resistance_keywords=[
            "tech regulation", "data privacy", "algorithmic accountability",
            "digital rights", "net neutrality",
        ],
    ),

    LawCategory(
        slug="communications",
        name="Communications & Media",
        description="FCC, broadcasting, telecom, and media policy",
        subcategories=[
            "fcc",
            "broadcasting",
            "telecom",
            "broadband",
        ],
        keywords=[
            "FCC", "communications", "broadcast", "telecom", "broadband",
            "spectrum", "radio", "television", "media", "net neutrality",
        ],
        p2025_related=False,
        threat_keywords=[],
        resistance_keywords=["net neutrality", "broadband access", "media diversity"],
    ),

    # === TRANSPORTATION & INFRASTRUCTURE ===
    LawCategory(
        slug="transportation",
        name="Transportation",
        description="Roads, transit, aviation, rail, and transportation policy",
        subcategories=[
            "highways",
            "transit",
            "aviation",
            "rail",
            "shipping",
        ],
        keywords=[
            "transportation", "highway", "road", "transit", "bus", "rail",
            "Amtrak", "aviation", "FAA", "DOT", "infrastructure",
            "bridge", "port", "shipping",
        ],
        p2025_related=False,
        threat_keywords=[],
        resistance_keywords=["public transit", "infrastructure investment"],
    ),

    LawCategory(
        slug="infrastructure",
        name="Infrastructure",
        description="Bridges, water systems, broadband, and public works",
        subcategories=[
            "water_infrastructure",
            "broadband",
            "bridges",
            "public_works",
        ],
        keywords=[
            "infrastructure", "bridge", "water system", "sewer", "broadband",
            "public works", "Army Corps", "construction",
        ],
        p2025_related=False,
        threat_keywords=[],
        resistance_keywords=["infrastructure investment", "clean water"],
    ),

    # === TRIBAL & TERRITORIES ===
    LawCategory(
        slug="tribal",
        name="Tribal Affairs",
        description="Native American policy, tribal sovereignty, and Indian affairs",
        subcategories=[
            "sovereignty",
            "bia",
            "tribal_lands",
            "indian_health",
        ],
        keywords=[
            "tribal", "Native American", "Indian", "BIA", "sovereignty",
            "reservation", "IHS", "Indian Health Service", "treaty",
        ],
        p2025_related=False,
        threat_keywords=[],
        resistance_keywords=["tribal sovereignty", "treaty rights"],
    ),

    LawCategory(
        slug="territories",
        name="Territories",
        description="Puerto Rico, Guam, US Virgin Islands, and territorial policy",
        subcategories=[
            "puerto_rico",
            "guam",
            "virgin_islands",
            "statehood",
        ],
        keywords=[
            "Puerto Rico", "Guam", "Virgin Islands", "American Samoa",
            "Northern Mariana", "territory", "statehood",
        ],
        p2025_related=False,
        threat_keywords=[],
        resistance_keywords=["statehood", "territorial rights"],
    ),
]


def get_category_by_slug(slug: str) -> LawCategory | None:
    """Get a category by its slug."""
    for cat in CATEGORIES:
        if cat.slug == slug:
            return cat
    return None


def get_p2025_categories() -> list[LawCategory]:
    """Get categories related to Project 2025."""
    return [cat for cat in CATEGORIES if cat.p2025_related]


def get_all_keywords() -> dict[str, list[str]]:
    """Get all keywords mapped to their categories."""
    keyword_map = {}
    for cat in CATEGORIES:
        for keyword in cat.keywords:
            if keyword.lower() not in keyword_map:
                keyword_map[keyword.lower()] = []
            keyword_map[keyword.lower()].append(cat.slug)
    return keyword_map
