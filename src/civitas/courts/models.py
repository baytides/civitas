"""Models for federal court data from Court Listener.

Credits: Court Listener API by Free Law Project (AGPL-3.0)
https://github.com/freelawproject/courtlistener
"""

from datetime import date

from pydantic import BaseModel


class CourtListenerOpinion(BaseModel):
    """An opinion from Court Listener."""

    id: int
    case_id: int | None = None
    case_name: str
    court: str
    court_name: str | None = None
    date_created: date

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
