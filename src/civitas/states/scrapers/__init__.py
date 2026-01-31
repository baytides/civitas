"""State legislature scrapers for Civitas.

This module provides direct scraping of state legislature websites.

Usage:
    from civitas.states.scrapers import get_scraper, list_available_scrapers

    # Get a specific scraper
    scraper_cls = get_scraper("ny")
    with scraper_cls() as scraper:
        for bill in scraper.get_bills(session="2025"):
            print(f"{bill.identifier}: {bill.title}")

    # List available scrapers
    for state, scraper_cls in list_available_scrapers():
        print(f"{state}: {scraper_cls.STATE_NAME}")

Credits:
- OpenStates Project (GPL-3.0)
- Spatula scraping library (MIT)
"""

from .base import STATE_NAMES, ScrapedBill, ScrapedLegislator, ScrapedVote, StateScraper
from .california import CaliforniaScraper

# Registry of available scrapers by state code
_SCRAPER_REGISTRY: dict[str, type[StateScraper]] = {
    "ca": CaliforniaScraper,
}


def register_scraper(scraper_cls: type[StateScraper]) -> type[StateScraper]:
    """Decorator to register a scraper class.

    Usage:
        @register_scraper
        class NewYorkScraper(StateScraper):
            STATE = "ny"
            ...
    """
    if scraper_cls.STATE:
        _SCRAPER_REGISTRY[scraper_cls.STATE.lower()] = scraper_cls
    return scraper_cls


def get_scraper(state: str) -> type[StateScraper] | None:
    """Get scraper class for a state.

    Args:
        state: Two-letter state code (e.g., "ny", "ca")

    Returns:
        Scraper class or None if not available
    """
    return _SCRAPER_REGISTRY.get(state.lower())


def list_available_scrapers() -> list[tuple[str, type[StateScraper]]]:
    """List all available scrapers.

    Returns:
        List of (state_code, scraper_class) tuples
    """
    return sorted(_SCRAPER_REGISTRY.items())


def get_state_name(state: str) -> str:
    """Get full state name from code.

    Args:
        state: Two-letter state code

    Returns:
        Full state name or the code if not found
    """
    return STATE_NAMES.get(state.lower(), state.upper())


# Lazy imports for additional scrapers
# These are imported on demand to avoid loading unnecessary dependencies
def _lazy_import_new_york():
    from .new_york import NewYorkScraper

    _SCRAPER_REGISTRY["ny"] = NewYorkScraper
    return NewYorkScraper


def _lazy_import_illinois():
    from .illinois import IllinoisScraper

    _SCRAPER_REGISTRY["il"] = IllinoisScraper
    return IllinoisScraper


def _lazy_import_washington():
    from .washington import WashingtonScraper

    _SCRAPER_REGISTRY["wa"] = WashingtonScraper
    return WashingtonScraper


# Try to import additional scrapers if available
try:
    from .new_york import NewYorkScraper

    _SCRAPER_REGISTRY["ny"] = NewYorkScraper
except ImportError:
    pass

try:
    from .illinois import IllinoisScraper

    _SCRAPER_REGISTRY["il"] = IllinoisScraper
except ImportError:
    pass

try:
    from .washington import WashingtonScraper

    _SCRAPER_REGISTRY["wa"] = WashingtonScraper
except ImportError:
    pass


__all__ = [
    # Base classes
    "StateScraper",
    "ScrapedBill",
    "ScrapedLegislator",
    "ScrapedVote",
    "STATE_NAMES",
    # Registry functions
    "register_scraper",
    "get_scraper",
    "list_available_scrapers",
    "get_state_name",
    # Scrapers
    "CaliforniaScraper",
]
