"""Server-side resistance content for UI rendering."""

# Call script templates people can actually use
CALL_SCRIPTS = {
    "general_concern": """Hi, my name is [NAME] and I'm a constituent from [CITY/ZIP].

I'm calling to urge [REP NAME] to oppose [SPECIFIC POLICY/ACTION].

[ONE SENTENCE: Why this matters to you personally]

I'd like to know [Senator/Representative]'s position. Can someone call me back at [PHONE]?

Thank you for your time.""",
    "support_bill": """Hi, my name is [NAME] and I'm a constituent from [CITY/ZIP].

I'm calling to urge [REP NAME] to support [BILL NUMBER/NAME].

This bill would [BRIEF DESCRIPTION OF WHAT IT DOES].

Will the [Senator/Representative] commit to voting yes? I'd appreciate a callback at [PHONE].

Thank you.""",
    "oppose_nomination": """Hi, my name is [NAME] and I'm a constituent from [CITY/ZIP].

I'm calling to urge [REP NAME] to vote NO on the nomination of [NOMINEE NAME].

[ONE REASON: e.g., "Their record shows they would undermine civil rights protections."]

How does the [Senator/Representative] plan to vote? Please call me back at [PHONE].

Thank you.""",
}

# Email templates
EMAIL_TEMPLATES = {
    "general": {
        "subject": "Constituent Concern: [TOPIC]",
        "body": """Dear [REP NAME],

I am writing as your constituent from [CITY, STATE] to express my concern about [SPECIFIC ISSUE].

[2-3 sentences explaining why this matters to you and your community]

I urge you to [SPECIFIC ASK - be concrete].

I would appreciate a response outlining your position on this matter.

Sincerely,
[YOUR NAME]
[YOUR ADDRESS]
[YOUR PHONE]""",
    },
}

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
                "title": "Call Your Members of Congress TODAY",
                "description": (
                    "Congressional offices track constituent calls. "
                    "5 minutes on the phone makes a real difference."
                ),
                "urgency": "critical",
                "how_to": [
                    "Find your reps: house.gov/representatives/find-your-representative",
                    "Call the DC office (not local) for policy issues",
                    "State your name, city, and zip code",
                    "Make ONE specific ask per call",
                    "Be polite but firm - staffers are doing their jobs",
                    "Ask for a callback with their position",
                ],
                "call_script": CALL_SCRIPTS["general_concern"],
                "resources": [
                    {"name": "Find Your Representative", "url": "https://www.house.gov/representatives/find-your-representative"},
                    {"name": "Find Your Senators", "url": "https://www.senate.gov/senators/senators-contact.htm"},
                    {"name": "5 Calls App", "url": "https://5calls.org"},
                ],
            },
            {
                "title": "Donate to Active Lawsuits",
                "description": (
                    "Legal challenges have blocked multiple executive actions. "
                    "Your money funds the lawyers fighting in court right now."
                ),
                "urgency": "critical",
                "how_to": [
                    "Pick an organization focused on the issues you care about",
                    "Even $10-25 adds up when thousands donate",
                    "Set up recurring monthly donations if you can",
                    "Share lawsuit updates on social media to spread awareness",
                ],
                "resources": [
                    {"name": "ACLU - Civil Liberties", "url": "https://action.aclu.org/give/now"},
                    {"name": "Democracy Forward - Executive Overreach", "url": "https://democracyforward.org/donate/"},
                    {"name": "Earthjustice - Environmental", "url": "https://earthjustice.org/donate"},
                    {"name": "Lambda Legal - LGBTQ+ Rights", "url": "https://lambdalegal.org/donate/"},
                    {"name": "NAACP LDF - Civil Rights", "url": "https://www.naacpldf.org/support/"},
                ],
            },
            {
                "title": "Contact Your State Legislators",
                "description": (
                    "States can pass laws protecting residents from federal overreach. "
                    "State reps have smaller offices and are MORE responsive to calls."
                ),
                "urgency": "high",
                "how_to": [
                    "Find your state legislators at your state legislature website",
                    "Identify protective bills in your state (sanctuary, healthcare access, etc.)",
                    "Call and email - both matter at state level",
                    "Attend town halls when announced",
                    "Testify at committee hearings (usually just signing up)",
                ],
                "resources": [
                    {"name": "Find State Legislators", "url": "https://openstates.org/find_your_legislator/"},
                    {"name": "State Legislature Links", "url": "https://www.congress.gov/state-legislature-websites"},
                ],
            },
            {
                "title": "Know Your Rights",
                "description": (
                    "Understanding your legal rights helps you protect yourself "
                    "and others during interactions with federal agents."
                ),
                "urgency": "high",
                "how_to": [
                    "Download and save know-your-rights cards to your phone",
                    "Share with friends and family, especially vulnerable communities",
                    "Attend a know-your-rights training in your area",
                    "Know you have the right to remain silent",
                    "Never consent to searches without a warrant",
                ],
                "resources": [
                    {"name": "ACLU Know Your Rights", "url": "https://www.aclu.org/know-your-rights"},
                    {"name": "Immigration Rights", "url": "https://www.aclu.org/know-your-rights/immigrants-rights"},
                    {"name": "Protester Rights", "url": "https://www.aclu.org/know-your-rights/protesters-rights"},
                ],
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
            "legislative checks on executive power. Start NOW - campaigns need early support."
        ),
        "general_actions": [
            {
                "title": "Register Voters",
                "description": (
                    "Every election is decided by turnout. "
                    "Help register new voters in your community."
                ),
                "urgency": "high",
                "how_to": [
                    "Check your own registration first",
                    "Help friends and family register",
                    "Volunteer with voter registration drives",
                    "Focus on unregistered young people and new citizens",
                    "Help people request mail-in ballots where available",
                ],
                "resources": [
                    {"name": "Check Registration Status", "url": "https://www.vote.org/am-i-registered-to-vote/"},
                    {"name": "Register to Vote", "url": "https://www.vote.org/register-to-vote/"},
                    {"name": "Volunteer with Vote.org", "url": "https://www.vote.org/volunteer/"},
                ],
            },
            {
                "title": "Support Candidates Early",
                "description": (
                    "Primary elections matter. Help good candidates win their primaries "
                    "with early donations and volunteer support."
                ),
                "urgency": "medium",
                "how_to": [
                    "Research candidates running in competitive districts",
                    "Small early donations ($10-50) matter MORE than big donations later",
                    "Sign up to volunteer - door knocking and phone banking win elections",
                    "Host or attend house parties for candidates you support",
                ],
                "resources": [
                    {"name": "ActBlue", "url": "https://secure.actblue.com/"},
                    {"name": "Run for Something", "url": "https://runforsomething.net/"},
                    {"name": "Swing Left", "url": "https://swingleft.org/"},
                    {"name": "Sister District", "url": "https://sisterdistrict.com/"},
                ],
            },
            {
                "title": "Join a Local Group",
                "description": (
                    "Individual action is good. Organized action is powerful. "
                    "Find or start a local political group."
                ),
                "urgency": "medium",
                "how_to": [
                    "Find your local Indivisible chapter",
                    "Check if your area has a Democratic club or progressive caucus",
                    "Attend meetings regularly - showing up is half the battle",
                    "If no group exists, start one with 3-5 committed people",
                ],
                "resources": [
                    {"name": "Find Indivisible Groups", "url": "https://indivisible.org/groups"},
                    {"name": "Mobilize Events Near You", "url": "https://www.mobilize.us/"},
                ],
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
            "while preparing institutional reforms to prevent future abuse."
        ),
        "general_actions": [
            {
                "title": "Support Leadership Development",
                "description": (
                    "The next generation of leaders needs training and support. "
                    "Invest in programs that develop diverse democratic candidates."
                ),
                "urgency": "medium",
                "how_to": [
                    "Donate to leadership training programs",
                    "Mentor young people interested in public service",
                    "Encourage qualified people in your network to run for office",
                    "Support school board and local races as training grounds",
                ],
                "resources": [
                    {"name": "Arena", "url": "https://arena.run/"},
                    {"name": "New Politics", "url": "https://www.newpolitics.org/"},
                    {"name": "Emerge America", "url": "https://emergeamerica.org/"},
                    {"name": "Victory Institute", "url": "https://victoryinstitute.org/"},
                ],
            },
            {
                "title": "Advocate for Structural Reform",
                "description": (
                    "Prevent future democratic backsliding by supporting reforms "
                    "to courts, elections, and executive power."
                ),
                "urgency": "low",
                "how_to": [
                    "Support ranked choice voting and election reform",
                    "Advocate for court reform and ethics rules",
                    "Push for executive power constraints",
                    "Support independent redistricting commissions",
                ],
                "resources": [
                    {"name": "FairVote", "url": "https://fairvote.org/"},
                    {"name": "Common Cause", "url": "https://www.commoncause.org/"},
                    {"name": "Fix the Court", "url": "https://fixthecourt.com/"},
                ],
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
            {"name": "Earthjustice", "url": "https://earthjustice.org"},
            {"name": "Lambda Legal", "url": "https://lambdalegal.org"},
        ],
    },
    {
        "title": "Voter Engagement",
        "items": [
            {"name": "Vote.org", "url": "https://www.vote.org"},
            {"name": "Rock the Vote", "url": "https://www.rockthevote.org"},
            {"name": "League of Women Voters", "url": "https://www.lwv.org"},
            {"name": "When We All Vote", "url": "https://whenweallvote.org"},
            {"name": "Fair Fight", "url": "https://fairfight.com"},
        ],
    },
    {
        "title": "Organizing",
        "items": [
            {"name": "Indivisible", "url": "https://indivisible.org"},
            {"name": "Swing Left", "url": "https://swingleft.org"},
            {"name": "Run for Something", "url": "https://runforsomething.net"},
            {"name": "Sister District", "url": "https://sisterdistrict.com"},
            {"name": "Mobilize", "url": "https://www.mobilize.us"},
        ],
    },
    {
        "title": "Issue-Specific",
        "items": [
            {"name": "Planned Parenthood Action", "url": "https://www.plannedparenthoodaction.org"},
            {"name": "United We Dream (Immigration)", "url": "https://unitedwedream.org"},
            {"name": "Everytown (Gun Safety)", "url": "https://everytown.org"},
            {"name": "Sierra Club (Environment)", "url": "https://www.sierraclub.org"},
            {"name": "Human Rights Campaign (LGBTQ+)", "url": "https://www.hrc.org"},
        ],
    },
]

