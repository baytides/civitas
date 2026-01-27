"""Pydantic models for Supreme Court data."""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class SCOTUSOpinion(BaseModel):
    """A Supreme Court opinion."""

    citation: str
    case_name: str
    docket_number: str
    decision_date: date
    term: str

    # Vote
    vote_majority: Optional[int] = None
    vote_dissent: Optional[int] = None

    # Authors
    majority_author: Optional[str] = None

    # Content
    holding: Optional[str] = None
    syllabus: Optional[str] = None
    majority_opinion: Optional[str] = None
    dissent_opinion: Optional[str] = None
    concurrence_opinion: Optional[str] = None

    # URLs
    pdf_url: Optional[str] = None
    azure_url: Optional[str] = None  # Stored copy in Azure


class SCOTUSListingItem(BaseModel):
    """Item from SCOTUS slip opinions listing."""

    case_name: str
    docket_number: str
    decision_date: date
    pdf_url: str
    term: str
