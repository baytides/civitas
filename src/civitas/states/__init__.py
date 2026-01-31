"""State legislative data integration.

Uses direct scraping from state legislature websites:
- No API limits, real-time data
- Uses `civitas.states.scrapers` module

Credits:
- State legislature websites (public domain)
- Plural Policy: https://open.pluralpolicy.com/data/
"""

# Direct scrapers (preferred approach)
from .scrapers import (
    CaliforniaScraper,
    ScrapedBill,
    ScrapedLegislator,
    StateScraper,
)

__all__ = [
    # Direct scrapers
    "StateScraper",
    "ScrapedBill",
    "ScrapedLegislator",
    "CaliforniaScraper",
]
