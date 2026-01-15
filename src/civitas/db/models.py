"""SQLAlchemy models for the unified Civitas database.

This schema consolidates data from multiple sources:
- U.S. Congress (federal legislation)
- California Legislature (state legislation)
- Supreme Court (future)
- Other state legislatures (future)
"""

from __future__ import annotations

from datetime import date, datetime
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
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
# Future: Court Cases
# =============================================================================

class CourtCase(Base):
    """Supreme Court or other court case (future)."""

    __tablename__ = "court_cases"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Identification
    citation: Mapped[str] = mapped_column(String(100), unique=True, index=True)  # e.g., "598 U.S. 651"
    case_name: Mapped[str] = mapped_column(String(500))
    docket_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Court
    court: Mapped[str] = mapped_column(String(100))  # "Supreme Court", etc.

    # Decision
    decision_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)

    # Vote
    vote_majority: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vote_dissent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Authors
    majority_author: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Content
    holding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    majority_opinion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dissent_opinion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    concurrence_opinion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# =============================================================================
# Database Initialization
# =============================================================================

def create_database(db_path: str = "civitas.db") -> None:
    """Create all database tables."""
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    return engine


def get_engine(db_path: str = "civitas.db"):
    """Get database engine."""
    return create_engine(f"sqlite:///{db_path}")
