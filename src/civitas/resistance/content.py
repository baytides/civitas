"""Server-side resistance content for UI rendering."""

RESISTANCE_TIERS = [
    {
        "tier": 1,
        "id": "tier_1_immediate",
        "title": "Courts & States",
        "subtitle": "Immediate Actions (Now)",
        "color": "green",
        "description": (
            "Challenge unconstitutional actions through litigation and strengthen "
            "state-level protections. These are the most effective immediate tools available."
        ),
        "general_actions": [
            {
                "title": "Support Constitutional Litigation",
                "description": (
                    "Donate to and spread awareness about lawsuits challenging executive overreach"
                ),
                "urgency": "critical",
                "resources": ["ACLU", "Brennan Center", "Democracy Forward"],
            },
            {
                "title": "Contact State Legislators",
                "description": "Push for state laws that protect rights and resist federal overreach",
                "urgency": "high",
                "resources": ["Find your state rep", "Model legislation"],
            },
            {
                "title": "Support State Attorney Generals",
                "description": "State AGs are filing suits against unconstitutional federal actions",
                "urgency": "high",
                "resources": ["State lawsuits tracker"],
            },
        ],
    },
    {
        "tier": 2,
        "id": "tier_2_congressional",
        "title": "Congress 2026",
        "subtitle": "Midterm Strategy",
        "color": "yellow",
        "description": (
            "Work toward flipping Congress in the 2026 midterm elections to provide "
            "legislative checks on executive power."
        ),
        "general_actions": [
            {
                "title": "Register New Voters",
                "description": "Every new registered voter increases our chances in 2026",
                "urgency": "high",
                "resources": ["Vote.org", "Rock the Vote"],
            },
            {
                "title": "Support Candidates",
                "description": "Identify and support candidates committed to democratic values",
                "urgency": "medium",
                "resources": ["ActBlue", "Run for Something"],
            },
        ],
    },
    {
        "tier": 3,
        "id": "tier_3_presidential",
        "title": "Presidency 2028",
        "subtitle": "Long-term Vision",
        "color": "blue",
        "description": (
            "Build toward restoring democratic leadership in the executive branch in 2028, "
            "while preparing institutional reforms."
        ),
        "general_actions": [
            {
                "title": "Develop New Leaders",
                "description": "Support programs that train the next generation of democratic leaders",
                "urgency": "medium",
                "resources": ["Arena", "New Politics"],
            },
            {
                "title": "Reform Advocacy",
                "description": "Push for systemic reforms to prevent future democratic backsliding",
                "urgency": "low",
                "resources": ["Democracy reform organizations"],
            },
        ],
    },
]

RESISTANCE_ORG_SECTIONS = [
    {
        "title": "Legal Defense",
        "items": [
            {"name": "ACLU", "url": "https://www.aclu.org"},
            {"name": "Brennan Center for Justice", "url": "https://www.brennancenter.org"},
            {"name": "Democracy Forward", "url": "https://democracyforward.org"},
            {"name": "NAACP Legal Defense Fund", "url": "https://www.naacpldf.org"},
        ],
    },
    {
        "title": "Voter Engagement",
        "items": [
            {"name": "Vote.org", "url": "https://www.vote.org"},
            {"name": "Rock the Vote", "url": "https://www.rockthevote.org"},
            {"name": "League of Women Voters", "url": "https://www.lwv.org"},
            {"name": "When We All Vote", "url": "https://whenweallvote.org"},
        ],
    },
    {
        "title": "Organizing",
        "items": [
            {"name": "Indivisible", "url": "https://indivisible.org"},
            {"name": "Swing Left", "url": "https://swingleft.org"},
            {"name": "Run for Something", "url": "https://runforsomething.net"},
            {"name": "Sister District", "url": "https://sisterdistrict.com"},
        ],
    },
]
