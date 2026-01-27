"""SQLAlchemy models for the unified Civitas database.

This schema consolidates data from multiple sources:
- U.S. Congress (federal legislation)
- California Legislature (state legislation)
- Supreme Court (future)
- Other state legislatures (future)
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


def utcnow() -> datetime:
    """Return timezone-aware UTC now for consistent timestamps."""
    return datetime.now(UTC)


# =============================================================================
# Enums
# =============================================================================

class Jurisdiction(str):
    """Jurisdiction types."""
    FEDERAL = "federal"
    CALIFORNIA = "california"
    # Add more states as needed


class LegislationType(str):
    """Types of legislation."""
    BILL = "bill"
    RESOLUTION = "resolution"
    JOINT_RESOLUTION = "joint_resolution"
    CONCURRENT_RESOLUTION = "concurrent_resolution"
    CONSTITUTIONAL_AMENDMENT = "constitutional_amendment"


class Chamber(str):
    """Legislative chambers."""
    HOUSE = "house"  # US House / CA Assembly
    SENATE = "senate"
    JOINT = "joint"


class VoteType(str):
    """Vote types."""
    AYE = "aye"
    NAY = "nay"
    ABSTAIN = "abstain"
    NOT_VOTING = "not_voting"
    PRESENT = "present"


# =============================================================================
# Core Models
# =============================================================================

class Legislation(Base):
    """Unified legislation record (bills, resolutions, etc.)."""

    __tablename__ = "legislation"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Source identification
    jurisdiction: Mapped[str] = mapped_column(String(50), index=True)  # federal, california, etc.
    source_id: Mapped[str] = mapped_column(String(100))  # Original ID from source

    # Core fields
    legislation_type: Mapped[str] = mapped_column(String(50))
    number: Mapped[int] = mapped_column(Integer)
    chamber: Mapped[str] = mapped_column(String(20))
    session: Mapped[str] = mapped_column(String(20), index=True)  # e.g., "118" or "20232024"

    # Display
    citation: Mapped[str] = mapped_column(String(50), index=True)  # e.g., "H.R. 1234", "AB 567"
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    current_location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Dates
    introduced_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_action_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)

    # Enacted law info
    is_enacted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    public_law_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    enacted_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    chapter_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Full text
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Subject/topics
    subjects: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    policy_area: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Metadata
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    versions: Mapped[list["LegislationVersion"]] = relationship(back_populates="legislation")
    actions: Mapped[list["LegislationAction"]] = relationship(back_populates="legislation")
    votes: Mapped[list["Vote"]] = relationship(back_populates="legislation")
    sponsors: Mapped[list["Sponsorship"]] = relationship(back_populates="legislation")

    __table_args__ = (
        UniqueConstraint("jurisdiction", "source_id", name="uq_legislation_source"),
        Index("ix_legislation_search", "jurisdiction", "session", "is_enacted"),
    )


class LegislationVersion(Base):
    """Version of legislation (amendments, engrossed, enrolled, etc.)."""

    __tablename__ = "legislation_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    legislation_id: Mapped[int] = mapped_column(ForeignKey("legislation.id"), index=True)

    version_number: Mapped[int] = mapped_column(Integer)
    version_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    version_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Content
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    legislation: Mapped["Legislation"] = relationship(back_populates="versions")


class LegislationAction(Base):
    """Action/history entry for legislation."""

    __tablename__ = "legislation_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    legislation_id: Mapped[int] = mapped_column(ForeignKey("legislation.id"), index=True)

    action_date: Mapped[date] = mapped_column(Date, index=True)
    action_text: Mapped[str] = mapped_column(Text)
    action_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    chamber: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Location
    committee: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    legislation: Mapped["Legislation"] = relationship(back_populates="actions")


class Legislator(Base):
    """Elected official (federal or state)."""

    __tablename__ = "legislators"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Source identification
    jurisdiction: Mapped[str] = mapped_column(String(50), index=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # bioguide_id, etc.

    # Name
    full_name: Mapped[str] = mapped_column(String(200))
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Position
    chamber: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    party: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Status
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    # Terms served (JSON)
    terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    sponsorships: Mapped[list["Sponsorship"]] = relationship(back_populates="legislator")
    vote_records: Mapped[list["VoteRecord"]] = relationship(back_populates="legislator")

    __table_args__ = (
        Index("ix_legislator_search", "jurisdiction", "chamber", "state"),
    )


class Sponsorship(Base):
    """Sponsor/cosponsor relationship."""

    __tablename__ = "sponsorships"

    id: Mapped[int] = mapped_column(primary_key=True)
    legislation_id: Mapped[int] = mapped_column(ForeignKey("legislation.id"), index=True)
    legislator_id: Mapped[int] = mapped_column(ForeignKey("legislators.id"), index=True)

    sponsorship_type: Mapped[str] = mapped_column(String(50))  # sponsor, cosponsor, author, coauthor
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    legislation: Mapped["Legislation"] = relationship(back_populates="sponsors")
    legislator: Mapped["Legislator"] = relationship(back_populates="sponsorships")


class Vote(Base):
    """Vote on legislation (roll call)."""

    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(primary_key=True)
    legislation_id: Mapped[int] = mapped_column(ForeignKey("legislation.id"), index=True)

    vote_date: Mapped[date] = mapped_column(Date, index=True)
    chamber: Mapped[str] = mapped_column(String(20))

    # Results
    ayes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nays: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    abstain: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    not_voting: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    result: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # passed, failed

    # Motion
    motion_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    legislation: Mapped["Legislation"] = relationship(back_populates="votes")
    records: Mapped[list["VoteRecord"]] = relationship(back_populates="vote")


class VoteRecord(Base):
    """Individual legislator's vote."""

    __tablename__ = "vote_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    vote_id: Mapped[int] = mapped_column(ForeignKey("votes.id"), index=True)
    legislator_id: Mapped[int] = mapped_column(ForeignKey("legislators.id"), index=True)

    vote_cast: Mapped[str] = mapped_column(String(20))  # aye, nay, abstain, not_voting

    vote: Mapped["Vote"] = relationship(back_populates="records")
    legislator: Mapped["Legislator"] = relationship(back_populates="vote_records")


