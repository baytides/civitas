"""Pydantic models for Congress.gov API responses."""

from datetime import date as date_type, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LatestAction(BaseModel):
    """Latest action taken on a bill."""

    action_date: date_type = Field(alias="actionDate")
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
    laws: list[LawReference] | None = None
    model_config = ConfigDict(populate_by_name=True)


class PolicyArea(BaseModel):
    """Policy area/subject category."""

    name: str


class CRSSummary(BaseModel):
    """Congressional Research Service summary."""

    action_date: date_type = Field(alias="actionDate")
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
    party: str | None = None
    state: str | None = None
    district: int | None = None
    is_by_request: str | None = Field(default=None, alias="isByRequest")
    model_config = ConfigDict(populate_by_name=True)


class TextVersion(BaseModel):
    """Bill text version."""

    date: date_type | None = None
    type: str
    url: str | None = None
    model_config = ConfigDict(populate_by_name=True)


class BillDetail(BaseModel):
    """Detailed bill information."""

    congress: int
    number: str
    type: str
    title: str
    origin_chamber: str = Field(alias="originChamber")
    origin_chamber_code: str = Field(alias="originChamberCode")
    introduced_date: date_type | None = Field(default=None, alias="introducedDate")
    latest_action: LatestAction = Field(alias="latestAction")
    update_date: datetime = Field(alias="updateDate")
    policy_area: PolicyArea | None = Field(default=None, alias="policyArea")
    sponsors: list[Sponsor] | None = None
    summaries: list[CRSSummary] | None = None
    laws: list[LawReference] | None = None
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
    def public_law_number(self) -> str | None:
        """Get the public law number if enacted."""
        if self.laws:
            for law in self.laws:
                if law.type == "Public Law":
                    return f"P.L. {self.congress}-{law.number}"
        return None


class MemberTerm(BaseModel):
    """Congressional term information."""

    chamber: str
    congress: int | None = None
    start_year: int | None = Field(default=None, alias="startYear")
    end_year: int | None = Field(default=None, alias="endYear")
    model_config = ConfigDict(populate_by_name=True)


class MemberSummary(BaseModel):
    """Member from list endpoint."""

    bioguide_id: str = Field(alias="bioguideId")
    name: str
    party_name: str | None = Field(default=None, alias="partyName")
    state: str | None = None
    district: int | None = None
    terms: list[MemberTerm] | None = None
    url: str | None = None
    model_config = ConfigDict(populate_by_name=True)


class MemberDetail(BaseModel):
    """Detailed member information."""

    bioguide_id: str = Field(alias="bioguideId")
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    birth_year: int | None = Field(default=None, alias="birthYear")
    party_history: list[dict[str, Any]] | None = Field(default=None, alias="partyHistory")
    terms: list[MemberTerm] | None = None
    sponsored_legislation: dict[str, Any] | None = Field(
        default=None, alias="sponsoredLegislation"
    )
    model_config = ConfigDict(populate_by_name=True)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Pagination(BaseModel):
    """Pagination information from API responses."""

    count: int
    next: str | None = None


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