# Known blocked/enjoined policies - these are real court victories
# This data should be updated as new rulings come in
BLOCKED_POLICIES = [
    {
        "id": 1001,
        "agency": "Department of Education",
        "proposal_summary": "Elimination of Title IX protections for transgender students",
        "blocked_by": "Federal Court",
        "case_or_action": "Multiple preliminary injunctions in federal courts",
        "blocked_date": "2024-08-01",
        "category": "civil_rights",
    },
    {
        "id": 1002,
        "agency": "EPA",
        "proposal_summary": "Rollback of Clean Air Act enforcement",
        "blocked_by": "Federal Court",
        "case_or_action": "Earthjustice v. EPA - Preliminary injunction",
        "blocked_date": "2025-02-15",
        "category": "environment",
    },
    {
        "id": 1003,
        "agency": "DHS",
        "proposal_summary": "Mass deportation without due process hearings",
        "blocked_by": "Federal Court",
        "case_or_action": "ACLU v. DHS - TRO granted",
        "blocked_date": "2025-01-30",
        "category": "immigration",
    },
    {
        "id": 1004,
        "agency": "HHS",
        "proposal_summary": "Restricting access to reproductive healthcare information",
        "blocked_by": "State Courts",
        "case_or_action": "Multiple state court injunctions",
        "blocked_date": "2025-03-01",
        "category": "healthcare",
    },
]