class LawCode(Base):
    """Law code (e.g., California Government Code, U.S. Code)."""

    __tablename__ = "law_codes"

    id: Mapped[int] = mapped_column(primary_key=True)

    jurisdiction: Mapped[str] = mapped_column(String(50), index=True)
    code: Mapped[str] = mapped_column(String(20))  # GOV, PRC, USC, etc.
    title: Mapped[str] = mapped_column(String(500))

    sections: Mapped[list["LawSection"]] = relationship(back_populates="law_code")

    __table_args__ = (
        UniqueConstraint("jurisdiction", "code", name="uq_law_code"),
    )


class LawSection(Base):
    """Section of a law code."""

    __tablename__ = "law_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    law_code_id: Mapped[int] = mapped_column(ForeignKey("law_codes.id"), index=True)

    section_number: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Hierarchy
    division: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    part: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    chapter: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    article: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Content
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # History
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    law_code: Mapped["LawCode"] = relationship(back_populates="sections")


# =============================================================================
# Court Cases (SCOTUS, Circuit, District)
# =============================================================================

class CourtCase(Base):
    """Court case (Supreme Court, Circuit, District).

    Stores cases from:
    - Supreme Court (via supremecourt.gov)
    - Circuit Courts of Appeals (via Court Listener)
    - District Courts (via Court Listener)
    """

    __tablename__ = "court_cases"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Identification
    citation: Mapped[str] = mapped_column(String(100), index=True)  # e.g., "598 U.S. 651"
    case_name: Mapped[str] = mapped_column(String(500))
    docket_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Court hierarchy
    court_level: Mapped[str] = mapped_column(String(20), index=True, default="unknown")  # scotus, circuit, district
    court: Mapped[str] = mapped_column(String(100), index=True)  # "Supreme Court", "ca9", etc.
    court_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # Full court name

    # SCOTUS-specific
    term: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Dates
    decision_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    argument_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_filed: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Vote (primarily for SCOTUS)
    vote_majority: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vote_dissent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Authors
    majority_author: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Content
    holding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    syllabus: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    majority_opinion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dissent_opinion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    concurrence_opinion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Litigation tracking
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # decided, pending
    outcome: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # affirmed, reversed

    # Related legislation (for cases challenging laws)
    legislation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("legislation.id"), nullable=True)

    # Appeals chain
    parent_case_id: Mapped[Optional[int]] = mapped_column(ForeignKey("court_cases.id"), nullable=True)

    # Storage
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    azure_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # PDF in Azure
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # External ID (Court Listener)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("court", "docket_number", name="uq_court_case_docket"),
        Index("ix_court_case_search", "court_level", "court", "decision_date"),
    )


# =============================================================================
# Project 2025 Tracking
# =============================================================================

