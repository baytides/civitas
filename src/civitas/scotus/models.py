"""Pydantic models for Supreme Court data."""

from datetime import date

from pydantic import BaseModel


class SCOTUSOpinion(BaseModel):
    """A Supreme Court opinion."""

    citation: str
    case_name: str
    docket_number: str
    decision_date: date
    term: str

    # Vote
    vote_majority: int | None = None
    vote_dissent: int | None = None

    # Authors
    majority_author: str | None = None
    majority_authors: list[str] = []
    dissent_authors: list[str] = []
    concurrence_authors: list[str] = []

    # Content
    holding: str | None = None
    syllabus: str | None = None
    majority_opinion: str | None = None
    dissent_opinion: str | None = None
    concurrence_opinion: str | None = None

    # URLs
    pdf_url: str | None = None
    azure_url: str | None = None  # Stored copy in Azure


class SCOTUSListingItem(BaseModel):
    """Item from SCOTUS slip opinions listing."""

    case_name: str
    docket_number: str
    decision_date: date
    pdf_url: str
    term: str
