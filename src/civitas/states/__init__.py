"""State legislative data integration.

Three approaches available for accessing state legislative data:

1. **Direct Scraping** (recommended): Scrape directly from state legislature websites
   - No API limits, real-time data
   - Uses `civitas.states.scrapers` module

2. **Bulk Data** (~9GB monthly dump): Complete historical data for all 50 states
   - Good for initial database population
   - Uses `civitas.states.bulk_ingest` module

Credits:
- Open States Project (GPL-3.0 / CC0-1.0)
- Open Civic Data (BSD-3-Clause)
- Plural Policy: https://open.pluralpolicy.com/data/
- State legislature websites (public domain)
"""

# Bulk ingestion (no API limits)
from .bulk_ingest import (
    BulkStateBill,
    BulkStateLegislator,
    OpenStatesBulkIngester,
    download_bulk_data,
)

# Direct scrapers (preferred approach)
from .scrapers import (
    CaliforniaScraper,
    ScrapedBill,
    ScrapedLegislator,
    StateScraper,
)

__all__ = [
    # Direct scrapers (preferred)
    "StateScraper",
    "ScrapedBill",
    "ScrapedLegislator",
    "CaliforniaScraper",
    # Bulk ingestion (no limits)
    "OpenStatesBulkIngester",
    "BulkStateBill",
    "BulkStateLegislator",
    "download_bulk_data",
]