class Project2025Policy(Base):
    """A policy proposal from Project 2025 Mandate for Leadership.

    Used to track which proposals are being implemented through
    legislation, executive orders, or agency actions.

    Enhanced fields support AI-assisted extraction:
    - category: Policy area (immigration, environment, healthcare, etc.)
    - priority: Urgency level (high, medium, low)
    - implementation_timeline: When to implement (day_one, first_100_days, etc.)
    - action_type: Type of action (eliminate, restructure, create, etc.)
    - constitutional_concerns: Potential legal vulnerabilities (JSON array)
    - confidence: AI extraction confidence score (0-1)
    """

    __tablename__ = "project2025_policies"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Document location
    section: Mapped[str] = mapped_column(String(200))  # Section title
    chapter: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    page_number: Mapped[int] = mapped_column(Integer)

    # Target agency
    agency: Mapped[str] = mapped_column(String(100), index=True)

    # Proposal content
    proposal_text: Mapped[str] = mapped_column(Text)
    proposal_summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Keywords for matching
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    # Enhanced categorization (from AI-assisted extraction)
    category: Mapped[str] = mapped_column(String(50), default="general", index=True)
    # Categories: immigration, environment, healthcare, education, civil_rights, labor,
    #             economy, defense, justice, government_structure, general

    action_type: Mapped[str] = mapped_column(String(50), default="unknown")
    # Actions: eliminate, restructure, reduce, create, modify, privatize, repeal, unknown

    priority: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    # Priority: high, medium, low

    implementation_timeline: Mapped[str] = mapped_column(String(50), default="unknown")
    # Timeline: day_one, first_100_days, first_year, long_term, unknown

    # Constitutional analysis
    constitutional_concerns: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    # e.g., ["First Amendment - free speech", "Tenth Amendment - federalism"]

    # AI confidence score (0.0 - 1.0)
    confidence: Mapped[float] = mapped_column(default=0.5)

    # Tracking status
    status: Mapped[str] = mapped_column(String(50), default="proposed", index=True)
    # Status values: proposed, in_progress, completed, blocked, reversed

    # Matched items (JSON arrays of IDs)
    matching_legislation_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    matching_eo_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    matching_rule_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Analysis
    implementation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_p2025_agency_status", "agency", "status"),
        Index("ix_p2025_category_priority", "category", "priority"),
        Index("ix_p2025_timeline", "implementation_timeline"),
    )


class P2025Implementation(Base):
    """Tracks implementation of a P2025 policy through specific actions.

    Links P2025 objectives to concrete government actions (EOs, rules, etc.)
    """

    __tablename__ = "p2025_implementations"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Link to policy
    policy_id: Mapped[int] = mapped_column(ForeignKey("project2025_policies.id"), index=True)

    # Implementation type and reference
    action_type: Mapped[str] = mapped_column(String(50))  # executive_order, rule, memo, guidance, personnel
    action_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # FK to EO/rule table
    action_reference: Mapped[str] = mapped_column(String(200))  # e.g., "EO 14XXX", "FR 2025-XXXX"

    # Status
    status: Mapped[str] = mapped_column(String(50), index=True)  # announced, in_progress, completed, blocked, reversed
    implementation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Evidence
    evidence_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_urls: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    # AI analysis
    ai_confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)  # 0.0-1.0

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class LegalChallenge(Base):
    """Legal challenges to P2025 implementations or executive actions.

    Tracks court cases challenging specific policies.
    """

    __tablename__ = "legal_challenges"

    id: Mapped[int] = mapped_column(primary_key=True)

    # What's being challenged
    p2025_policy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("project2025_policies.id"), nullable=True)
    implementation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("p2025_implementations.id"), nullable=True)
    executive_order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("executive_orders.id"), nullable=True)

    # Challenge details
    challenge_type: Mapped[str] = mapped_column(String(50), index=True)
    # Types: constitutional, apa, ultra_vires, equal_protection, due_process, statutory

    legal_basis: Mapped[str] = mapped_column(Text)  # Specific clause/statute
    constitutional_provisions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    # Court info
    court_level: Mapped[str] = mapped_column(String(20))  # district, circuit, scotus
    court_name: Mapped[str] = mapped_column(String(200))
    court_case_id: Mapped[Optional[int]] = mapped_column(ForeignKey("court_cases.id"), nullable=True)
    case_citation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    docket_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Parties
    lead_plaintiffs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    representing_orgs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array (ACLU, etc.)

    # Status
    status: Mapped[str] = mapped_column(String(50), index=True)
    # Status: filed, pending, preliminary_injunction, stayed, won, lost, appealed, settled, dismissed

    filed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    decision_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Outcome
    outcome_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    precedent_value: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # binding, persuasive, limited

    # Links
    complaint_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ruling_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_legal_challenge_status_type", "status", "challenge_type"),
    )


