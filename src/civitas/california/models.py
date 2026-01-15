"""Pydantic models for California Legislature data.

Based on the capublic database schema from:
https://downloads.leginfo.legislature.ca.gov/pubinfo_load.zip
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Bill(BaseModel):
    """California Legislature bill record.

    Corresponds to BILL_TBL in the capublic database.
    """

    bill_id: str = Field(description="Unique bill identifier (e.g., '20230AB1')")
    session_year: str = Field(description="Legislative session year (e.g., '20232024')")
    session_num: str = Field(description="Session number (0=regular, 1/2=special)")
    measure_type: str = Field(description="Bill type: AB, SB, ACA, SCA, ACR, SCR, AJR, SJR, AR, SR")
    measure_num: int = Field(description="Bill number")
    measure_state: str = Field(description="Current state of the measure")
    chapter_year: Optional[str] = Field(default=None, description="Year chaptered (if enacted)")
    chapter_type: Optional[str] = Field(default=None, description="Chapter type")
    chapter_num: Optional[str] = Field(default=None, description="Chapter number (if enacted)")
    latest_bill_version_id: Optional[str] = Field(default=None, description="ID of latest version")
    current_location: Optional[str] = Field(default=None, description="Current committee/location")
    current_house: Optional[str] = Field(default=None, description="Current house (Assembly/Senate)")
    current_status: Optional[str] = Field(default=None, description="Current status")
    active_flg: str = Field(default="Y", description="Active flag")

    @property
    def citation(self) -> str:
        """Generate standard bill citation (e.g., 'AB 1234')."""
        return f"{self.measure_type} {self.measure_num}"

    @property
    def is_chaptered(self) -> bool:
        """Check if bill has been enacted into law."""
        return self.chapter_num is not None

    @property
    def chapter_citation(self) -> Optional[str]:
        """Generate chapter citation if enacted (e.g., 'Chapter 123, Statutes of 2023')."""
        if self.chapter_num and self.chapter_year:
            return f"Chapter {self.chapter_num}, Statutes of {self.chapter_year}"
        return None


class BillVersion(BaseModel):
    """Bill version with full text.

    Corresponds to BILL_VERSION_TBL in the capublic database.
    """

    bill_version_id: str = Field(description="Unique version identifier")
    bill_id: str = Field(description="Parent bill ID")
    version_num: int = Field(description="Version number")
    bill_version_action_date: datetime = Field(description="Date of this version")
    bill_version_action: Optional[str] = Field(default=None, description="Action type")
    subject: Optional[str] = Field(default=None, description="Bill subject/digest")
    vote_required: Optional[str] = Field(default=None, description="Vote threshold required")
    appropriation: Optional[str] = Field(default=None, description="Contains appropriation (YES/NO)")
    fiscal_committee: Optional[str] = Field(default=None, description="Requires fiscal review (YES/NO)")
    urgency: Optional[str] = Field(default=None, description="Urgency clause (YES/NO)")
    bill_xml: Optional[str] = Field(default=None, description="Full bill text in XML format")
    active_flg: str = Field(default="Y")


class BillVersionAuthor(BaseModel):
    """Bill author/coauthor information.

    Corresponds to BILL_VERSION_AUTHORS_TBL in the capublic database.
    """

    bill_version_id: str
    type: str = Field(description="Author type: LEAD_AUTHOR, COAUTHOR, etc.")
    house: Optional[str] = Field(default=None, description="Assembly or Senate")
    name: Optional[str] = Field(default=None, description="Author name")
    contribution: Optional[str] = Field(default=None, description="Contribution type")
    primary_author_flg: str = Field(default="N")


class BillHistory(BaseModel):
    """Bill action/history record.

    Corresponds to BILL_HISTORY_TBL in the capublic database.
    """

    bill_id: str
    bill_history_id: Optional[int] = None
    action_date: Optional[datetime] = None
    action: Optional[str] = Field(default=None, description="Action text")
    action_sequence: Optional[int] = None
    action_code: Optional[str] = None
    action_status: Optional[str] = None
    primary_location: Optional[str] = None
    secondary_location: Optional[str] = None
    end_status: Optional[str] = None


class BillAnalysis(BaseModel):
    """Committee analysis of a bill.

    Corresponds to BILL_ANALYSIS_TBL in the capublic database.
    """

    analysis_id: int
    bill_id: str
    house: Optional[str] = Field(default=None, description="A=Assembly, S=Senate")
    analysis_type: Optional[str] = None
    committee_code: Optional[str] = None
    committee_name: Optional[str] = None
    analysis_date: Optional[datetime] = None
    # source_doc is LONGBLOB - full analysis document
    active_flg: str = Field(default="Y")


class BillSummaryVote(BaseModel):
    """Summary vote record for a bill.

    Corresponds to BILL_SUMMARY_VOTE_TBL in the capublic database.
    """

    bill_id: str
    location_code: str = Field(description="Committee/floor code")
    vote_date_time: datetime
    vote_date_seq: int
    motion_id: int
    ayes: Optional[int] = None
    noes: Optional[int] = None
    abstain: Optional[int] = None
    vote_result: Optional[str] = Field(default=None, description="PASS/FAIL")
    file_location: Optional[str] = None
    session_date: Optional[datetime] = None


class BillDetailVote(BaseModel):
    """Individual legislator vote on a bill.

    Corresponds to BILL_DETAIL_VOTE_TBL in the capublic database.
    """

    bill_id: str
    location_code: str
    legislator_name: str
    vote_date_time: datetime
    vote_date_seq: int
    vote_code: Optional[str] = Field(default=None, description="AYE, NOE, ABS, NVR")
    motion_id: int
    member_order: Optional[int] = None
    session_date: Optional[datetime] = None
    speaker: Optional[str] = None


class BillMotion(BaseModel):
    """Vote motion text.

    Corresponds to BILL_MOTION_TBL in the capublic database.
    """

    motion_id: int
    motion_text: Optional[str] = None


class Legislator(BaseModel):
    """California state legislator.

    Corresponds to LEGISLATOR_TBL in the capublic database.
    """

    district: str
    session_year: Optional[str] = None
    legislator_name: Optional[str] = None
    house_type: Optional[str] = Field(default=None, description="A=Assembly, S=Senate")
    author_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_initial: Optional[str] = None
    party: Optional[str] = Field(default=None, description="DEM, REP, etc.")
    active_flg: str = Field(default="Y")
    active_legislator: Optional[str] = Field(default="Y")

    @property
    def full_name(self) -> str:
        """Get legislator's full name."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.middle_initial:
            parts.append(f"{self.middle_initial}.")
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else self.legislator_name or ""

    @property
    def chamber(self) -> str:
        """Get chamber name."""
        return "Assembly" if self.house_type == "A" else "Senate" if self.house_type == "S" else ""


