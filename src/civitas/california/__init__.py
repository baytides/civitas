"""California Legislature data integration.

Data source: https://downloads.leginfo.legislature.ca.gov/

Provides access to:
- Bills and their versions
- Vote records (summary and detail)
- Bill history and actions
- Legislators
- Committee hearings and agendas
- California law codes and sections
- Veto messages
"""

from civitas.california.client import CaliforniaLegislatureClient
from civitas.california.models import (
    Bill,
    BillAnalysis,
    BillDetailVote,
    BillHistory,
    BillSummaryVote,
    BillVersion,
    LawSection,
    Legislator,
    VetoMessage,
)

__all__ = [
    "CaliforniaLegislatureClient",
    "Bill",
    "BillVersion",
    "BillHistory",
    "BillAnalysis",
    "BillSummaryVote",
    "BillDetailVote",
    "Legislator",
    "LawSection",
    "VetoMessage",
]
