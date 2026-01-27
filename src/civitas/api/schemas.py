"""Pydantic schemas for API responses."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

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
    chapter: Optional[str] = None
    agency: str
    proposal_text: str
    proposal_summary: Optional[str] = None
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
    implementation_notes: Optional[str] = None
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


# =============================================================================
# Executive Orders
# =============================================================================


class ExecutiveOrderBase(BaseModel):
    """Base schema for executive orders."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_number: str
    executive_order_number: Optional[int] = None
    title: str
    signing_date: Optional[date] = None
    publication_date: Optional[date] = None
    president: Optional[str] = None
    abstract: Optional[str] = None


class ExecutiveOrderDetail(ExecutiveOrderBase):
    """Detailed EO with matched objectives."""

    pdf_url: Optional[str] = None
    html_url: Optional[str] = None
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
    decision_date: Optional[date] = None
    status: Optional[str] = None


class CourtCaseDetail(CourtCaseBase):
    """Detailed court case."""

    docket_number: Optional[str] = None
    holding: Optional[str] = None
    majority_author: Optional[str] = None
    dissent_author: Optional[str] = None
    source_url: Optional[str] = None
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
    title: Optional[str] = None
    chamber: str
    session: str
    status: Optional[str] = None
    introduced_date: Optional[date] = None


class StateLegislatorBase(BaseModel):
    """Base schema for state legislators."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    chamber: str
    district: Optional[str] = None
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
    legal_basis: Optional[str] = None
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
    blocked_date: Optional[date] = None


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
