"""External data source integrations.

This module contains clients for accessing external data sources:
- Internet Archive (archive.org) - Legal documents, US Reports, EOs
- DocumentCloud - Primary source documents, court filings
- MuckRock - FOIA requests and responses

Usage:
    # Internet Archive (ready to use)
    from civitas.sources import InternetArchiveClient
    client = InternetArchiveClient()
    for doc in client.download_us_reports():
        print(doc.title)

    # DocumentCloud (requires credentials)
    from civitas.sources import DocumentCloudClient
    client = DocumentCloudClient()  # Uses DC_USERNAME, DC_PASSWORD
    results = client.search("executive order")

    # MuckRock (requires credentials)
    from civitas.sources import MuckRockClient
    client = MuckRockClient()  # Uses MUCKROCK_USERNAME, MUCKROCK_PASSWORD
    requests = client.search_requests("immigration")
"""

from .documentcloud import DocumentCloudClient
from .internet_archive import InternetArchiveClient
from .muckrock import MuckRockClient

__all__ = [
    "InternetArchiveClient",
    "DocumentCloudClient",
    "MuckRockClient",
]