class StateResistanceAction(Base):
    """State-level actions resisting federal P2025 implementations.

    10th Amendment, sanctuary policies, state lawsuits, etc.
    """

    __tablename__ = "state_resistance_actions"

    id: Mapped[int] = mapped_column(primary_key=True)

    # State
    state_code: Mapped[str] = mapped_column(String(2), index=True)
    state_name: Mapped[str] = mapped_column(String(50))

    # What it counters
    p2025_policy_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    category: Mapped[str] = mapped_column(String(50), index=True)
    # Categories: immigration, environment, healthcare, lgbtq, education, labor, voting, civil_rights

    # Action details
    action_type: Mapped[str] = mapped_column(String(50), index=True)
    # Types: sanctuary_policy, state_lawsuit, legislation, executive_order, constitutional_amendment, budget_action

    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    legal_citation: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), index=True)
    # Status: proposed, passed, enacted, enjoined, effective, overturned

    introduced_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Replication
    is_model_legislation: Mapped[bool] = mapped_column(Boolean, default=False)
    model_legislation_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    states_adopted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of state codes

    # Links
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    full_text_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_state_resistance_state_category", "state_code", "category"),
    )


class ResistanceRecommendation(Base):
    """AI-generated recommendations for countering P2025 policies.

    Generated by Carl (Ollama/Llama) analyzing legal data.
    """

    __tablename__ = "resistance_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)

    # What it addresses
    p2025_policy_id: Mapped[int] = mapped_column(ForeignKey("project2025_policies.id"), index=True)
    implementation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("p2025_implementations.id"), nullable=True)

    # Recommendation tier
    tier: Mapped[str] = mapped_column(String(20), index=True)
    # Tiers: tier_1_immediate, tier_2_congressional, tier_3_presidential

    # Recommendation details
    action_type: Mapped[str] = mapped_column(String(50))
    # Types: legal_challenge, state_legislation, public_comment, foia_request, organizing,
    #        congressional_oversight, statutory_reversal, executive_reversal

    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)

    # Legal basis
    legal_basis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relevant_precedents: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of case citations
    constitutional_provisions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    statutory_provisions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    # Assessment
    likelihood_of_success: Mapped[str] = mapped_column(String(20))  # high, medium, low
    time_sensitivity: Mapped[str] = mapped_column(String(20))  # urgent, soon, long_term
    resources_required: Mapped[str] = mapped_column(String(20))  # low, medium, high

    # Prerequisites
    prerequisites: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    # Model resources
    model_complaint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Draft text
    model_legislation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Draft text
    action_steps: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    # Examples of success
    successful_examples: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    # AI metadata
    ai_model_version: Mapped[str] = mapped_column(String(50))
    ai_confidence_score: Mapped[float] = mapped_column(default=0.0)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Human review
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_resistance_rec_tier_type", "tier", "action_type"),
        Index("ix_resistance_rec_policy", "p2025_policy_id"),
    )


# =============================================================================
# Executive Actions (Executive Orders, Agency Rules)
# =============================================================================

class ExecutiveOrder(Base):
    """Executive Order from the Federal Register.

    Source: Federal Register API (US National Archives, Public Domain)
    """

    __tablename__ = "executive_orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Identification
    document_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    executive_order_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    # Content
    title: Mapped[str] = mapped_column(String(500))
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Dates
    signing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    publication_date: Mapped[date] = mapped_column(Date, index=True)

    # President
    president: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # URLs
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    html_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    xml_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    azure_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # P2025 tracking
    p2025_related: Mapped[bool] = mapped_column(Boolean, default=False)
    p2025_policy_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    # Legal status
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, challenged, enjoined, reversed
    challenged_in_court: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# =============================================================================
# Database Initialization
# =============================================================================

def get_database_url(db_url: str | None = None) -> str:
    """Get database URL from parameter, environment, or default.

    Priority:
    1. Explicit db_url parameter
    2. DATABASE_URL environment variable
    3. Default SQLite file

    Supports both SQLite and PostgreSQL:
    - SQLite: sqlite:///civitas.db
    - PostgreSQL: postgresql://user:pass@host:5432/civitas
    """
    import os

    if db_url:
        return db_url

    env_url = os.getenv("DATABASE_URL")
    if env_url:
        # Handle Heroku-style postgres:// URLs
        if env_url.startswith("postgres://"):
            env_url = env_url.replace("postgres://", "postgresql://", 1)
        return env_url

    return "sqlite:///civitas.db"


def create_database(db_url: str | None = None) -> None:
    """Create all database tables.

    Args:
        db_url: Database URL. If None, uses DATABASE_URL env var or sqlite:///civitas.db
    """
    url = get_database_url(db_url)
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return engine


