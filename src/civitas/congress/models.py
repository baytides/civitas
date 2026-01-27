"""Pydantic models for Congress.gov API responses."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class LatestAction(BaseModel):
    """Latest action taken on a bill."""

    action_date: date = Field(alias="actionDate")
    text: str


class LawReference(BaseModel):
    """Reference to an enacted law."""

    number: str
    type: str  # "Public Law" or "Private Law"


class BillSummary(BaseModel):
    """Bill from list endpoint."""

    congress: int
    number: str
    type: str
    title: str
    origin_chamber: str = Field(alias="originChamber")
    origin_chamber_code: str = Field(alias="originChamberCode")
    latest_action: LatestAction = Field(alias="latestAction")
    update_date: datetime = Field(alias="updateDate")
    url: str
    laws: Optional[list[LawReference]] = None
    model_config = ConfigDict(populate_by_name=True)


class PolicyArea(BaseModel):
    """Policy area/subject category."""

    name: str


class CRSSummary(BaseModel):
    """Congressional Research Service summary."""

    action_date: date = Field(alias="actionDate")
    action_desc: str = Field(alias="actionDesc")
    text: str
    update_date: datetime = Field(alias="updateDate")
    version_code: str = Field(alias="versionCode")


class Sponsor(BaseModel):
    """Bill sponsor information."""

    bioguide_id: str = Field(alias="bioguideId")
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    full_name: str = Field(alias="fullName")
    party: Optional[str] = None
    state: Optional[str] = None
    district: Optional[int] = None
    is_by_request: Optional[str] = Field(default=None, alias="isByRequest")
    model_config = ConfigDict(populate_by_name=True)


class TextVersion(BaseModel):
    """Bill text version."""

    date: Optional[date] = None
    type: str
    url: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True)


class BillDetail(BaseModel):
    """Detailed bill information."""

    congress: int
    number: str
    type: str
    title: str
    origin_chamber: str = Field(alias="originChamber")
    origin_chamber_code: str = Field(alias="originChamberCode")
    introduced_date: Optional[date] = Field(default=None, alias="introducedDate")
    latest_action: LatestAction = Field(alias="latestAction")
    update_date: datetime = Field(alias="updateDate")
    policy_area: Optional[PolicyArea] = Field(default=None, alias="policyArea")
    sponsors: Optional[list[Sponsor]] = None
    summaries: Optional[list[CRSSummary]] = None
    laws: Optional[list[LawReference]] = None
    model_config = ConfigDict(populate_by_name=True)

    @property
    def citation(self) -> str:
        """Generate standard bill citation (e.g., 'H.R. 1234')."""
        type_map = {
            "HR": "H.R.",
            "S": "S.",
            "HJRES": "H.J.Res.",
            "SJRES": "S.J.Res.",
            "HCONRES": "H.Con.Res.",
            "SCONRES": "S.Con.Res.",
            "HRES": "H.Res.",
            "SRES": "S.Res.",
        }
        prefix = type_map.get(self.type.upper(), self.type)
        return f"{prefix} {self.number}"

    @property
    def public_law_number(self) -> Optional[str]:
        """Get the public law number if enacted."""
        if self.laws:
            for law in self.laws:
                if law.type == "Public Law":
                    return f"P.L. {self.congress}-{law.number}"
        return None


class MemberTerm(BaseModel):
    """Congressional term information."""

    chamber: str
    congress: Optional[int] = None
    start_year: Optional[int] = Field(default=None, alias="startYear")
    end_year: Optional[int] = Field(default=None, alias="endYear")
    model_config = ConfigDict(populate_by_name=True)


class MemberSummary(BaseModel):
    """Member from list endpoint."""

    bioguide_id: str = Field(alias="bioguideId")
    name: str
    party_name: Optional[str] = Field(default=None, alias="partyName")
    state: Optional[str] = None
    district: Optional[int] = None
    terms: Optional[list[MemberTerm]] = None
    url: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True)


class MemberDetail(BaseModel):
    """Detailed member information."""

    bioguide_id: str = Field(alias="bioguideId")
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    birth_year: Optional[int] = Field(default=None, alias="birthYear")
    party_history: Optional[list[dict[str, Any]]] = Field(default=None, alias="partyHistory")
    terms: Optional[list[MemberTerm]] = None
    sponsored_legislation: Optional[dict[str, Any]] = Field(
        default=None, alias="sponsoredLegislation"
    )
    model_config = ConfigDict(populate_by_name=True)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Pagination(BaseModel):
    """Pagination information from API responses."""

    count: int
    next: Optional[str] = None


class BillListResponse(BaseModel):
    """Response from bills list endpoint."""

    bills: list[BillSummary]
    pagination: Pagination
    request: dict[str, Any]


class LawListResponse(BaseModel):
    """Response from laws list endpoint."""

    bills: list[BillSummary]  # Laws endpoint returns bills that became law
    pagination: Pagination
    request: dict[str, Any]


class MemberListResponse(BaseModel):
    """Response from members list endpoint."""

    members: list[MemberSummary]
    pagination: Pagination
    request: dict[str, Any]
