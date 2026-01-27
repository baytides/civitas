"""Models for federal court data from Court Listener.

Credits: Court Listener API by Free Law Project (AGPL-3.0)
https://github.com/freelawproject/courtlistener
"""

from datetime import date, datetime

from pydantic import BaseModel, field_validator


class CourtListenerOpinion(BaseModel):
    """An opinion from Court Listener."""

    id: int
    case_id: int | None = None
    case_name: str
    court: str
    court_name: str | None = None
    date_created: date | None = None

    @field_validator("date_created", mode="before")
    @classmethod
    def parse_date_created(cls, v):
        """Parse datetime strings to date."""
        if v is None:
            return None
        if isinstance(v, date) and not isinstance(v, datetime):
            return v
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, str):
            # Handle ISO datetime strings
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00")).date()
            except ValueError:
                try:
                    return datetime.strptime(v[:10], "%Y-%m-%d").date()
                except ValueError:
                    return None
        return None

    # Content
    plain_text: str | None = None
    html: str | None = None

    # Metadata
    opinion_type: str = "unknown"
    author: str | None = None
    citation: str | None = None

    # URL
    absolute_url: str | None = None


class CourtListenerCase(BaseModel):
    """A case from Court Listener."""

    id: int
    case_name: str
    docket_number: str
    court: str
    court_name: str | None = None

    # Dates
    date_filed: date | None = None
    date_terminated: date | None = None

    # Status
    status: str | None = None
    nature_of_suit: str | None = None

    # URL
    absolute_url: str | None = None
