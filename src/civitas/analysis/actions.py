"""Specific resistance actions for each category and issue type.

Instead of generic "contact your senator" actions, this provides contextual,
specific actions that users can take based on the category, jurisdiction,
and nature of the legislation.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ActionType(Enum):
    """Types of actions users can take."""
    CONTACT = "contact"  # Contact officials
    ORGANIZE = "organize"  # Community organizing
    LEGAL = "legal"  # Legal/rights-based
    FINANCIAL = "financial"  # Financial actions
    PARTICIPATE = "participate"  # Public participation
    INFORM = "inform"  # Information sharing
    SUPPORT = "support"  # Support organizations


class ActionUrgency(Enum):
    """Urgency level for actions."""
    IMMEDIATE = "immediate"  # Act now (vote coming, deadline)
    SOON = "soon"  # Act within days/weeks
    ONGOING = "ongoing"  # Continuous engagement


@dataclass
class ResistanceAction:
    """A specific action a user can take."""

    action_type: ActionType
    title: str
    description: str
    how_to: str  # Step-by-step instructions
    urgency: ActionUrgency = ActionUrgency.ONGOING
    resources: list[str] = field(default_factory=list)  # URLs or resource names
    effective_for: list[str] = field(default_factory=list)  # Jurisdictions/contexts
    impact_level: str = "medium"  # low, medium, high


# Actions organized by category slug
CATEGORY_ACTIONS: dict[str, list[ResistanceAction]] = {

    # === CIVIL RIGHTS ===
    "civil_rights": [
        ResistanceAction(
            action_type=ActionType.LEGAL,
            title="Know Your Rights",
            description="Understand your constitutional protections before engaging with authorities.",
            how_to="1. Download ACLU Know Your Rights guides\n2. Save emergency legal contact numbers\n3. Document any rights violations with photos/video\n4. Contact civil rights attorneys if rights are violated",
            resources=[
                "https://www.aclu.org/know-your-rights",
                "https://www.naacpldf.org/",
                "https://civilrights.org/",
            ],
        ),
        ResistanceAction(
            action_type=ActionType.ORGANIZE,
            title="Join Local Civil Rights Coalition",
            description="Connect with organizations fighting for civil rights in your community.",
            how_to="1. Search for local NAACP, ACLU, or civil rights chapters\n2. Attend a meeting or event\n3. Sign up for action alerts\n4. Volunteer for campaigns",
            resources=[
                "https://naacp.org/find-local-unit",
                "https://www.aclu.org/affiliates",
            ],
        ),
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Attend Public Comment Periods",
            description="Speak at government hearings on civil rights policies.",
            how_to="1. Monitor state/local government calendars for hearings\n2. Register to speak (often 48hrs ahead)\n3. Prepare 2-3 minute testimony\n4. Bring supporters to fill the room",
            urgency=ActionUrgency.IMMEDIATE,
        ),
        ResistanceAction(
            action_type=ActionType.CONTACT,
            title="Contact Your State Civil Rights Office",
            description="File complaints or get information from your state's civil rights enforcement agency.",
            how_to="1. Find your state's civil rights commission/office\n2. Document the violation with dates, witnesses\n3. File a formal complaint\n4. Follow up in writing",
            resources=["https://www.findlaw.com/civilrights/civil-rights-overview/state-civil-rights-offices.html"],
        ),
    ],

    # === IMMIGRATION ===
    "immigration": [
        ResistanceAction(
            action_type=ActionType.LEGAL,
            title="Know Your Rights If Approached by ICE",
            description="Understand what to do if immigration enforcement contacts you.",
            how_to="1. You have the right to remain silent\n2. Ask if you are free to leave\n3. Don't sign anything without an attorney\n4. Memorize an emergency legal contact number\n5. Don't open your door without a judicial warrant",
            urgency=ActionUrgency.IMMEDIATE,
            resources=[
                "https://www.ilrc.org/red-cards",
                "https://www.immigrantdefenseproject.org/",
            ],
        ),
        ResistanceAction(
            action_type=ActionType.SUPPORT,
            title="Support Immigrant Defense Funds",
            description="Help fund legal representation for immigrants facing deportation.",
            how_to="1. Find local immigrant legal defense funds\n2. Make a one-time or recurring donation\n3. Organize workplace/community fundraising",
            resources=[
                "https://www.immigrantdefenseproject.org/",
                "https://www.vera.org/initiatives/safe-initiative",
            ],
        ),
        ResistanceAction(
            action_type=ActionType.ORGANIZE,
            title="Join Rapid Response Network",
            description="Be alerted when ICE is active in your community and help document.",
            how_to="1. Find your local rapid response network\n2. Sign up for alerts\n3. Attend know-your-rights training\n4. Learn safe documentation practices",
            resources=["https://www.unitedwedream.org/"],
        ),
        ResistanceAction(
            action_type=ActionType.CONTACT,
            title="Contact Elected Officials About Immigration Policy",
            description="Urge your representatives to protect immigrant communities.",
            how_to="1. Find your state legislators at openstates.org\n2. Call during business hours\n3. Be specific: mention bill numbers\n4. Share personal stories if comfortable\n5. Follow up with email",
            effective_for=["state", "federal"],
        ),
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Attend Sanctuary City Hearings",
            description="Support sanctuary policies at city council meetings.",
            how_to="1. Monitor your city council agenda\n2. Sign up to speak during public comment\n3. Bring community members to show support\n4. Wear supportive colors/signs",
            effective_for=["local"],
        ),
    ],

    # === HEALTHCARE ===
    "healthcare": [
        ResistanceAction(
            action_type=ActionType.LEGAL,
            title="Understand Your Healthcare Rights",
            description="Know your rights under ACA, Medicaid, and emergency care laws.",
            how_to="1. Review your state's Medicaid eligibility\n2. Understand EMTALA emergency care rights\n3. Know your appeals process for denied claims\n4. Keep copies of all medical bills and correspondence",
            resources=[
                "https://www.healthcare.gov/",
                "https://www.medicaid.gov/",
            ],
        ),
        ResistanceAction(
            action_type=ActionType.CONTACT,
            title="Contact Your State Insurance Commissioner",
            description="Report insurance violations or unfair denials.",
            how_to="1. Document denied claims with dates and reasons\n2. Find your state insurance commissioner\n3. File a formal complaint\n4. Request an external review if available",
            effective_for=["state"],
        ),
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Attend Medicaid Public Comment Sessions",
            description="Speak at hearings when states propose Medicaid changes.",
            how_to="1. Monitor your state Medicaid agency for proposed rules\n2. Submit written comments before deadline\n3. Attend in-person hearings if held\n4. Coordinate with healthcare advocacy groups",
            urgency=ActionUrgency.IMMEDIATE,
        ),
        ResistanceAction(
            action_type=ActionType.SUPPORT,
            title="Support Community Health Centers",
            description="Help fund safety-net healthcare providers.",
            how_to="1. Find federally qualified health centers in your area\n2. Donate or volunteer\n3. Spread awareness about free/low-cost services\n4. Advocate for increased funding",
            resources=["https://findahealthcenter.hrsa.gov/"],
        ),
        ResistanceAction(
            action_type=ActionType.ORGANIZE,
            title="Join Healthcare Advocacy Group",
            description="Connect with organizations fighting for healthcare access.",
            how_to="1. Find local healthcare advocacy chapters\n2. Attend meetings and training\n3. Participate in lobby days\n4. Share your healthcare story if comfortable",
            resources=[
                "https://familiesusa.org/",
                "https://www.communitycatalyst.org/",
            ],
        ),
    ],

    # === REPRODUCTIVE RIGHTS ===
    "reproductive_rights": [
        ResistanceAction(
            action_type=ActionType.LEGAL,
            title="Know Your Reproductive Healthcare Rights",
            description="Understand what's legal in your state and how to access care.",
            how_to="1. Check your state's current abortion laws\n2. Know about telemedicine options\n3. Understand privacy protections\n4. Save abortion fund contact information",
            resources=[
                "https://www.abortionfinder.org/",
                "https://www.plannedparenthood.org/",
                "https://www.ineedana.com/",
            ],
        ),
        ResistanceAction(
            action_type=ActionType.SUPPORT,
            title="Support Abortion Funds",
            description="Help fund abortion access for those who can't afford it.",
            how_to="1. Find your local abortion fund\n2. Make a donation\n3. Volunteer as a practical support person\n4. Help with transportation, lodging, childcare",
            resources=[
                "https://abortionfunds.org/",
                "https://www.prochoice.org/",
            ],
        ),
        ResistanceAction(
            action_type=ActionType.ORGANIZE,
            title="Join Clinic Defense/Escort",
            description="Help patients safely access reproductive healthcare clinics.",
            how_to="1. Contact local clinics about volunteer escort programs\n2. Complete training on de-escalation\n3. Commit to regular volunteer shifts\n4. Follow clinic safety protocols",
        ),
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Testify at State Legislature Hearings",
            description="Share your story at hearings on reproductive rights bills.",
            how_to="1. Monitor your state legislature for relevant bills\n2. Sign up to testify (often requires advance registration)\n3. Prepare 2-3 minute testimony\n4. Share personal story if comfortable, or speak to policy impacts",
            urgency=ActionUrgency.IMMEDIATE,
        ),
        ResistanceAction(
            action_type=ActionType.INFORM,
            title="Share Accurate Information",
            description="Combat misinformation about reproductive healthcare.",
            how_to="1. Follow reputable medical sources\n2. Share factual information on social media\n3. Correct misinformation when you see it\n4. Direct people to verified resources",
        ),
    ],

    # === EDUCATION ===
    "education": [
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Attend School Board Meetings",
            description="Participate in local education decisions.",
            how_to="1. Find your school board meeting schedule\n2. Review the agenda before attending\n3. Sign up for public comment\n4. Speak to specific agenda items\n5. Bring supportive community members",
            effective_for=["local"],
        ),
        ResistanceAction(
            action_type=ActionType.ORGANIZE,
            title="Join Parent-Teacher Organizations",
            description="Get involved in your school community.",
            how_to="1. Contact your local school's PTA/PTO\n2. Attend meetings regularly\n3. Volunteer for committees\n4. Help organize around education issues",
        ),
        ResistanceAction(
            action_type=ActionType.CONTACT,
            title="Contact Your State Education Board",
            description="Influence state curriculum and policy decisions.",
            how_to="1. Find your state Board of Education\n2. Submit written comments on proposed rules\n3. Attend public hearings\n4. Contact your district's representative",
            effective_for=["state"],
        ),
        ResistanceAction(
            action_type=ActionType.SUPPORT,
            title="Support Public School Funding Campaigns",
            description="Advocate for adequate public education funding.",
            how_to="1. Find education funding advocacy groups in your state\n2. Support local school funding ballot measures\n3. Contact legislators about education budgets\n4. Attend budget hearings",
            resources=["https://edlawcenter.org/"],
        ),
        ResistanceAction(
            action_type=ActionType.LEGAL,
            title="Understand Student Rights",
            description="Know students' constitutional rights in schools.",
            how_to="1. Review First Amendment rights in schools\n2. Understand due process for discipline\n3. Know special education rights (IDEA)\n4. Contact ACLU for student rights violations",
            resources=["https://www.aclu.org/issues/free-speech/student-speech-and-privacy"],
        ),
    ],

    # === ENVIRONMENT ===
    "environment": [
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Submit Comments on Environmental Rules",
            description="Participate in EPA and state environmental rulemaking.",
            how_to="1. Monitor regulations.gov for proposed rules\n2. Review the proposed rule and supporting documents\n3. Submit substantive comments before deadline\n4. Cite scientific evidence and personal impacts",
            urgency=ActionUrgency.IMMEDIATE,
            resources=["https://www.regulations.gov/"],
        ),
        ResistanceAction(
            action_type=ActionType.LEGAL,
            title="Report Environmental Violations",
            description="Report pollution and environmental law violations.",
            how_to="1. Document the violation with photos/video\n2. Note date, time, location, and conditions\n3. Report to EPA or state environmental agency\n4. Contact local environmental groups",
            resources=["https://www.epa.gov/enforcement/report-environmental-violations"],
        ),
        ResistanceAction(
            action_type=ActionType.ORGANIZE,
            title="Join Local Environmental Groups",
            description="Connect with organizations fighting for environmental protection.",
            how_to="1. Find Sierra Club, 350.org, or local chapters\n2. Attend meetings and events\n3. Participate in campaigns and actions\n4. Help with community organizing",
            resources=[
                "https://www.sierraclub.org/",
                "https://350.org/",
            ],
        ),
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Attend Permit Hearings",
            description="Oppose permits for polluting facilities in your community.",
            how_to="1. Monitor your state environmental agency for permit notices\n2. Request public hearing if not scheduled\n3. Prepare testimony on health and environmental impacts\n4. Organize community members to attend",
            effective_for=["state", "local"],
        ),
        ResistanceAction(
            action_type=ActionType.SUPPORT,
            title="Support Environmental Justice Organizations",
            description="Help communities on the frontlines of pollution.",
            how_to="1. Find environmental justice organizations in your area\n2. Donate or volunteer\n3. Amplify their campaigns\n4. Show up for their actions",
            resources=["https://www.ejnet.org/ej/"],
        ),
    ],

    # === ELECTIONS ===
    "elections": [
        ResistanceAction(
            action_type=ActionType.ORGANIZE,
            title="Become a Poll Worker",
            description="Help ensure fair elections by working at polls.",
            how_to="1. Contact your county election office\n2. Apply to be a poll worker\n3. Complete required training\n4. Commit to working on election day(s)",
            urgency=ActionUrgency.SOON,
        ),
        ResistanceAction(
            action_type=ActionType.ORGANIZE,
            title="Join Election Protection Efforts",
            description="Help voters exercise their rights on election day.",
            how_to="1. Sign up with Election Protection (866-OUR-VOTE)\n2. Complete training\n3. Staff hotlines or observe polls\n4. Report irregularities",
            urgency=ActionUrgency.IMMEDIATE,
            resources=["https://866ourvote.org/"],
        ),
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Attend Redistricting Hearings",
            description="Fight gerrymandering by participating in redistricting.",
            how_to="1. Monitor your state's redistricting commission/legislature\n2. Attend public hearings\n3. Submit proposed maps or comments\n4. Organize community testimony",
            effective_for=["state"],
        ),
        ResistanceAction(
            action_type=ActionType.ORGANIZE,
            title="Register Voters",
            description="Help eligible citizens register to vote.",
            how_to="1. Get trained as a voter registrar (rules vary by state)\n2. Set up registration drives at community events\n3. Help people check their registration status\n4. Provide information about voting deadlines",
            resources=["https://www.vote.org/"],
        ),
        ResistanceAction(
            action_type=ActionType.CONTACT,
            title="Contact Secretary of State",
            description="Advocate for election security and access.",
            how_to="1. Find your Secretary of State's contact information\n2. Call or write about specific election policies\n3. Attend public meetings\n4. Request information about election procedures",
            effective_for=["state"],
        ),
    ],

    # === CRIMINAL JUSTICE ===
    "criminal_justice": [
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Attend Police Oversight Meetings",
            description="Participate in civilian oversight of law enforcement.",
            how_to="1. Find your city's police commission/oversight board\n2. Attend public meetings\n3. Speak during public comment\n4. Request data on police conduct",
            effective_for=["local"],
        ),
        ResistanceAction(
            action_type=ActionType.LEGAL,
            title="Know Your Rights with Police",
            description="Understand your rights during police encounters.",
            how_to="1. You have the right to remain silent\n2. You can refuse consent to searches\n3. You can film police in public\n4. Get badge numbers and document interactions\n5. File complaints for misconduct",
            resources=["https://www.aclu.org/know-your-rights/stopped-by-police/"],
        ),
        ResistanceAction(
            action_type=ActionType.SUPPORT,
            title="Support Bail Funds",
            description="Help people who can't afford bail get released.",
            how_to="1. Find local community bail funds\n2. Make a donation\n3. Volunteer for court watching\n4. Advocate for bail reform",
            resources=["https://www.communityjusticeexchange.org/nbfn-directory"],
        ),
        ResistanceAction(
            action_type=ActionType.ORGANIZE,
            title="Join Court Watching Programs",
            description="Monitor court proceedings for fairness.",
            how_to="1. Find local court watching organizations\n2. Complete training\n3. Attend arraignments and hearings\n4. Document and report findings",
        ),
        ResistanceAction(
            action_type=ActionType.CONTACT,
            title="Contact Your District Attorney",
            description="Advocate for prosecutorial reform.",
            how_to="1. Find your local DA's office\n2. Attend community meetings they hold\n3. Write or call about specific policies\n4. Support reform DA candidates",
            effective_for=["local", "state"],
        ),
    ],

    # === GOVERNMENT ===
    "government": [
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Submit FOIA Requests",
            description="Use public records laws to access government information.",
            how_to="1. Identify the agency with the records you need\n2. Write a specific FOIA/public records request\n3. Submit via the agency's FOIA portal or email\n4. Appeal if improperly denied",
            resources=[
                "https://www.foia.gov/",
                "https://www.muckrock.com/",
            ],
        ),
        ResistanceAction(
            action_type=ActionType.SUPPORT,
            title="Support Government Accountability Groups",
            description="Back organizations that monitor government actions.",
            how_to="1. Follow watchdog organizations\n2. Donate to investigative journalism\n3. Share their findings\n4. Report tips about government misconduct",
            resources=[
                "https://www.pogo.org/",
                "https://www.citizen.org/",
            ],
        ),
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Comment on Proposed Regulations",
            description="Participate in the federal rulemaking process.",
            how_to="1. Monitor regulations.gov for proposed rules\n2. Read the proposed rule carefully\n3. Submit substantive comments with evidence\n4. Respond to specific questions asked",
            resources=["https://www.regulations.gov/"],
        ),
        ResistanceAction(
            action_type=ActionType.CONTACT,
            title="Contact Inspector General Offices",
            description="Report waste, fraud, and abuse in government agencies.",
            how_to="1. Find the relevant agency's Inspector General\n2. Submit a complaint via their hotline or website\n3. Provide specific details and evidence\n4. Request to be informed of outcome",
            resources=["https://www.ignet.gov/"],
        ),
    ],

    # === ECONOMY & LABOR ===
    "economy": [
        ResistanceAction(
            action_type=ActionType.ORGANIZE,
            title="Support Union Organizing",
            description="Help workers organize for better conditions.",
            how_to="1. Learn about your workplace rights under NLRA\n2. Connect with union organizers if interested\n3. Support union campaigns in your community\n4. Shop union and support union labor",
            resources=[
                "https://www.nlrb.gov/about-nlrb/rights-we-protect",
                "https://www.aflcio.org/",
            ],
        ),
        ResistanceAction(
            action_type=ActionType.LEGAL,
            title="Know Your Workplace Rights",
            description="Understand wage, hour, and safety protections.",
            how_to="1. Review FLSA wage and hour requirements\n2. Know OSHA safety protections\n3. Document violations with dates and witnesses\n4. File complaints with DOL or OSHA",
            resources=[
                "https://www.dol.gov/agencies/whd",
                "https://www.osha.gov/workers",
            ],
        ),
        ResistanceAction(
            action_type=ActionType.CONTACT,
            title="Support Living Wage Campaigns",
            description="Advocate for higher minimum wages.",
            how_to="1. Find local Fight for $15 or living wage campaigns\n2. Contact city council about local minimum wage\n3. Testify at public hearings\n4. Support ballot initiatives",
            effective_for=["local", "state"],
        ),
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Attend NLRB Hearings",
            description="Support workers in union organizing proceedings.",
            how_to="1. Monitor NLRB case filings\n2. Attend public hearings\n3. Show solidarity with organizing workers\n4. Report unfair labor practices you witness",
        ),
    ],

    # === HOUSING ===
    "housing": [
        ResistanceAction(
            action_type=ActionType.LEGAL,
            title="Know Your Tenant Rights",
            description="Understand your rights as a renter.",
            how_to="1. Review your state's tenant rights laws\n2. Know your lease terms\n3. Document all communications with landlord\n4. Know eviction procedures and timelines\n5. Contact tenant rights organizations if needed",
            resources=["https://www.hud.gov/topics/rental_assistance/tenantrights"],
        ),
        ResistanceAction(
            action_type=ActionType.ORGANIZE,
            title="Join Tenant Organizing",
            description="Work with neighbors to improve housing conditions.",
            how_to="1. Talk to neighbors about shared concerns\n2. Form a tenant association\n3. Connect with local tenant rights groups\n4. Collectively address issues with landlord\n5. Know your right to organize",
        ),
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Attend Zoning and Planning Meetings",
            description="Advocate for affordable housing in your community.",
            how_to="1. Monitor city planning commission agendas\n2. Attend hearings on housing developments\n3. Speak in favor of affordable housing\n4. Oppose exclusionary zoning",
            effective_for=["local"],
        ),
        ResistanceAction(
            action_type=ActionType.CONTACT,
            title="File Fair Housing Complaints",
            description="Report housing discrimination.",
            how_to="1. Document discriminatory behavior\n2. File with HUD or your state fair housing agency\n3. File within one year of incident\n4. Contact fair housing organizations for help",
            resources=["https://www.hud.gov/program_offices/fair_housing_equal_opp/online-complaint"],
        ),
        ResistanceAction(
            action_type=ActionType.SUPPORT,
            title="Support Housing Justice Organizations",
            description="Help organizations fighting for housing rights.",
            how_to="1. Find local housing advocacy groups\n2. Donate or volunteer\n3. Participate in campaigns\n4. Support homeless services",
            resources=["https://nlihc.org/"],
        ),
    ],

    # === GUNS ===
    "guns": [
        ResistanceAction(
            action_type=ActionType.ORGANIZE,
            title="Join Gun Safety Organizations",
            description="Connect with groups working on gun violence prevention.",
            how_to="1. Find local Moms Demand Action or similar chapters\n2. Attend meetings and training\n3. Participate in advocacy days\n4. Support candidates who back gun safety",
            resources=[
                "https://momsdemandaction.org/",
                "https://giffords.org/",
                "https://everytownresearch.org/",
            ],
        ),
        ResistanceAction(
            action_type=ActionType.CONTACT,
            title="Contact State Legislators on Gun Bills",
            description="Advocate for gun safety legislation.",
            how_to="1. Find your state legislators at openstates.org\n2. Call during business hours\n3. Reference specific bill numbers\n4. Share personal connection to issue",
            effective_for=["state"],
        ),
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Testify at State Gun Bill Hearings",
            description="Share your voice at legislative hearings.",
            how_to="1. Monitor your state legislature for gun bills\n2. Sign up to testify\n3. Prepare brief, personal testimony\n4. Coordinate with advocacy groups",
            urgency=ActionUrgency.IMMEDIATE,
            effective_for=["state"],
        ),
        ResistanceAction(
            action_type=ActionType.SUPPORT,
            title="Support Gun Violence Intervention Programs",
            description="Help fund community-based violence prevention.",
            how_to="1. Find local violence intervention programs\n2. Donate or volunteer\n3. Advocate for public funding\n4. Support survivors of gun violence",
        ),
    ],

    # === FOREIGN POLICY ===
    "foreign_policy": [
        ResistanceAction(
            action_type=ActionType.CONTACT,
            title="Contact Congress on Foreign Policy",
            description="Urge representatives on international issues.",
            how_to="1. Find your senators and representative\n2. Call during business hours\n3. Reference specific bills or policies\n4. Follow up with written correspondence",
            effective_for=["federal"],
        ),
        ResistanceAction(
            action_type=ActionType.ORGANIZE,
            title="Join International Solidarity Groups",
            description="Connect with organizations working on global issues.",
            how_to="1. Find groups focused on your issue area\n2. Attend meetings and events\n3. Participate in campaigns and actions\n4. Stay informed on international developments",
            resources=[
                "https://www.amnestyusa.org/",
                "https://www.hrw.org/",
            ],
        ),
        ResistanceAction(
            action_type=ActionType.PARTICIPATE,
            title="Attend Congressional Town Halls",
            description="Question your representatives on foreign policy.",
            how_to="1. Find town halls at townhallproject.com\n2. Prepare specific questions\n3. Record responses\n4. Follow up afterward",
            resources=["https://townhallproject.com/"],
        ),
    ],
}

# Default actions that apply to any category
DEFAULT_ACTIONS: list[ResistanceAction] = [
    ResistanceAction(
        action_type=ActionType.CONTACT,
        title="Contact Your State Legislators",
        description="Reach your state representatives and senators.",
        how_to="1. Find your legislators at openstates.org\n2. Call during business hours (9am-5pm)\n3. Ask to speak to the staffer handling this issue\n4. Be polite, brief, and specific\n5. Leave your name, address, and callback number\n6. Follow up with email",
        resources=["https://openstates.org/find_your_legislator/"],
        effective_for=["state"],
    ),
    ResistanceAction(
        action_type=ActionType.CONTACT,
        title="Contact Your US Congress Members",
        description="Reach your federal representatives and senators.",
        how_to="1. Find your representative at house.gov\n2. Find your senators at senate.gov\n3. Call the DC office for policy, local office for casework\n4. Be polite, brief, and specific about the bill\n5. Ask for a response in writing",
        resources=[
            "https://www.house.gov/representatives/find-your-representative",
            "https://www.senate.gov/senators/senators-contact.htm",
        ],
        effective_for=["federal"],
    ),
    ResistanceAction(
        action_type=ActionType.CONTACT,
        title="Contact Your Local Officials",
        description="Reach city council, mayor, and county officials.",
        how_to="1. Find your city council member's contact info\n2. Call or email about local issues\n3. Attend city council meetings\n4. Sign up for public comment",
        effective_for=["local"],
    ),
    ResistanceAction(
        action_type=ActionType.INFORM,
        title="Share Information",
        description="Spread awareness about this issue in your community.",
        how_to="1. Share verified news articles on social media\n2. Talk to friends and family\n3. Write letters to local newspapers\n4. Create or share educational content",
    ),
    ResistanceAction(
        action_type=ActionType.ORGANIZE,
        title="Find Local Advocacy Groups",
        description="Connect with organizations working on this issue.",
        how_to="1. Search for local chapters of national organizations\n2. Check community calendars for events\n3. Attend a meeting or event\n4. Sign up for action alerts",
    ),
]


def get_actions_for_category(category_slug: str) -> list[ResistanceAction]:
    """Get specific actions for a category, plus default actions."""
    category_actions = CATEGORY_ACTIONS.get(category_slug, [])
    return category_actions + DEFAULT_ACTIONS


def get_actions_by_type(
    category_slug: str,
    action_type: ActionType
) -> list[ResistanceAction]:
    """Get actions of a specific type for a category."""
    all_actions = get_actions_for_category(category_slug)
    return [a for a in all_actions if a.action_type == action_type]


def get_urgent_actions(category_slug: str) -> list[ResistanceAction]:
    """Get urgent/immediate actions for a category."""
    all_actions = get_actions_for_category(category_slug)
    return [a for a in all_actions if a.urgency == ActionUrgency.IMMEDIATE]


def get_actions_for_jurisdiction(
    category_slug: str,
    jurisdiction: str  # "federal", "state", "local"
) -> list[ResistanceAction]:
    """Get actions effective for a specific jurisdiction."""
    all_actions = get_actions_for_category(category_slug)
    return [
        a for a in all_actions
        if not a.effective_for or jurisdiction in a.effective_for
    ]
