"""Models for federal court data from Court Listener.

Credits: Court Listener API by Free Law Project (AGPL-3.0)
https://github.com/freelawproject/courtlistener
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class CourtListenerOpinion(BaseModel):
    """An opinion from Court Listener."""

    id: int
    case_id: Optional[int] = None
    case_name: str
    court: str
    court_name: Optional[str] = None
    date_created: date

    # Content
    plain_text: Optional[str] = None
    html: Optional[str] = None

    # Metadata
    opinion_type: str = "unknown"
    author: Optional[str] = None
    citation: Optional[str] = None

    # URL
    absolute_url: Optional[str] = None


class CourtListenerCase(BaseModel):
    """A case from Court Listener."""

    id: int
    case_name: str
    docket_number: str
    court: str
    court_name: Optional[str] = None

    # Dates
    date_filed: Optional[date] = None
    date_terminated: Optional[date] = None

    # Status
    status: Optional[str] = None
    nature_of_suit: Optional[str] = None

    # URL
    absolute_url: Optional[str] = None