class LawSection(BaseModel):
    """California law code section.

    Corresponds to LAW_SECTION_TBL in the capublic database.
    """

    id: str
    law_code: Optional[str] = Field(default=None, description="Code abbreviation (e.g., GOV, PRC)")
    section_num: Optional[str] = None
    effective_date: Optional[datetime] = None
    division: Optional[str] = None
    title: Optional[str] = None
    part: Optional[str] = None
    chapter: Optional[str] = None
    article: Optional[str] = None
    history: Optional[str] = Field(default=None, description="Legislative history")
    content_xml: Optional[str] = Field(default=None, description="Section content in XML")
    active_flg: str = Field(default="Y")


class LawCode(BaseModel):
    """California law code (e.g., Government Code, Public Resources Code).

    Corresponds to CODES_TBL in the capublic database.
    """

    code: str = Field(description="Code abbreviation")
    title: Optional[str] = Field(default=None, description="Full code title")


class VetoMessage(BaseModel):
    """Governor's veto message.

    Corresponds to VETO_MESSAGE_TBL in the capublic database.
    """

    bill_id: str
    veto_date: Optional[datetime] = None
    message: Optional[str] = Field(default=None, description="Full veto message text")


class CommitteeHearing(BaseModel):
    """Committee hearing record.

    Corresponds to COMMITTEE_HEARING_TBL in the capublic database.
    """

    bill_id: str
    committee_type: Optional[str] = None
    committee_nr: Optional[int] = None
    hearing_date: Optional[datetime] = None
    location_code: Optional[str] = None


class LocationCode(BaseModel):
    """Location/committee code lookup.

    Corresponds to LOCATION_CODE_TBL in the capublic database.
    """

    session_year: Optional[str] = None
    location_code: str
    location_type: str
    description: Optional[str] = None
    long_description: Optional[str] = None
    active_flg: str = Field(default="Y")
