"""Supreme Court opinion data ingestion.

Provides:
- SCOTUSClient: Scrapes slip opinions from supremecourt.gov
- SCOTUSOpinion: Parsed opinion data model
- SCOTUSListingItem: Opinion listing metadata
"""

from .client import SCOTUSClient
from .justices import link_opinions_to_justices, sync_justices
from .models import SCOTUSListingItem, SCOTUSOpinion

__all__ = [
    "SCOTUSClient",
    "SCOTUSOpinion",
    "SCOTUSListingItem",
    "sync_justices",
    "link_opinions_to_justices",
]