def get_engine(db_url: str | None = None):
    """Get database engine.

    Args:
        db_url: Database URL. If None, uses DATABASE_URL env var or sqlite:///civitas.db
    """
    url = get_database_url(db_url)
    return create_engine(url)


# =============================================================================
# Full-Text Search (FTS5)
# =============================================================================

def setup_fts(engine) -> None:
    """Create FTS5 virtual tables for full-text search.

    This must be called after create_database() to set up:
    - legislation_fts: Searches title, summary, full_text
    - court_cases_fts: Searches case_name, holding, majority_opinion
    - law_sections_fts: Searches title, content

    FTS5 provides fast full-text search with ranking.
    """
    with engine.connect() as conn:
        # Legislation FTS
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS legislation_fts USING fts5(
                title, summary, full_text,
                content='legislation', content_rowid='id'
            )
        """))

        # Court Cases FTS
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS court_cases_fts USING fts5(
                case_name, holding, majority_opinion,
                content='court_cases', content_rowid='id'
            )
        """))

        # Law Sections FTS
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS law_sections_fts USING fts5(
                title, content,
                content='law_sections', content_rowid='id'
            )
        """))

        # Triggers to keep FTS tables in sync
        # Legislation triggers
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS legislation_ai AFTER INSERT ON legislation BEGIN
                INSERT INTO legislation_fts(rowid, title, summary, full_text)
                VALUES (new.id, new.title, new.summary, new.full_text);
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS legislation_ad AFTER DELETE ON legislation BEGIN
                INSERT INTO legislation_fts(legislation_fts, rowid, title, summary, full_text)
                VALUES ('delete', old.id, old.title, old.summary, old.full_text);
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS legislation_au AFTER UPDATE ON legislation BEGIN
                INSERT INTO legislation_fts(legislation_fts, rowid, title, summary, full_text)
                VALUES ('delete', old.id, old.title, old.summary, old.full_text);
                INSERT INTO legislation_fts(rowid, title, summary, full_text)
                VALUES (new.id, new.title, new.summary, new.full_text);
            END
        """))

        # Court Cases triggers
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS court_cases_ai AFTER INSERT ON court_cases BEGIN
                INSERT INTO court_cases_fts(rowid, case_name, holding, majority_opinion)
                VALUES (new.id, new.case_name, new.holding, new.majority_opinion);
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS court_cases_ad AFTER DELETE ON court_cases BEGIN
                INSERT INTO court_cases_fts(court_cases_fts, rowid, case_name, holding, majority_opinion)
                VALUES ('delete', old.id, old.case_name, old.holding, old.majority_opinion);
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS court_cases_au AFTER UPDATE ON court_cases BEGIN
                INSERT INTO court_cases_fts(court_cases_fts, rowid, case_name, holding, majority_opinion)
                VALUES ('delete', old.id, old.case_name, old.holding, old.majority_opinion);
                INSERT INTO court_cases_fts(rowid, case_name, holding, majority_opinion)
                VALUES (new.id, new.case_name, new.holding, new.majority_opinion);
            END
        """))

        # Law Sections triggers
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS law_sections_ai AFTER INSERT ON law_sections BEGIN
                INSERT INTO law_sections_fts(rowid, title, content)
                VALUES (new.id, new.title, new.content);
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS law_sections_ad AFTER DELETE ON law_sections BEGIN
                INSERT INTO law_sections_fts(law_sections_fts, rowid, title, content)
                VALUES ('delete', old.id, old.title, old.content);
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS law_sections_au AFTER UPDATE ON law_sections BEGIN
                INSERT INTO law_sections_fts(law_sections_fts, rowid, title, content)
                VALUES ('delete', old.id, old.title, old.content);
                INSERT INTO law_sections_fts(rowid, title, content)
                VALUES (new.id, new.title, new.content);
            END
        """))

        conn.commit()


def rebuild_fts(engine) -> None:
    """Rebuild FTS indexes from scratch.

    Call this to populate FTS tables from existing data,
    or to fix any sync issues.
    """
    with engine.connect() as conn:
        # Rebuild legislation FTS
        conn.execute(text("INSERT INTO legislation_fts(legislation_fts) VALUES('rebuild')"))

        # Rebuild court cases FTS
        conn.execute(text("INSERT INTO court_cases_fts(court_cases_fts) VALUES('rebuild')"))

        # Rebuild law sections FTS
        conn.execute(text("INSERT INTO law_sections_fts(law_sections_fts) VALUES('rebuild')"))

        conn.commit()
