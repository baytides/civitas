"""State legislature scrapers for Civitas.

This module provides direct scraping of state legislature websites,
bypassing the OpenStates API rate limits.

Architecture mirrors OpenStates scrapers (GPL-3.0) but reimplemented
for direct Civitas integration.

Usage:
    from civitas.states.scrapers import CaliforniaScraper

    with CaliforniaScraper() as scraper:
        for bill in scraper.get_bills(session="2023"):
            print(f"{bill.identifier}: {bill.title}")

Credits:
- OpenStates Project (GPL-3.0)
- Spatula scraping library (MIT)
"""

from .base import ScrapedBill, ScrapedLegislator, StateScraper
from .california import CaliforniaScraper

__all__ = [
    "StateScraper",
    "ScrapedBill",
    "ScrapedLegislator",
    "CaliforniaScraper",
]
