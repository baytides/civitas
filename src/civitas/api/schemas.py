"""Pydantic schemas for API responses."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

# =============================================================================
# Pagination
# =============================================================================


class PaginatedResponse(BaseModel):
    """Base class for paginated responses."""

    page: int
    per_page: int
    total: int
    total_pages: int


# =============================================================================
# P2025 Objectives
# =============================================================================


class ObjectiveBase(BaseModel):
    """Base schema for P2025 objectives."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    section: str
    chapter: str | None = None
    agency: str
    proposal_text: str
    proposal_summary: str | None = None
    page_number: int
    category: str
    action_type: str
    priority: str
    implementation_timeline: str
    status: str
    confidence: float


class ObjectiveDetail(ObjectiveBase):
    """Detailed objective with related data."""

    keywords: list[str] = []
    constitutional_concerns: list[str] = []
    matching_eo_ids: list[int] = []
    matching_legislation_ids: list[int] = []
    implementation_notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ObjectiveList(PaginatedResponse):
    """Paginated list of objectives."""

    items: list[ObjectiveBase]


class ObjectiveStats(BaseModel):
    """Aggregated statistics for objectives."""

    total: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    by_priority: dict[str, int]
    by_timeline: dict[str, int]
    completion_percentage: float


class ObjectiveMetadata(BaseModel):
    """Distinct metadata values for objectives."""

    categories: list[str]
    statuses: list[str]
    priorities: list[str]
    timelines: list[str]


# =============================================================================
# Executive Orders
# =============================================================================


class ExecutiveOrderBase(BaseModel):
    """Base schema for executive orders."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_number: str
    executive_order_number: int | None = None
    title: str
    signing_date: date | None = None
    publication_date: date | None = None
    president: str | None = None
    abstract: str | None = None


class ExecutiveOrderDetail(ExecutiveOrderBase):
    """Detailed EO with matched objectives."""

    pdf_url: str | None = None
    html_url: str | None = None
    matched_objectives: list[ObjectiveBase] = []


class ExecutiveOrderList(PaginatedResponse):
    """Paginated list of executive orders."""

    items: list[ExecutiveOrderBase]


# =============================================================================
# Court Cases
# =============================================================================


class CourtCaseBase(BaseModel):
    """Base schema for court cases."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    citation: str
    case_name: str
    court_level: str
    court: str
    decision_date: date | None = None
    status: str | None = None


class CourtCaseDetail(CourtCaseBase):
    """Detailed court case."""

    docket_number: str | None = None
    holding: str | None = None
    majority_author: str | None = None
    dissent_author: str | None = None
    source_url: str | None = None
    linked_objectives: list[ObjectiveBase] = []


class CourtCaseList(PaginatedResponse):
    """Paginated list of court cases."""

    items: list[CourtCaseBase]


# =============================================================================
# States
# =============================================================================


class StateBase(BaseModel):
    """Base schema for state data."""

    code: str
    name: str
    bill_count: int = 0
    legislator_count: int = 0
    resistance_action_count: int = 0


class StateBillBase(BaseModel):
    """Base schema for state bills."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    identifier: str
    title: str | None = None
    chamber: str
    session: str
    status: str | None = None
    introduced_date: date | None = None


class StateLegislatorBase(BaseModel):
    """Base schema for state legislators."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    chamber: str
    district: str | None = None
    party: str
    state: str


class StateDetail(StateBase):
    """Detailed state info."""

    recent_bills: list[StateBillBase] = []
    legislators: list[StateLegislatorBase] = []


class StateList(BaseModel):
    """List of all states."""

    items: list[StateBase]


# =============================================================================
# Resistance
# =============================================================================


class ResistanceRecommendation(BaseModel):
    """A resistance recommendation for an objective."""

    tier: str  # tier_1_immediate, tier_2_congressional, tier_3_presidential
    action_type: str
    title: str
    description: str
    legal_basis: str | None = None
    likelihood: str  # high, medium, low
    prerequisites: list[str] = []


class ResistanceAnalysis(BaseModel):
    """AI analysis of an objective's vulnerabilities."""

    objective_id: int
    constitutional_issues: list[dict] = []
    challenge_strategies: list[dict] = []
    state_resistance_options: list[dict] = []
    overall_vulnerability_score: int


class ProgressSummary(BaseModel):
    """Overall P2025 implementation progress."""

    total_objectives: int
    by_status: dict[str, int]
    completion_percentage: float
    recent_activity: list[dict] = []
    blocked_count: int


class BlockedPolicy(BaseModel):
    """A policy that has been blocked."""

    objective_id: int
    agency: str
    proposal_summary: str
    blocked_by: str  # court, state, congress
    case_or_action: str
    blocked_date: date | None = None


class ResistanceTierAction(BaseModel):
    """General action used in tier overviews."""

    title: str
    description: str
    urgency: str
    resources: list[str]


class ResistanceTier(BaseModel):
    """Tier metadata used by the resistance UI."""

    tier: int
    id: str
    title: str
    subtitle: str
    color: str
    description: str
    general_actions: list[ResistanceTierAction]


class ResistanceOrganization(BaseModel):
    """Organization entry for resistance resources."""

    name: str
    url: str


class ResistanceOrganizationSection(BaseModel):
    """Section of resistance organizations."""

    title: str
    items: list[ResistanceOrganization]


class ResistanceMeta(BaseModel):
    """Metadata for resistance pages."""

    tiers: list[ResistanceTier]
    organization_sections: list[ResistanceOrganizationSection]


# =============================================================================
# Search
# =============================================================================


class SearchResult(BaseModel):
    """A search result item."""

    type: str  # objective, eo, case, bill
    id: int
    title: str
    snippet: str
    score: float


class SearchResponse(BaseModel):
    """Search response."""

    query: str
    total: int
    items: list[SearchResult]
